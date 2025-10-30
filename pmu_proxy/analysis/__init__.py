# =======================
# analysis/__init__.py
# =======================
"""
PMU Signal Analysis Module

Provides advanced signal processing and event detection for PMU data:
- FFT frequency-domain analysis
- Inter-area oscillation detection (0.2-2.5 Hz)
- Signal-to-Noise Ratio (SNR) estimation
- Fault detection (voltage sag/swell, frequency deviations)
- Arcing detection (high-frequency transients)
"""

from .fft_analyzer import FFTAnalyzer
from .oscillation_detector import OscillationDetector
from .snr_estimator import SNREstimator
from .fault_detector import FaultDetector
from .analysis_manager import AnalysisManager

__all__ = [
    "FFTAnalyzer",
    "OscillationDetector",
    "SNREstimator",
    "FaultDetector",
    "ArcingDetector",
    "AnalysisManager"
]

__version__ = "1.0.0"
