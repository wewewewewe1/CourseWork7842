# =======================
# fft_analyzer.py
# =======================
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
from typing import Dict, List, Tuple
from datetime import datetime, timezone

class FFTAnalyzer:
    """
    FFT-based frequency-domain analyzer for PMU signals.

    Features:
    - Computes FFT spectrum with configurable window size
    - Identifies dominant frequency modes
    - Uses Hamming window to reduce spectral leakage
    - Outputs frequency bins and magnitudes
    """

    def __init__(self, sample_rate: float = 20.0, window_size: int = 512):
        """
        Args:
            sample_rate: Sampling frequency in Hz (default: 20 Hz for PMU)
            window_size: Number of samples for FFT (must be power of 2)
        """
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.nyquist_freq = sample_rate / 2.0

    def analyze(self, data: List[float], timestamps: List[float] = None) -> Dict:
        """
        Perform FFT analysis on time-series data.

        Args:
            data: List of signal values
            timestamps: Optional list of timestamps (for metadata)

        Returns:
            Dict containing:
                - frequencies: Frequency bins (Hz)
                - magnitudes: FFT magnitude spectrum
                - dominant_freq: Most prominent frequency
                - dominant_magnitude: Magnitude at dominant frequency
                - timestamp: Analysis timestamp
                - power_spectrum: Power spectral density
        """
        if len(data) < self.window_size:
            # Pad with zeros if insufficient data
            data = list(data) + [0] * (self.window_size - len(data))
        elif len(data) > self.window_size:
            # Use most recent window
            data = data[-self.window_size:]

        # Convert to numpy array
        signal_data = np.array(data, dtype=float)

        # Remove DC component (mean)
        signal_data = signal_data - np.mean(signal_data)

        # Apply Hamming window to reduce spectral leakage
        window = np.hamming(self.window_size)
        windowed_signal = signal_data * window

        # Compute FFT
        fft_result = fft(windowed_signal)

        # Get positive frequencies only (Nyquist)
        n = self.window_size // 2
        frequencies = fftfreq(self.window_size, d=1.0/self.sample_rate)[:n]

        # Compute magnitude spectrum
        magnitudes = np.abs(fft_result[:n]) * 2.0 / self.window_size

        # Compute power spectral density
        power_spectrum = magnitudes ** 2

        # Find dominant frequency (excluding DC - start from index 1)
        if len(magnitudes) > 1:
            dominant_idx = np.argmax(magnitudes[1:]) + 1
            dominant_freq = frequencies[dominant_idx]
            dominant_mag = magnitudes[dominant_idx]
        else:
            dominant_freq = 0.0
            dominant_mag = 0.0

        # Find top 5 dominant modes
        top_indices = np.argsort(magnitudes[1:])[-5:][::-1] + 1
        dominant_modes = [
            {"frequency": float(frequencies[i]), "magnitude": float(magnitudes[i])}
            for i in top_indices
        ]

        return {
            "frequencies": frequencies.tolist(),
            "magnitudes": magnitudes.tolist(),
            "power_spectrum": power_spectrum.tolist(),
            "dominant_freq": float(dominant_freq),
            "dominant_magnitude": float(dominant_mag),
            "dominant_modes": dominant_modes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sample_rate": self.sample_rate,
            "window_size": self.window_size,
            "nyquist_freq": self.nyquist_freq
        }

    def get_frequency_band_power(self, data: List[float],
                                  freq_min: float, freq_max: float) -> float:
        """
        Calculate total power in a specific frequency band.

        Args:
            data: Signal values
            freq_min: Lower frequency bound (Hz)
            freq_max: Upper frequency bound (Hz)

        Returns:
            Total power in the specified band
        """
        result = self.analyze(data)
        frequencies = np.array(result["frequencies"])
        power = np.array(result["power_spectrum"])

        # Find indices in frequency band
        mask = (frequencies >= freq_min) & (frequencies <= freq_max)
        band_power = np.sum(power[mask])

        return float(band_power)

    def to_influx_points(self, signal_id: str, analysis_result: Dict) -> List[Dict]:
        """
        Convert FFT analysis results to InfluxDB points.

        Args:
            signal_id: PMU signal identifier
            analysis_result: Output from analyze()

        Returns:
            List of InfluxDB point dictionaries
        """
        points = []

        # Store dominant frequency as a summary point
        points.append({
            "measurement": "fft_summary",
            "tags": {
                "signal_id": signal_id,
            },
            "fields": {
                "dominant_freq": analysis_result["dominant_freq"],
                "dominant_magnitude": analysis_result["dominant_magnitude"],
                "sample_rate": analysis_result["sample_rate"],
                "window_size": analysis_result["window_size"]
            },
            "time": analysis_result["timestamp"]
        })

        # Store full spectrum (for frontend visualization)
        frequencies = analysis_result["frequencies"]
        magnitudes = analysis_result["magnitudes"]

        # Store all frequency components (needed for proper spectrum visualization)
        # Note: Only storing positive frequencies (up to Nyquist)
        for freq, mag in zip(frequencies, magnitudes):
            points.append({
                "measurement": "fft_spectrum",
                "tags": {
                    "signal_id": signal_id,
                },
                "fields": {
                    "frequency": freq,
                    "magnitude": mag
                },
                "time": analysis_result["timestamp"]
            })

        # Store dominant modes
        for mode in analysis_result["dominant_modes"]:
            points.append({
                "measurement": "fft_dominant_modes",
                "tags": {
                    "signal_id": signal_id,
                },
                "fields": {
                    "frequency": mode["frequency"],
                    "magnitude": mode["magnitude"]
                },
                "time": analysis_result["timestamp"]
            })

        return points
