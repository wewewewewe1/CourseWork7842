# =======================
# oscillation_detector.py
# =======================
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
from typing import Dict, List
from datetime import datetime, timezone
import warnings

class OscillationDetector:
    """
    Detects inter-area oscillations in PMU data (0.2 - 2.5 Hz range).

    Power system oscillations in this frequency range indicate:
    - Inter-area oscillation modes (0.1 - 0.8 Hz)
    - Local oscillation modes (0.8 - 2.5 Hz)
    - Potential grid stability issues
    """

    def __init__(self,
                 sample_rate: float = 20.0,
                 freq_min: float = 0.2,
                 freq_max: float = 2.5,
                 window_size: int = 512,
                 threshold_multiplier: float = 3.0):
        """
        Args:
            sample_rate: Sampling frequency in Hz
            freq_min: Lower bound of oscillation range (Hz)
            freq_max: Upper bound of oscillation range (Hz)
            window_size: FFT window size
            threshold_multiplier: Detection threshold (multiple of baseline power)
        """
        self.sample_rate = sample_rate
        self.freq_min = freq_min
        self.freq_max = freq_max
        self.window_size = window_size
        self.threshold_multiplier = threshold_multiplier

        # ==============================
        # ✅ Design safe bandpass filter
        # ==============================
        nyquist = sample_rate / 2.0
        low = freq_min / nyquist
        high = freq_max / nyquist

        # Prevent invalid range
        if high >= 1.0 or low <= 0.0 or low >= high:
            warnings.warn(
                f"[OscillationDetector] Invalid filter range ({low:.3f}, {high:.3f}) "
                f"for sample_rate={sample_rate}. Adjusting automatically.",
                RuntimeWarning
            )
            # Clamp safely within (0, 1)
            low = max(0.001, min(low, 0.99))
            high = max(low + 0.001, min(high, 0.999))
            if high <= low:
                # Fallback default safe band (0.05–0.45 Nyquist)
                low, high = 0.05, 0.45

        self.bandpass_filter = signal.butter(4, [low, high], btype='band', output='sos')
        print(f"[OscillationDetector] Bandpass filter initialized: low={low:.3f}, high={high:.3f} (normalized)")

    # ==========================================================
    # Oscillation detection main function
    # ==========================================================
    def detect(self, data: List[float], timestamps: List[float] = None) -> Dict:
        if len(data) < self.window_size:
            return {
                "oscillation_detected": False,
                "error": "Insufficient data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        signal_data = np.array(data[-self.window_size:], dtype=float)
        signal_data = signal_data - np.mean(signal_data)

        # Apply bandpass filter
        filtered = signal.sosfilt(self.bandpass_filter, signal_data)

        # Hilbert transform for envelope
        analytic_signal = signal.hilbert(filtered)
        envelope = np.abs(analytic_signal)

        oscillation_power = np.mean(filtered ** 2)
        baseline_power = np.mean(signal_data ** 2) - oscillation_power
        threshold = baseline_power * self.threshold_multiplier
        oscillation_detected = oscillation_power > threshold

        # FFT to find dominant frequency
        fft_result = fft(filtered * np.hamming(len(filtered)))
        n = len(filtered) // 2
        frequencies = fftfreq(len(filtered), d=1.0 / self.sample_rate)[:n]
        magnitudes = np.abs(fft_result[:n])

        mask = (frequencies >= self.freq_min) & (frequencies <= self.freq_max)
        if np.any(mask):
            band_magnitudes = magnitudes[mask]
            band_frequencies = frequencies[mask]
            dominant_idx = np.argmax(band_magnitudes)
            oscillation_freq = float(band_frequencies[dominant_idx])
            oscillation_magnitude = float(band_magnitudes[dominant_idx])
        else:
            oscillation_freq = 0.0
            oscillation_magnitude = 0.0

        # Classify type
        if oscillation_detected:
            osc_type = "inter-area" if oscillation_freq < 0.8 else "local"
        else:
            osc_type = "none"

        damping_ratio = self._estimate_damping(envelope)

        return {
            "oscillation_detected": bool(oscillation_detected),
            "oscillation_frequency": oscillation_freq,
            "oscillation_magnitude": oscillation_magnitude,
            "oscillation_type": osc_type,
            "oscillation_power": float(oscillation_power),
            "baseline_power": float(baseline_power),
            "threshold": float(threshold),
            "damping_ratio": float(damping_ratio),
            "filtered_signal": filtered.tolist(),
            "envelope": envelope.tolist(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "freq_range": [self.freq_min, self.freq_max]
        }

    # ==========================================================
    # Helper: Estimate damping ratio
    # ==========================================================
    def _estimate_damping(self, envelope: np.ndarray) -> float:
        if len(envelope) < 10:
            return 0.0

        peaks, _ = signal.find_peaks(envelope, distance=5)
        if len(peaks) < 2:
            return 0.0

        try:
            peak_values = envelope[peaks]
            time_indices = np.arange(len(peak_values))
            log_peaks = np.log(peak_values + 1e-10)
            coeffs = np.polyfit(time_indices, log_peaks, 1)
            decay_rate = -coeffs[0]
            damping = decay_rate / np.sqrt(decay_rate ** 2 + (2 * np.pi) ** 2)
            return float(np.clip(damping, 0.0, 1.0))
        except Exception:
            return 0.0

    # ==========================================================
    # Convert detection result to InfluxDB points
    # ==========================================================
    def to_influx_points(self, signal_id: str, detection_result: Dict) -> List[Dict]:
        if "error" in detection_result:
            return []

        points = [{
            "measurement": "oscillation_events",
            "tags": {
                "signal_id": signal_id,
                "oscillation_type": detection_result["oscillation_type"],
                "detected": str(detection_result["oscillation_detected"])
            },
            "fields": {
                "oscillation_frequency": detection_result["oscillation_frequency"],
                "oscillation_magnitude": detection_result["oscillation_magnitude"],
                "oscillation_power": detection_result["oscillation_power"],
                "baseline_power": detection_result["baseline_power"],
                "threshold": detection_result["threshold"],
                "damping_ratio": detection_result["damping_ratio"]
            },
            "time": detection_result["timestamp"]
        }]

        if detection_result["oscillation_detected"]:
            points.append({
                "measurement": "oscillation_alerts",
                "tags": {
                    "signal_id": signal_id,
                    "severity": "high" if detection_result["damping_ratio"] < 0.05 else "medium"
                },
                "fields": {
                    "frequency": detection_result["oscillation_frequency"],
                    "magnitude": detection_result["oscillation_magnitude"],
                    "type": detection_result["oscillation_type"],
                    "damping": detection_result["damping_ratio"],
                    "message": f"{detection_result['oscillation_type']} oscillation at {detection_result['oscillation_frequency']:.2f} Hz"
                },
                "time": detection_result["timestamp"]
            })

        return points
