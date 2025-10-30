# =======================
# snr_estimator.py
# =======================
import numpy as np
from scipy import signal
from typing import Dict, List
from datetime import datetime, timezone

class SNREstimator:
    """
    Estimates Signal-to-Noise Ratio (SNR) for PMU data quality assessment.

    Methods:
    - Frequency-domain SNR (signal power vs. noise floor)
    - Time-domain SNR (signal variance vs. noise variance)
    - SINAD (Signal-to-Noise-and-Distortion)
    """

    def __init__(self, sample_rate: float = 20.0, window_size: int = 512):
        """
        Args:
            sample_rate: Sampling frequency in Hz
            window_size: Window size for analysis
        """
        self.sample_rate = sample_rate
        self.window_size = window_size

    def estimate(self, data: List[float], expected_freq: float = None) -> Dict:
        """
        Estimate SNR using multiple methods.

        Args:
            data: Signal values
            expected_freq: Expected fundamental frequency (e.g., 60 Hz for power systems)

        Returns:
            Dict containing:
                - snr_db: SNR in decibels (frequency-domain method)
                - snr_linear: SNR as linear ratio
                - signal_power: Estimated signal power
                - noise_power: Estimated noise power
                - quality: Quality rating (excellent/good/fair/poor)
                - timestamp: Measurement timestamp
        """
        if len(data) < self.window_size:
            return {
                "error": "Insufficient data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Use most recent window
        signal_data = np.array(data[-self.window_size:], dtype=float)

        # Remove DC component
        signal_mean = np.mean(signal_data)
        signal_data = signal_data - signal_mean

        # Frequency-domain SNR estimation
        snr_freq, signal_power, noise_power = self._estimate_frequency_domain(
            signal_data, expected_freq
        )

        # Time-domain SNR estimation (detrended)
        snr_time = self._estimate_time_domain(signal_data)

        # Combined SNR (average of methods)
        snr_db = (snr_freq + snr_time) / 2.0
        snr_linear = 10 ** (snr_db / 10.0)

        # Quality classification
        if snr_db > 40:
            quality = "excellent"
        elif snr_db > 30:
            quality = "good"
        elif snr_db > 20:
            quality = "fair"
        else:
            quality = "poor"

        # Calculate Total Harmonic Distortion (THD)
        thd = self._calculate_thd(signal_data, expected_freq)

        result = {
            "snr_db": float(snr_db),
            "snr_linear": float(snr_linear),
            "snr_freq_db": float(snr_freq),
            "snr_time_db": float(snr_time),
            "signal_power": float(signal_power),
            "noise_power": float(noise_power),
            "thd_percent": float(thd * 100),
            "quality": quality,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dc_offset": float(signal_mean)
        }

        return result

    def _estimate_frequency_domain(self, data: np.ndarray, expected_freq: float = None) -> tuple:
        """
        Estimate SNR using frequency-domain analysis.

        Separates signal power (in fundamental and harmonics) from noise floor.

        Args:
            data: Detrended signal data
            expected_freq: Expected fundamental frequency

        Returns:
            (snr_db, signal_power, noise_power)
        """
        # Apply window and FFT
        windowed = data * np.hamming(len(data))
        fft_result = np.fft.fft(windowed)
        n = len(data) // 2
        power_spectrum = (np.abs(fft_result[:n]) ** 2) / len(data)
        frequencies = np.fft.fftfreq(len(data), d=1.0/self.sample_rate)[:n]

        if expected_freq is not None:
            # Find bins corresponding to fundamental and harmonics
            signal_bins = set()
            for harmonic in range(1, 6):  # Include first 5 harmonics
                harmonic_freq = expected_freq * harmonic
                # Find closest bin
                idx = np.argmin(np.abs(frequencies - harmonic_freq))
                # Include ±2 bins around peak
                for offset in range(-2, 3):
                    if 0 <= idx + offset < len(power_spectrum):
                        signal_bins.add(idx + offset)

            # Calculate signal and noise power
            signal_power = sum(power_spectrum[i] for i in signal_bins)
            noise_bins = set(range(len(power_spectrum))) - signal_bins
            noise_power = sum(power_spectrum[i] for i in noise_bins) / max(len(noise_bins), 1)
        else:
            # Use top 5% of power as signal, rest as noise
            sorted_power = np.sort(power_spectrum)
            threshold_idx = int(0.95 * len(sorted_power))
            signal_power = np.sum(sorted_power[threshold_idx:])
            noise_power = np.mean(sorted_power[:threshold_idx])

        # Avoid division by zero
        if noise_power < 1e-12:
            noise_power = 1e-12

        snr_linear = signal_power / noise_power
        snr_db = 10 * np.log10(snr_linear)

        return snr_db, signal_power, noise_power

    def _estimate_time_domain(self, data: np.ndarray) -> float:
        """
        Estimate SNR using time-domain analysis.

        Fits a smooth curve to data and treats residuals as noise.

        Args:
            data: Detrended signal data

        Returns:
            SNR in dB
        """
        # Smooth signal using Savitzky-Golay filter
        try:
            smoothed = signal.savgol_filter(data, window_length=min(51, len(data)//2*2-1), polyorder=3)
        except Exception:
            # Fallback to simple moving average
            window = min(20, len(data) // 10)
            smoothed = np.convolve(data, np.ones(window)/window, mode='same')

        # Signal is the smoothed version, noise is the residual
        signal_power = np.mean(smoothed ** 2)
        noise = data - smoothed
        noise_power = np.mean(noise ** 2)

        if noise_power < 1e-12:
            noise_power = 1e-12

        snr_linear = signal_power / noise_power
        snr_db = 10 * np.log10(snr_linear)

        return snr_db

    def _calculate_thd(self, data: np.ndarray, fundamental_freq: float = None) -> float:
        """
        Calculate Total Harmonic Distortion (THD).

        Args:
            data: Signal data
            fundamental_freq: Fundamental frequency (Hz)

        Returns:
            THD as ratio (not percentage)
        """
        if fundamental_freq is None:
            return 0.0

        # FFT
        fft_result = np.fft.fft(data * np.hamming(len(data)))
        n = len(data) // 2
        magnitudes = np.abs(fft_result[:n])
        frequencies = np.fft.fftfreq(len(data), d=1.0/self.sample_rate)[:n]

        # Find fundamental
        fund_idx = np.argmin(np.abs(frequencies - fundamental_freq))
        fundamental_mag = magnitudes[fund_idx]

        # Find harmonics (2nd through 5th)
        harmonic_power = 0.0
        for h in range(2, 6):
            harmonic_freq = fundamental_freq * h
            harm_idx = np.argmin(np.abs(frequencies - harmonic_freq))
            harmonic_power += magnitudes[harm_idx] ** 2

        if fundamental_mag < 1e-12:
            return 0.0

        thd = np.sqrt(harmonic_power) / fundamental_mag
        return thd

    def to_influx_points(self, signal_id: str, snr_result: Dict) -> List[Dict]:
        """
        Convert SNR estimation results to InfluxDB points.

        Args:
            signal_id: PMU signal identifier
            snr_result: Output from estimate()

        Returns:
            List of InfluxDB point dictionaries
        """
        if "error" in snr_result:
            return []

        return [{
            "measurement": "snr_metrics",
            "tags": {
                "signal_id": signal_id,
                "quality": snr_result["quality"]
            },
            "fields": {
                "snr_db": snr_result["snr_db"],
                "snr_linear": snr_result["snr_linear"],
                "snr_freq_db": snr_result["snr_freq_db"],
                "snr_time_db": snr_result["snr_time_db"],
                "signal_power": snr_result["signal_power"],
                "noise_power": snr_result["noise_power"],
                "thd_percent": snr_result["thd_percent"],
                "dc_offset": snr_result["dc_offset"]
            },
            "time": snr_result["timestamp"]
        }]
