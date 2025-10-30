# =========================================================
# api_server.py  — 本地稳定版（开发阶段）
# =========================================================
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from influxdb import InfluxDBClient
from datetime import datetime
from typing import List, Optional, Dict, Any
from proxy_core import PMUMonitor
from analysis import AnalysisManager
from warning_system import WarningManager, ThresholdConfig, WarningEvent
from config import (
    HOST, PORT, SOURCE_DB, TARGET_DB, ANALYSIS_DB, SIGNALS,
    ANALYSIS_INTERVAL, ANALYSIS_SAMPLE_RATE
)

app = FastAPI(title="PMU Monitor API", version="7.14")

# 允许前端跨域访问（5173 → 8000）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动后台监测线程
monitor = PMUMonitor()
monitor.start()

# 启动后台分析线程
analysis_manager = AnalysisManager(
    influx_host=HOST,
    influx_port=PORT,
    source_db=SOURCE_DB,
    analysis_db=ANALYSIS_DB,
    signals=SIGNALS,
    analysis_interval=ANALYSIS_INTERVAL,
    sample_rate=ANALYSIS_SAMPLE_RATE
)
analysis_manager.start()

# Initialize warning system with default thresholds
default_thresholds = []
for signal_id, signal_config in SIGNALS.items():
    if signal_config.get("type") == "frequency":
        # Frequency thresholds
        base = signal_config.get("base", 60.0)
        default_thresholds.append(ThresholdConfig(
            signal_id=signal_id,
            signal_type="frequency",
            warning_min=base - 0.15,
            warning_max=base + 0.15,
            critical_min=base - 0.5,
            critical_max=base + 0.5,
            trigger_count=3,
            trigger_window=5.0,
            recovery_count=2,
            recovery_window=3.0
        ))
    elif signal_config.get("type") == "voltage":
        # Voltage thresholds
        base = signal_config.get("base", 299646.0)
        default_thresholds.append(ThresholdConfig(
            signal_id=signal_id,
            signal_type="voltage",
            warning_min=base * 0.90,
            warning_max=base * 1.10,
            critical_min=base * 0.70,
            critical_max=base * 1.30,
            trigger_count=3,
            trigger_window=5.0,
            recovery_count=2,
            recovery_window=3.0
        ))

warning_manager = WarningManager(
    thresholds=default_thresholds,
    influx_host=HOST,
    influx_port=PORT,
    db_name="pmu_warnings"
)

# ---- 时间转换辅助 ----
def _to_influx_time(ts: str):
    if not ts:
        return None
    try:
        if ts.isdigit():
            v = int(ts)
            if v > 1_000_000_000_000:
                v = v / 1000.0
            return datetime.utcfromtimestamp(v).isoformat() + "Z"
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

# ---- 接口定义 ----
@app.get("/")
def root():
    return {"status": "ok", "message": "PMU Monitor API running"}

@app.get("/signals")
def list_signals():
    return [{"id": k, **v} for k, v in SIGNALS.items()]

@app.get("/data/{signal_id}")
def get_data(signal_id: str, limit: int = 300, start: str = "", end: str = ""):
    client = InfluxDBClient(host=HOST, port=PORT, database=SOURCE_DB)
    start_iso = _to_influx_time(start)
    end_iso = _to_influx_time(end)

    if start_iso or end_iso:
        where = []
        if start_iso:
            where.append(f"time >= '{start_iso}'")
        if end_iso:
            where.append(f"time <= '{end_iso}'")
        q = f'SELECT "value","time" FROM "{signal_id}" WHERE ' + " AND ".join(where) + ' ORDER BY time ASC'
    else:
        q = f'SELECT "value","time" FROM "{signal_id}" ORDER BY time DESC LIMIT {limit}'

    res = list(client.query(q).get_points())
    return res if (start_iso or end_iso) else res[::-1]

