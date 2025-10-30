# =======================
# fault_detector.py
# =======================
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import deque

class FaultDetector:
    """
    Detects faults and sudden changes in PMU data.

    Fault types:
    - Voltage sag/swell (> 5% deviation)
    - Sudden frequency changes
    - Transient spikes
    - Rate-of-change anomalies
    """

    def __init__(self,
                 voltage_threshold: float = 0.05,
                 frequency_threshold: float = 0.1,
                 rate_threshold: float = 0.5,
                 buffer_size: int = 100):
        """
        Args:
            voltage_threshold: Voltage deviation threshold (ratio, e.g., 0.05 = 5%)
            frequency_threshold: Frequency deviation threshold (Hz)
            rate_threshold: Maximum rate of change per sample (ratio)
            buffer_size: Number of samples to maintain for baseline
        """
        self.voltage_threshold = voltage_threshold
        self.frequency_threshold = frequency_threshold
        self.rate_threshold = rate_threshold
        self.buffer_size = buffer_size

        # Maintain history for baseline calculation
        self.baseline_buffer = deque(maxlen=buffer_size)
        self.last_value = None
        self.fault_active = False
        self.fault_start_time = None

    def detect(self, value: float, timestamp: str,
               signal_type: str = "voltage",
               baseline: Optional[float] = None) -> Dict:
        """
        Detect faults in a single data point.

        Args:
            value: Current signal value
            timestamp: Timestamp of measurement
            signal_type: Type of signal ("voltage", "frequency", "current")
            baseline: Expected baseline value (if None, computed from history)

        Returns:
            Dict containing:
                - fault_detected: Boolean flag
                - fault_type: Type of fault detected
                - deviation: Absolute deviation from baseline
                - deviation_ratio: Relative deviation
                - rate_of_change: Change rate from previous sample
                - severity: Fault severity (low/medium/high/critical)
                - timestamp: Detection timestamp
        """
        # Update baseline buffer
        self.baseline_buffer.append(value)

        # Calculate baseline if not provided
        if baseline is None and len(self.baseline_buffer) >= 10:
            baseline = np.median(list(self.baseline_buffer))
        elif baseline is None:
            # Insufficient data for baseline
            self.last_value = value
            return {
                "fault_detected": False,
                "message": "Building baseline",
                "timestamp": timestamp
            }

        # Calculate deviation
        deviation = value - baseline
        deviation_ratio = abs(deviation / baseline) if baseline != 0 else 0

        # Calculate rate of change
        if self.last_value is not None:
            rate_of_change = abs(value - self.last_value) / baseline if baseline != 0 else 0
        else:
            rate_of_change = 0

        self.last_value = value

        # Fault detection logic
        fault_detected = False
        fault_type = "none"
        severity = "normal"

        if signal_type in ["voltage", "current"]:
            if deviation_ratio > self.voltage_threshold:
                fault_detected = True
                if deviation > 0:
                    fault_type = "swell" if signal_type == "voltage" else "overcurrent"
                else:
                    fault_type = "sag" if signal_type == "voltage" else "undercurrent"

                # Severity based on deviation magnitude
                if deviation_ratio > 0.2:
                    severity = "critical"
                elif deviation_ratio > 0.1:
                    severity = "high"
                elif deviation_ratio > 0.05:
                    severity = "medium"
                else:
                    severity = "low"

        elif signal_type == "frequency":
            if abs(deviation) > self.frequency_threshold:
                fault_detected = True
                fault_type = "frequency_deviation"
                if abs(deviation) > 0.5:
                    severity = "critical"
                elif abs(deviation) > 0.3:
                    severity = "high"
                elif abs(deviation) > 0.15:
                    severity = "medium"
                else:
                    severity = "low"

        # Check for excessive rate of change (transient)
        if rate_of_change > self.rate_threshold:
            fault_detected = True
            fault_type = "transient" if fault_type == "none" else f"{fault_type}_transient"
            severity = "high"

        # Update fault state
        if fault_detected and not self.fault_active:
            self.fault_active = True
            self.fault_start_time = timestamp
        elif not fault_detected and self.fault_active:
            self.fault_active = False
            self.fault_start_time = None

        result = {
            "fault_detected": fault_detected,
            "fault_type": fault_type,
            "signal_type": signal_type,
            "value": float(value),
            "baseline": float(baseline),
            "deviation": float(deviation),
            "deviation_ratio": float(deviation_ratio),
            "rate_of_change": float(rate_of_change),
            "severity": severity,
            "fault_active": self.fault_active,
            "timestamp": timestamp
        }

        return result

    def detect_batch(self, data: List[float],
                     timestamps: List[str],
                     signal_type: str = "voltage",
                     baseline: Optional[float] = None) -> List[Dict]:
        """
        Detect faults in a batch of data points.

        Args:
            data: List of signal values
            timestamps: List of timestamps
            signal_type: Type of signal
            baseline: Expected baseline value

        Returns:
            List of fault detection results
        """
        results = []
        for value, timestamp in zip(data, timestamps):
            result = self.detect(value, timestamp, signal_type, baseline)
            results.append(result)

        return results

    def to_influx_points(self, signal_id: str, detection_result: Dict) -> List[Dict]:
        """
        Convert fault detection results to InfluxDB points.

        Only stores points where faults are detected.

        Args:
            signal_id: PMU signal identifier
            detection_result: Output from detect()

        Returns:
            List of InfluxDB point dictionaries
        """
        if not detection_result.get("fault_detected", False):
            return []

        return [{
            "measurement": "fault_events",
            "tags": {
                "signal_id": signal_id,
                "fault_type": detection_result["fault_type"],
                "signal_type": detection_result["signal_type"],
                "severity": detection_result["severity"]
            },
            "fields": {
                "value": detection_result["value"],
                "baseline": detection_result["baseline"],
                "deviation": detection_result["deviation"],
                "deviation_ratio": detection_result["deviation_ratio"],
                "rate_of_change": detection_result["rate_of_change"],
                "message": f"{detection_result['fault_type']} detected: {detection_result['deviation_ratio']*100:.1f}% deviation"
            },
            "time": detection_result["timestamp"]
        }]

    def reset(self):
        """Reset detector state and baseline buffer."""
        self.baseline_buffer.clear()
        self.last_value = None
        self.fault_active = False
        self.fault_start_time = None
