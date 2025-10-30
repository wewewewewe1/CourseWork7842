# =======================
# warning_system.py - Two-Layer Warning System
# Real-time detection + Historical storage
# =======================
"""
Industrial PMU Warning System - Two-Layer Architecture

Layer 1 (Real-Time): Sub-20ms response
  - In-memory threshold checking
  - Smart triggering (continuous deviation detection)
  - Immediate notification to frontend
  - No database I/O on critical path

Layer 2 (Storage): Background persistence
  - Async event recording
  - Historical tracking with full details
  - Trend analysis
  - Recovery detection and auto-close
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from influxdb import InfluxDBClient
from threading import Thread, Lock
import json

# ==================== Enums ====================

class WarningSeverity(Enum):
    """Warning severity levels"""
    INFO = 0
    WARNING = 1
    CRITICAL = 2

class WarningState(Enum):
    """Warning event state"""
    ACTIVE = "active"
    RECOVERED = "recovered"
    ACKNOWLEDGED = "acknowledged"

# ==================== Configuration ====================

@dataclass
class ThresholdConfig:
    """Configurable threshold settings"""
    # Signal identification
    signal_id: str
    signal_type: str  # "frequency", "voltage", "current", etc.

    # Threshold values
    warning_min: Optional[float] = None
    warning_max: Optional[float] = None
    critical_min: Optional[float] = None
    critical_max: Optional[float] = None

    # Smart triggering parameters
    trigger_count: int = 3  # Must exceed threshold N times
    trigger_window: float = 5.0  # Within this many seconds
    recovery_count: int = 2  # Must be normal N times to recover
    recovery_window: float = 3.0  # Within this many seconds

    # Debouncing
    min_event_duration: float = 1.0  # Ignore events shorter than this

@dataclass
class WarningEvent:
    """Warning event data structure"""
    event_id: str
    signal_id: str
    signal_type: str
    severity: WarningSeverity
    state: WarningState

    # Threshold info
    threshold_type: str  # "min" or "max"
    threshold_value: float
    trigger_value: float

    # Timing
    first_trigger_time: datetime
    event_start_time: Optional[datetime] = None
    event_end_time: Optional[datetime] = None
    duration: Optional[float] = None

    # Tracking
    trigger_count: int = 0
    max_deviation: float = 0.0
    values_during_event: List[float] = field(default_factory=list)

    # Metadata
    message: str = ""
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

class RealTimeWarningLayer:
    """
    Real-Time Warning Detection Layer

    Features:
    - Sub-20ms threshold checking
    - In-memory operation (no DB on critical path)
    - Smart triggering with time windows
    - Immediate callback notification
    """

    def __init__(self, thresholds: List[ThresholdConfig],
                 callback: Optional[Callable] = None):
        """
        Args:
            thresholds: List of threshold configurations
            callback: Function to call when event state changes
        """
        self.thresholds = {t.signal_id: t for t in thresholds}
        self.callback = callback

        # Active tracking
        self.active_events: Dict[str, WarningEvent] = {}
        self.trigger_history: Dict[str, deque] = {}  # For smart triggering
        self.recovery_history: Dict[str, deque] = {}  # For recovery detection

        # Performance metrics
        self.check_count = 0
        self.total_check_time = 0.0

        # Thread safety
        self.lock = Lock()

        print("[WARNING-RT] Real-time warning layer initialized")
        print(f"[WARNING-RT] Monitoring {len(self.thresholds)} signals")

    def check_value(self, signal_id: str, value: float, timestamp: datetime) -> Optional[WarningEvent]:
        """
        Check a single value against thresholds (FAST - sub-20ms target)

        Args:
            signal_id: Signal identifier
            value: Current value
            timestamp: Measurement timestamp

        Returns:
            WarningEvent if state change occurred, None otherwise
        """
        start_time = time.perf_counter()

        with self.lock:
            if signal_id not in self.thresholds:
                return None

            config = self.thresholds[signal_id]

            # Initialize history if needed
            if signal_id not in self.trigger_history:
                self.trigger_history[signal_id] = deque(maxlen=100)
                self.recovery_history[signal_id] = deque(maxlen=100)

            # Check thresholds
            violation = self._check_threshold(value, config)

            if violation:
                # Threshold exceeded
                self.trigger_history[signal_id].append((timestamp, value, violation))
                self.recovery_history[signal_id].clear()

                # Check if we should trigger an event
                event = self._evaluate_trigger(signal_id, config, timestamp)

                if event:
                    # New event or state change
                    if self.callback:
                        self.callback(event)

                    elapsed = time.perf_counter() - start_time
                    self.check_count += 1
                    self.total_check_time += elapsed

                    return event

            else:
                # Normal value
                self.recovery_history[signal_id].append((timestamp, value))

                # Check if active event should recover
                if signal_id in self.active_events:
                    event = self._evaluate_recovery(signal_id, config, timestamp)

                    if event:
                        if self.callback:
                            self.callback(event)

                        elapsed = time.perf_counter() - start_time
                        self.check_count += 1
                        self.total_check_time += elapsed

                        return event

        elapsed = time.perf_counter() - start_time
        self.check_count += 1
        self.total_check_time += elapsed

        return None

    def _check_threshold(self, value: float, config: ThresholdConfig) -> Optional[Dict]:
        """
        Check if value exceeds thresholds

        Returns:
            Dict with violation details if threshold exceeded, None otherwise
        """
        # Check critical thresholds first
        if config.critical_min is not None and value < config.critical_min:
            return {
                'severity': WarningSeverity.CRITICAL,
                'type': 'min',
                'threshold': config.critical_min,
                'deviation': config.critical_min - value
            }

        if config.critical_max is not None and value > config.critical_max:
            return {
                'severity': WarningSeverity.CRITICAL,
                'type': 'max',
                'threshold': config.critical_max,
                'deviation': value - config.critical_max
            }

        # Check warning thresholds
        if config.warning_min is not None and value < config.warning_min:
            return {
                'severity': WarningSeverity.WARNING,
                'type': 'min',
                'threshold': config.warning_min,
                'deviation': config.warning_min - value
            }

        if config.warning_max is not None and value > config.warning_max:
            return {
                'severity': WarningSeverity.WARNING,
                'type': 'max',
                'threshold': config.warning_max,
                'deviation': value - config.warning_max
            }

        return None

    def _evaluate_trigger(self, signal_id: str, config: ThresholdConfig,
                          current_time: datetime) -> Optional[WarningEvent]:
        """
        Evaluate if we should trigger a warning event (smart triggering)

        Only triggers if threshold exceeded N times within time window
        """
        history = self.trigger_history[signal_id]

        if len(history) < config.trigger_count:
            return None  # Not enough violations yet

        # Check if we have enough violations within the time window
        recent_violations = [
            (ts, val, viol) for ts, val, viol in history
            if (current_time - ts).total_seconds() <= config.trigger_window
        ]

        if len(recent_violations) < config.trigger_count:
            return None  # Not enough recent violations

        # Trigger event!
        if signal_id in self.active_events:
            # Event already active, just update it
            event = self.active_events[signal_id]
            event.trigger_count += 1

            # Track max deviation
            latest_viol = recent_violations[-1][2]
            if latest_viol['deviation'] > event.max_deviation:
                event.max_deviation = latest_viol['deviation']

            event.values_during_event.append(recent_violations[-1][1])

            return None  # No state change

        else:
            # New event
            first_viol = recent_violations[0]
            latest_viol = recent_violations[-1]

            event_id = f"{signal_id}_{int(first_viol[0].timestamp())}"

            event = WarningEvent(
                event_id=event_id,
                signal_id=signal_id,
                signal_type=config.signal_type,
                severity=latest_viol[2]['severity'],
                state=WarningState.ACTIVE,
                threshold_type=latest_viol[2]['type'],
                threshold_value=latest_viol[2]['threshold'],
                trigger_value=latest_viol[1],
                first_trigger_time=first_viol[0],
                event_start_time=current_time,
                trigger_count=len(recent_violations),
                max_deviation=max(v[2]['deviation'] for v in recent_violations),
                values_during_event=[v[1] for v in recent_violations],
                message=self._generate_message(config, latest_viol[2])
            )

            self.active_events[signal_id] = event

            print(f"[WARNING-RT] Event triggered: {event.event_id}")
            print(f"  Signal: {signal_id}, Severity: {event.severity.name}")
            print(f"  Threshold: {event.threshold_type} {event.threshold_value}")
            print(f"  Value: {event.trigger_value}")

            return event

    def _evaluate_recovery(self, signal_id: str, config: ThresholdConfig,
                           current_time: datetime) -> Optional[WarningEvent]:
        """
        Evaluate if an active event should recover

        Only recovers if normal for N consecutive times within time window
        """
        history = self.recovery_history[signal_id]

        if len(history) < config.recovery_count:
            return None

        # Check if we have enough normal readings within the window
        recent_normal = [
            (ts, val) for ts, val in history
            if (current_time - ts).total_seconds() <= config.recovery_window
        ]

        if len(recent_normal) < config.recovery_count:
            return None

        # Check minimum duration
        event = self.active_events[signal_id]
        duration = (current_time - event.event_start_time).total_seconds()

        if duration < config.min_event_duration:
            # Too short, ignore
            del self.active_events[signal_id]
            self.trigger_history[signal_id].clear()
            return None

        # Recover!
        event.event_end_time = current_time
        event.duration = duration
        event.state = WarningState.RECOVERED
        event.message += f" | Recovered after {duration:.1f}s"

        del self.active_events[signal_id]
        self.trigger_history[signal_id].clear()
        self.recovery_history[signal_id].clear()

        print(f"[WARNING-RT] Event recovered: {event.event_id}")
        print(f"  Duration: {duration:.1f}s")

        return event

    def _generate_message(self, config: ThresholdConfig, violation: Dict) -> str:
        """Generate human-readable warning message"""
        severity = violation['severity'].name
        threshold_type = violation['type']
        threshold = violation['threshold']
        deviation = violation['deviation']

        if threshold_type == 'min':
            return f"{severity}: {config.signal_type} below {threshold} (deviation: -{deviation:.2f})"
        else:
            return f"{severity}: {config.signal_type} above {threshold} (deviation: +{deviation:.2f})"

    def get_active_events(self) -> List[WarningEvent]:
        """Get all currently active events"""
        with self.lock:
            return list(self.active_events.values())

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        if self.check_count == 0:
            return {"avg_check_time_ms": 0.0, "check_count": 0}

        avg_time_ms = (self.total_check_time / self.check_count) * 1000
        return {
            "avg_check_time_ms": avg_time_ms,
            "check_count": self.check_count,
            "active_events": len(self.active_events)
        }

class StorageWarningLayer:
    """
    Storage Warning Layer

    Features:
    - Async background event persistence
    - Historical tracking
    - Trend analysis
    - Query API for historical events
    """

    def __init__(self, influx_host: str = "127.0.0.1", influx_port: int = 8086,
                 database: str = "pmu_warnings"):
        """
        Args:
            influx_host: InfluxDB host
            influx_port: InfluxDB port
            database: Database name for warnings
        """
        self.client = InfluxDBClient(host=influx_host, port=influx_port, database=database)

        # Create database if needed
        databases = self.client.get_list_database()
        db_names = [db['name'] for db in databases]
        if database not in db_names:
            self.client.create_database(database)
            print(f"[WARNING-STORAGE] Created database: {database}")

        # Write queue (for async writes)
        self.write_queue: List[WarningEvent] = []
        self.queue_lock = Lock()

        # Background thread
        self.running = False
        self.thread = None

        print("[WARNING-STORAGE] Storage layer initialized")

    def record_event(self, event: WarningEvent):
        """
        Record a warning event (async - queued for background write)

        Args:
            event: Warning event to record
        """
        with self.queue_lock:
            self.write_queue.append(event)

    def start_background_writer(self, interval: float = 1.0):
        """Start background thread that writes queued events"""
        if self.running:
            return

        self.running = True
        self.thread = Thread(target=self._writer_loop, args=(interval,), daemon=True)
        self.thread.start()
        print("[WARNING-STORAGE] Background writer started")

    def stop_background_writer(self):
        """Stop background writer thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[WARNING-STORAGE] Background writer stopped")

    def _writer_loop(self, interval: float):
        """Background writer loop"""
        while self.running:
            try:
                with self.queue_lock:
                    events_to_write = self.write_queue.copy()
                    self.write_queue.clear()

                if events_to_write:
                    self._write_events_batch(events_to_write)

                time.sleep(interval)
            except Exception as e:
                print(f"[WARNING-STORAGE] Error in writer loop: {e}")

    def _write_events_batch(self, events: List[WarningEvent]):
        """Write batch of events to InfluxDB"""
        points = []

        for event in events:
            # Main event record
            points.append({
                "measurement": "warning_events",
                "tags": {
                    "event_id": event.event_id,
                    "signal_id": event.signal_id,
                    "signal_type": event.signal_type,
                    "severity": event.severity.name,
                    "state": event.state.value,
                },
                "fields": {
                    "threshold_type": event.threshold_type,
                    "threshold_value": event.threshold_value,
                    "trigger_value": event.trigger_value,
                    "trigger_count": event.trigger_count,
                    "max_deviation": event.max_deviation,
                    "duration": event.duration if event.duration else 0.0,
                    "message": event.message,
                    "acknowledged": 1 if event.acknowledged else 0,
                },
                "time": event.event_start_time.isoformat() if event.event_start_time else event.first_trigger_time.isoformat()
            })

            # Recovery record (if recovered)
            if event.state == WarningState.RECOVERED and event.event_end_time:
                points.append({
                    "measurement": "warning_recoveries",
                    "tags": {
                        "event_id": event.event_id,
                        "signal_id": event.signal_id,
                    },
                    "fields": {
                        "duration": event.duration,
                        "recovery_time": event.event_end_time.isoformat(),
                    },
                    "time": event.event_end_time.isoformat()
                })

        try:
            self.client.write_points(points)
            print(f"[WARNING-STORAGE] Wrote {len(events)} events to database")
        except Exception as e:
            print(f"[WARNING-STORAGE] Failed to write events: {e}")

    def query_events(self, start_time: Optional[str] = None, end_time: Optional[str] = None,
                     signal_id: Optional[str] = None, severity: Optional[str] = None,
                     state: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Query historical warning events

        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            signal_id: Filter by signal ID
            severity: Filter by severity
            state: Filter by state
            limit: Maximum results

        Returns:
            List of event dictionaries
        """
        where_clauses = []

        if start_time:
            where_clauses.append(f"time >= '{start_time}'")
        if end_time:
            where_clauses.append(f"time <= '{end_time}'")
        if signal_id:
            where_clauses.append(f'"signal_id" = \'{signal_id}\'')
        if severity:
            where_clauses.append(f'"severity" = \'{severity}\'')
        if state:
            where_clauses.append(f'"state" = \'{state}\'')

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f'SELECT * FROM "warning_events" WHERE {where_str} ORDER BY time DESC LIMIT {limit}'

        try:
            result = self.client.query(query)
            return list(result.get_points())
        except Exception as e:
            print(f"[WARNING-STORAGE] Query failed: {e}")
            return []

# ==================== Integrated Warning Manager ====================

class WarningManager:
    """
    Integrated two-layer warning manager

    Combines real-time detection with background storage
    """

    def __init__(self, thresholds: List[ThresholdConfig],
                 influx_host: str = "127.0.0.1", influx_port: int = 8086,
                 db_name: str = "pmu_warnings"):
        """
        Args:
            thresholds: List of threshold configurations
            influx_host: InfluxDB host
            influx_port: InfluxDB port
            db_name: Database name for warnings
        """
        # Create layers
        self.realtime_layer = RealTimeWarningLayer(
            thresholds=thresholds,
            callback=self._on_event_change
        )

        self.storage_layer = StorageWarningLayer(
            influx_host=influx_host,
            influx_port=influx_port,
            database=db_name
        )

        # Start background writer
        self.storage_layer.start_background_writer(interval=1.0)

        print("[WARNING-MGR] Integrated warning manager initialized")

    def _on_event_change(self, event: WarningEvent):
        """Callback when event state changes"""
        # Queue for storage
        self.storage_layer.record_event(event)

    def check_value(self, signal_id: str, value: float, timestamp: datetime) -> Optional[WarningEvent]:
        """
        Check a value (delegates to real-time layer)

        Returns:
            WarningEvent if state changed, None otherwise
        """
        return self.realtime_layer.check_value(signal_id, value, timestamp)

    def get_active_warnings(self) -> List[WarningEvent]:
        """Get all currently active warnings"""
        return self.realtime_layer.get_active_events()

    def query_historical(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        signal_id: Optional[str] = None,
                        severity: Optional[str] = None,
                        limit: int = 100) -> List[WarningEvent]:
        """
        Query historical warnings from storage layer

        Args:
            start_time: Start datetime filter
            end_time: End datetime filter
            signal_id: Signal ID filter
            severity: Severity filter
            limit: Maximum results

        Returns:
            List of WarningEvent objects
        """
        # Convert datetime to ISO strings for query
        start_iso = start_time.isoformat() if start_time else None
        end_iso = end_time.isoformat() if end_time else None

        results = self.storage_layer.query_events(
            start_time=start_iso,
            end_time=end_iso,
            signal_id=signal_id,
            severity=severity,
            limit=limit
        )

        # Convert dict results to WarningEvent objects
        events = []
        for r in results:
            try:
                from warning_system import WarningSeverity, WarningState
                event = WarningEvent(
                    event_id=r.get('event_id', ''),
                    signal_id=r.get('signal_id', ''),
                    signal_type=r.get('signal_type', ''),
                    severity=WarningSeverity[r.get('severity', 'WARNING')],
                    state=WarningState(r.get('state', 'active')),
                    threshold_type=r.get('threshold_type', 'max'),
                    threshold_value=r.get('threshold_value', 0.0),
                    trigger_value=r.get('trigger_value', 0.0),
                    first_trigger_time=datetime.fromisoformat(r['time']) if 'time' in r else datetime.utcnow(),
                    trigger_count=r.get('trigger_count', 0),
                    max_deviation=r.get('max_deviation', 0.0),
                    duration=r.get('duration', 0.0),
                    message=r.get('message', ''),
                    acknowledged=bool(r.get('acknowledged', 0))
                )
                events.append(event)
            except Exception as e:
                print(f"[WARNING-MGR] Error converting event: {e}")
                continue

        return events

    def get_statistics(self) -> Dict:
        """
        Get comprehensive warning system statistics

        Returns:
            Dict with active count, performance metrics, and breakdowns
        """
        perf_stats = self.realtime_layer.get_performance_stats()
        active_events = self.realtime_layer.get_active_events()

        # Count by severity
        by_severity = {"WARNING": 0, "CRITICAL": 0}
        by_signal = {}

        for event in active_events:
            severity_name = event.severity.name if hasattr(event.severity, 'name') else str(event.severity)
            by_severity[severity_name] = by_severity.get(severity_name, 0) + 1
            by_signal[event.signal_id] = by_signal.get(event.signal_id, 0) + 1

        return {
            "active_count": len(active_events),
            "total_events": len(active_events),
            "avg_check_time_ms": perf_stats.get("avg_check_time_ms", 0.0),
            "max_check_time_ms": perf_stats.get("max_check_time_ms", 0.0),
            "total_checks": perf_stats.get("total_checks", 0),
            "checks_per_second": perf_stats.get("checks_per_second", 0.0),
            "by_severity": by_severity,
            "by_signal": by_signal
        }

    def update_thresholds(self, thresholds: List[ThresholdConfig]):
        """
        Update threshold configurations

        Args:
            thresholds: New list of threshold configurations
        """
        # Stop current storage writer
        self.storage_layer.stop_background_writer()

        # Recreate real-time layer with new thresholds
        self.realtime_layer = RealTimeWarningLayer(
            thresholds=thresholds,
            callback=self._on_event_change
        )

        # Restart storage writer
        self.storage_layer.start_background_writer(interval=1.0)

        print(f"[WARNING-MGR] Updated {len(thresholds)} threshold configurations")

    def acknowledge_event(self, event_id: str, user: str) -> bool:
        """
        Acknowledge a warning event

        Args:
            event_id: Event ID to acknowledge
            user: Username acknowledging the event

        Returns:
            True if event found and acknowledged, False otherwise
        """
        # Find event in active events
        active_events = self.realtime_layer.get_active_events()

        for event in active_events:
            if event.event_id == event_id:
                event.acknowledged = True
                event.acknowledged_by = user
                event.acknowledged_at = datetime.utcnow()

                # Record acknowledgment to storage
                self.storage_layer.record_event(event)

                print(f"[WARNING-MGR] Event {event_id} acknowledged by {user}")
                return True

        return False

    def get_stats(self) -> Dict:
        """Get system statistics (legacy method - use get_statistics)"""
        return self.get_statistics()

    def stop(self):
        """Stop the warning manager"""
        self.storage_layer.stop_background_writer()
        print("[WARNING-MGR] Warning manager stopped")

# ==================== Example Configuration ====================

def create_default_thresholds() -> List[ThresholdConfig]:
    """Create default threshold configuration for common PMU signals"""
    return [
        ThresholdConfig(
            signal_id="PMU_frequency",
            signal_type="frequency",
            warning_min=59.9,
            warning_max=60.1,
            critical_min=59.8,
            critical_max=60.2,
            trigger_count=3,
            trigger_window=5.0,
            recovery_count=2,
            recovery_window=3.0,
            min_event_duration=1.0
        ),
        ThresholdConfig(
            signal_id="PMU_voltage_a_mag",
            signal_type="voltage",
            warning_min=190000.0,  # -5%
            warning_max=208000.0,  # +5%
            critical_min=180000.0,  # -10%
            critical_max=220000.0,  # +10%
            trigger_count=3,
            trigger_window=5.0,
            recovery_count=2,
            recovery_window=3.0,
            min_event_duration=1.0
        ),
        ThresholdConfig(
            signal_id="PMU_rocof",
            signal_type="ROCOF",
            warning_min=-0.5,
            warning_max=0.5,
            critical_min=-1.0,
            critical_max=1.0,
            trigger_count=2,
            trigger_window=3.0,
            recovery_count=2,
            recovery_window=2.0,
            min_event_duration=0.5
        ),
    ]