@app.get("/alerts")
def get_alerts(limit: int = 200):
    client = InfluxDBClient(host=HOST, port=PORT, database=TARGET_DB)
    q = f'SELECT "device","signal_type","value","deviation","time" FROM "pmu_monitor_alerts" ORDER BY time DESC LIMIT {limit}'
    res = list(client.query(q).get_points())
    return res[::-1]

@app.get("/stop")
def stop_monitor():
    monitor.stop()
    analysis_manager.stop()
    warning_manager.stop()
    return {"status": "stopped"}

# ---- Analysis Endpoints ----

@app.get("/analysis/fft/{signal_id}")
def get_fft_analysis(signal_id: str, limit: int = 1):
    """
    Get FFT analysis results for a signal.

    Args:
        signal_id: Signal identifier (e.g., "PPA:2")
        limit: Number of recent results to return

    Returns:
        Latest FFT summary including dominant frequency and modes
    """
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)
    q = f'SELECT * FROM "fft_summary" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT {limit}'
    res = list(client.query(q).get_points())
    return res[::-1] if res else []

@app.get("/analysis/fft/{signal_id}/spectrum")
def get_fft_spectrum(signal_id: str, limit: int = 512):
    """
    Get detailed FFT spectrum for a signal.

    Args:
        signal_id: Signal identifier
        limit: Number of frequency bins to return

    Returns:
        List of frequency-magnitude pairs for plotting
    """
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)
    # Get most recent timestamp first
    q_time = f'SELECT * FROM "fft_spectrum" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT 1'
    time_res = list(client.query(q_time).get_points())

    if not time_res:
        return []

    latest_time = time_res[0]['time']
    # Get all spectrum points at that timestamp (InfluxDB 1.x only supports ORDER BY time)
    q = f'SELECT "frequency","magnitude" FROM "fft_spectrum" WHERE "signal_id"=\'{signal_id}\' AND time=\'{latest_time}\' LIMIT {limit}'
    res = list(client.query(q).get_points())

    # Sort by frequency in Python since InfluxDB 1.x doesn't support ORDER BY on non-time fields
    res.sort(key=lambda x: x.get('frequency', 0))
    return res

@app.get("/analysis/snr/{signal_id}")
def get_snr_metrics(signal_id: str, limit: int = 20):
    """
    Get SNR quality metrics for a signal.

    Args:
        signal_id: Signal identifier
        limit: Number of recent measurements

    Returns:
        List of SNR metrics with quality ratings
    """
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)
    q = f'SELECT * FROM "snr_metrics" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT {limit}'
    res = list(client.query(q).get_points())
    return res[::-1] if res else []

@app.get("/analysis/oscillations")
def get_oscillation_events(limit: int = 50, detected_only: bool = True):
    """
    Get oscillation detection events.

    Args:
        limit: Maximum number of events to return
        detected_only: If True, only return detected oscillations

    Returns:
        List of oscillation events with frequency and damping info
    """
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)

    if detected_only:
        q = f'SELECT * FROM "oscillation_alerts" ORDER BY time DESC LIMIT {limit}'
    else:
        q = f'SELECT * FROM "oscillation_events" ORDER BY time DESC LIMIT {limit}'

    res = list(client.query(q).get_points())
    return res[::-1] if res else []

@app.get("/analysis/oscillations/{signal_id}")
def get_oscillation_by_signal(signal_id: str, limit: int = 20):
    """
    Get oscillation events for a specific signal.

    Args:
        signal_id: Signal identifier
        limit: Number of recent events

    Returns:
        List of oscillation events
    """
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)
    q = f'SELECT * FROM "oscillation_events" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT {limit}'
    res = list(client.query(q).get_points())
    return res[::-1] if res else []

