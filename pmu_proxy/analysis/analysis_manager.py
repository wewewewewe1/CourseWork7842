# =======================
# analysis_manager.py
# =======================
import time
from threading import Thread
from datetime import datetime, timezone
from influxdb import InfluxDBClient
from typing import Dict, List
from collections import deque

from .fft_analyzer import FFTAnalyzer
from .oscillation_detector import OscillationDetector
from .snr_estimator import SNREstimator
from .fault_detector import FaultDetector

class AnalysisManager:
    """
    Coordinates all signal analysis modules.

    Features:
    - Asynchronous analysis execution
    - Configurable analysis intervals
    - Automatic result storage to InfluxDB
    - Buffer management for windowed analysis
    """

    def __init__(self,
                 influx_host: str = "127.0.0.1",
                 influx_port: int = 8086,
                 source_db: str = "pmu_data",
                 analysis_db: str = "pmu_analysis",
                 signals: Dict = None,
                 analysis_interval: float = 5.0,
                 sample_rate: float = 1.0):  # 1 Hz for simulated data
        """
        Args:
            influx_host: InfluxDB host
            influx_port: InfluxDB port
            source_db: Source database for PMU data
            analysis_db: Target database for analysis results
            signals: Signal configuration dict
            analysis_interval: How often to run analysis (seconds)
            sample_rate: Sampling rate of PMU data (Hz)
        """
        self.influx_host = influx_host
        self.influx_port = influx_port
        self.source_db = source_db
        self.analysis_db = analysis_db
        self.signals = signals or {}
        self.analysis_interval = analysis_interval
        self.sample_rate = sample_rate

        # Initialize InfluxDB clients
        self.src_client = InfluxDBClient(host=influx_host, port=influx_port, database=source_db)
        self.dst_client = InfluxDBClient(host=influx_host, port=influx_port, database=analysis_db)

        # Create analysis database if it doesn't exist
        self._ensure_database()

        # Initialize analyzers
        self.fft_analyzer = FFTAnalyzer(sample_rate=sample_rate, window_size=128)
        self.oscillation_detector = OscillationDetector(
            sample_rate=sample_rate,
            freq_min=0.2,
            freq_max=2.5,
            window_size=128
        )
        self.snr_estimator = SNREstimator(sample_rate=sample_rate, window_size=128)

        # Fault detectors per signal
        self.fault_detectors = {}
        for sig_id, sig_cfg in self.signals.items():
            if sig_cfg["type"] == "frequency":
                self.fault_detectors[sig_id] = FaultDetector(
                    frequency_threshold=0.1,
                    buffer_size=100
                )
            elif sig_cfg["type"] == "voltage":
                self.fault_detectors[sig_id] = FaultDetector(
                    voltage_threshold=0.05,
                    buffer_size=100
                )

        # Data buffers for windowed analysis
        self.data_buffers = {
            sig_id: deque(maxlen=256)  # Store last 256 samples
            for sig_id in self.signals.keys()
        }

        # Thread control
        self.running = False
        self.thread = None

        print("[ANALYSIS] Analysis Manager initialized")

    def _ensure_database(self):
        """Create analysis database if it doesn't exist."""
        try:
            databases = self.dst_client.get_list_database()
            db_names = [db['name'] for db in databases]
            if self.analysis_db not in db_names:
                self.dst_client.create_database(self.analysis_db)
                print(f"[ANALYSIS] Created database: {self.analysis_db}")
        except Exception as e:
            print(f"[ERROR] Failed to ensure database: {e}")

    def _fetch_recent_data(self, signal_id: str, limit: int = 256) -> List[Dict]:
        """
        Fetch recent data from source database.

        Args:
            signal_id: Signal measurement name
            limit: Number of recent points to fetch

        Returns:
            List of data points [{"time": ..., "value": ...}, ...]
        """
        try:
            q = f'SELECT "value","time" FROM "{signal_id}" ORDER BY time DESC LIMIT {limit}'
            result = self.src_client.query(q)
            points = list(result.get_points())
            return points[::-1]  # Reverse to chronological order
        except Exception as e:
            print(f"[ERROR] Failed to fetch data for {signal_id}: {e}")
            return []

    def _write_analysis_results(self, points: List[Dict]):
        """Write analysis results to InfluxDB."""
        if not points:
            return
        try:
            self.dst_client.write_points(points)
            # print(f"[ANALYSIS] Wrote {len(points)} analysis points")
        except Exception as e:
            print(f"[ERROR] Failed to write analysis results: {e}")

    def analyze_signal(self, signal_id: str):
        """
        Run all analysis modules on a single signal.

        Args:
            signal_id: Signal measurement name
        """
        # Fetch recent data
        data_points = self._fetch_recent_data(signal_id)

        if not data_points or len(data_points) < 10:
            # print(f"[ANALYSIS] Insufficient data for {signal_id}")
            return

        # Extract values and timestamps
        values = [float(pt["value"]) for pt in data_points]
        timestamps = [pt["time"] for pt in data_points]

        # Update buffer
        self.data_buffers[signal_id].extend(values)
        buffer_values = list(self.data_buffers[signal_id])

        # Get signal configuration
        sig_cfg = self.signals.get(signal_id, {})
        sig_type = sig_cfg.get("type", "unknown")
        baseline = sig_cfg.get("base")

        analysis_points = []

        # 1. FFT Analysis
        try:
            if len(buffer_values) >= 64:  # Minimum for meaningful FFT
                fft_result = self.fft_analyzer.analyze(buffer_values)
                analysis_points.extend(
                    self.fft_analyzer.to_influx_points(signal_id, fft_result)
                )
        except Exception as e:
            print(f"[ERROR] FFT analysis failed for {signal_id}: {e}")

        # 2. Oscillation Detection
        try:
            if len(buffer_values) >= 128:
                osc_result = self.oscillation_detector.detect(buffer_values)
                analysis_points.extend(
                    self.oscillation_detector.to_influx_points(signal_id, osc_result)
                )
        except Exception as e:
            print(f"[ERROR] Oscillation detection failed for {signal_id}: {e}")

        # 3. SNR Estimation
        try:
            if len(buffer_values) >= 128:
                expected_freq = 60.0 if sig_type == "frequency" else None
                snr_result = self.snr_estimator.estimate(buffer_values, expected_freq)
                analysis_points.extend(
                    self.snr_estimator.to_influx_points(signal_id, snr_result)
                )
        except Exception as e:
            print(f"[ERROR] SNR estimation failed for {signal_id}: {e}")

        # 4. Fault Detection (per-point)
        try:
            if signal_id in self.fault_detectors:
                detector = self.fault_detectors[signal_id]
                # Analyze most recent point
                latest_value = values[-1]
                latest_time = timestamps[-1]
                fault_result = detector.detect(
                    latest_value,
                    latest_time,
                    signal_type=sig_type,
                    baseline=baseline
                )
                analysis_points.extend(
                    detector.to_influx_points(signal_id, fault_result)
                )
        except Exception as e:
            print(f"[ERROR] Fault detection failed for {signal_id}: {e}")

        # Write all results
        self._write_analysis_results(analysis_points)

    def _analysis_loop(self):
        """Main analysis loop (runs in background thread)."""
        print("[ANALYSIS] Analysis loop started")
        while self.running:
            try:
                for signal_id in self.signals.keys():
                    self.analyze_signal(signal_id)
                time.sleep(self.analysis_interval)
            except Exception as e:
                print(f"[ERROR] Analysis loop error: {e}")
                time.sleep(self.analysis_interval)

    def start(self):
        """Start background analysis thread."""
        if self.running:
            print("[ANALYSIS] Already running")
            return

        self.running = True
        self.thread = Thread(target=self._analysis_loop, daemon=True)
        self.thread.start()
        print("[ANALYSIS] Background analysis started")

    def stop(self):
        """Stop background analysis thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[ANALYSIS] Background analysis stopped")

    def get_latest_fft(self, signal_id: str) -> Dict:
        """Get latest FFT results for a signal."""
        try:
            q = f'SELECT * FROM "fft_summary" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT 1'
            result = self.dst_client.query(q)
            points = list(result.get_points())
            return points[0] if points else {}
        except Exception as e:
            print(f"[ERROR] Failed to get FFT results: {e}")
            return {}

    def get_latest_snr(self, signal_id: str) -> Dict:
        """Get latest SNR metrics for a signal."""
        try:
            q = f'SELECT * FROM "snr_metrics" WHERE "signal_id"=\'{signal_id}\' ORDER BY time DESC LIMIT 1'
            result = self.dst_client.query(q)
            points = list(result.get_points())
            return points[0] if points else {}
        except Exception as e:
            print(f"[ERROR] Failed to get SNR results: {e}")
            return {}

    def get_recent_faults(self, limit: int = 50) -> List[Dict]:
        """Get recent fault events across all signals."""
        try:
            q = f'SELECT * FROM "fault_events" ORDER BY time DESC LIMIT {limit}'
            result = self.dst_client.query(q)
            return list(result.get_points())[::-1]
        except Exception as e:
            print(f"[ERROR] Failed to get fault events: {e}")
            return []

    def get_recent_oscillations(self, limit: int = 50) -> List[Dict]:
        """Get recent oscillation events."""
        try:
            q = f'SELECT * FROM "oscillation_alerts" ORDER BY time DESC LIMIT {limit}'
            result = self.dst_client.query(q)
            return list(result.get_points())[::-1]
        except Exception as e:
            print(f"[ERROR] Failed to get oscillation events: {e}")
            return []