@app.get("/analysis/faults")
def get_fault_events(
    limit: int = 50,
    severity: str = Query(None, description="Filter by severity: critical, high, medium, low")
):
    """
    Get fault detection events.

    Args:
        limit: Maximum number of events to return
        severity: Optional severity filter

    Returns:
        List of fault events with deviation details
    """
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)

    if severity:
        q = f'SELECT * FROM "fault_events" WHERE "severity"=\'{severity}\' ORDER BY time DESC LIMIT {limit}'
    else:
        q = f'SELECT * FROM "fault_events" ORDER BY time DESC LIMIT {limit}'

    res = list(client.query(q).get_points())
    return res[::-1] if res else []

@app.get("/analysis/summary/{signal_id}")
def get_analysis_summary(signal_id: str):
    """
    Get comprehensive analysis summary for a signal.

    Args:
        signal_id: Signal identifier

    Returns:
        Dict containing latest FFT, SNR, oscillation, and quality metrics
    """
    summary = {
        "signal_id": signal_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # Get latest FFT
    fft = analysis_manager.get_latest_fft(signal_id)
    summary["fft"] = fft if fft else None

    # Get latest SNR
    snr = analysis_manager.get_latest_snr(signal_id)
    summary["snr"] = snr if snr else None

    # Get recent oscillations
    client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)
    q_osc = f'SELECT * FROM "oscillation_events" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT 1'
    osc_res = list(client.query(q_osc).get_points())
    summary["oscillation"] = osc_res[0] if osc_res else None

    return summary

@app.get("/analysis/health")
def get_analysis_health():
    """
    Get health status of analysis system.

    Returns:
        Status of analysis manager and recent activity
    """
    return {
        "status": "running" if analysis_manager.running else "stopped",
        "analysis_interval": ANALYSIS_INTERVAL,
        "sample_rate": ANALYSIS_SAMPLE_RATE,
        "monitored_signals": list(SIGNALS.keys()),
        "analysis_db": ANALYSIS_DB
    }

# ---- Warning System Endpoints ----

def _serialize_warning_event(event: WarningEvent) -> Dict[str, Any]:
    """Convert WarningEvent to JSON-serializable dict"""
    return {
        "event_id": event.event_id,
        "signal_id": event.signal_id,
        "signal_type": event.signal_type,
        "severity": event.severity.name if hasattr(event.severity, 'name') else str(event.severity),
        "state": event.state.value if hasattr(event.state, 'value') else str(event.state),
        "threshold_type": event.threshold_type,
        "threshold_value": event.threshold_value,
        "trigger_value": event.trigger_value,
        "first_trigger_time": event.first_trigger_time.isoformat() if event.first_trigger_time else None,
        "event_start_time": event.event_start_time.isoformat() if event.event_start_time else None,
        "event_end_time": event.event_end_time.isoformat() if event.event_end_time else None,
        "duration": event.duration,
        "trigger_count": event.trigger_count,
        "max_deviation": event.max_deviation,
        "is_active": event.state.value == "active" if hasattr(event.state, 'value') else False,
        "message": event.message,
        "acknowledged": event.acknowledged,
        "acknowledged_by": event.acknowledged_by,
        "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None
    }

@app.get("/warnings/active")
def get_active_warnings():
    """
    Get all currently active warnings (real-time layer).

    Returns:
        List of active warning events with sub-second refresh capability
    """
    try:
        events = warning_manager.get_active_warnings()
        return [_serialize_warning_event(e) for e in events]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve active warnings: {str(e)}")

@app.get("/warnings/historical")
def get_historical_warnings(
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    signal_id: Optional[str] = Query(None, description="Filter by signal ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warning"),
    limit: int = Query(100, description="Maximum number of events")
):
    """
    Query historical warnings from storage layer.

    Args:
        start_time: Start of time range (ISO format)
        end_time: End of time range (ISO format)
        signal_id: Optional signal filter
        severity: Optional severity filter
        limit: Maximum results

    Returns:
        List of historical warning events
    """
    try:
        # Convert time strings to datetime if provided
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        events = warning_manager.query_historical(
            start_time=start_dt,
            end_time=end_dt,
            signal_id=signal_id,
            severity=severity,
            limit=limit
        )
        return [_serialize_warning_event(e) for e in events]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query historical warnings: {str(e)}")

@app.get("/warnings/stats")
def get_warning_stats():
    """
    Get warning system statistics and performance metrics.

    Returns:
        Statistics including active count, total events, performance metrics
    """
    try:
        stats = warning_manager.get_statistics()
        return {
            "active_warnings": stats["active_count"],
            "total_events_today": stats["total_events"],
            "performance": {
                "avg_check_time_ms": stats["avg_check_time_ms"],
                "max_check_time_ms": stats["max_check_time_ms"],
                "total_checks": stats["total_checks"],
                "checks_per_second": stats["checks_per_second"]
            },
            "by_severity": stats["by_severity"],
            "by_signal": stats["by_signal"],
            "realtime_layer_status": "running" if warning_manager.realtime_layer else "stopped",
            "storage_layer_status": "running" if warning_manager.storage_layer.running else "stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve warning statistics: {str(e)}")

@app.post("/warnings/thresholds")
def update_thresholds(thresholds: List[Dict[str, Any]]):
    """
    Update warning thresholds (user-configurable from frontend).

    Args:
        thresholds: List of threshold configurations

    Example payload:
    [
        {
            "signal_id": "PPA:2",
            "signal_type": "frequency",
            "warning_min": 59.85,
            "warning_max": 60.15,
            "critical_min": 59.5,
            "critical_max": 60.5,
            "trigger_count": 3,
            "trigger_window": 5.0,
            "recovery_count": 2,
            "recovery_window": 3.0
        }
    ]

    Returns:
        Status of threshold update
    """
    try:
        # Convert dicts to ThresholdConfig objects
        threshold_configs = []
        for t in thresholds:
            config = ThresholdConfig(
                signal_id=t["signal_id"],
                signal_type=t["signal_type"],
                warning_min=t.get("warning_min"),
                warning_max=t.get("warning_max"),
                critical_min=t.get("critical_min"),
                critical_max=t.get("critical_max"),
                trigger_count=t.get("trigger_count", 3),
                trigger_window=t.get("trigger_window", 5.0),
                recovery_count=t.get("recovery_count", 2),
                recovery_window=t.get("recovery_window", 3.0),
                min_event_duration=t.get("min_event_duration", 1.0)
            )
            threshold_configs.append(config)

        # Update thresholds (this will reinitialize the warning manager)
        warning_manager.update_thresholds(threshold_configs)

        return {
            "status": "success",
            "message": f"Updated {len(threshold_configs)} threshold configurations",
            "thresholds": [{"signal_id": c.signal_id, "signal_type": c.signal_type} for c in threshold_configs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update thresholds: {str(e)}")

@app.post("/warnings/{event_id}/acknowledge")
def acknowledge_warning(event_id: str, user: str = Query("system", description="User acknowledging the warning")):
    """
    Acknowledge a warning event.

    Args:
        event_id: Warning event ID to acknowledge
        user: Username of person acknowledging

    Returns:
        Status of acknowledgment
    """
    try:
        success = warning_manager.acknowledge_event(event_id, user)
        if success:
            return {
                "status": "success",
                "message": f"Event {event_id} acknowledged by {user}",
                "event_id": event_id,
                "acknowledged_by": user,
                "ack_time": datetime.utcnow().isoformat() + "Z"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge warning: {str(e)}")

@app.post("/warnings/check")
def manual_check_value(signal_id: str, value: float):
    """
    Manually check a value against thresholds (for testing).

    Args:
        signal_id: Signal identifier
        value: Value to check

    Returns:
        Check result and any triggered events
    """
    try:
        event = warning_manager.check_value(signal_id, value)
        if event:
            return {
                "status": "event_triggered",
                "event": _serialize_warning_event(event)
            }
        else:
            return {
                "status": "normal",
                "message": f"Value {value} is within normal range for {signal_id}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check value: {str(e)}")
