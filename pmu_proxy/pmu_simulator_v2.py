# =======================
# pmu_simulator_v2.py - Industrial-Grade PMU Data Simulator
# Complete IEEE C37.118 compliant PMU data generation
# =======================
"""
Professional PMU Data Simulator - Full Industrial Specification

Generates complete PMU data streams including:
- Operating Status (NORMAL/WARNING/CRITICAL/OFFLINE)
- Boolean Signals (Breaker, Relay, Alarm states)
- System Frequency + ROCOF (Rate of Change of Frequency)
- 3-Phase Voltage (Magnitude + Angle)
- 3-Phase Current (Magnitude + Angle)
- Power Measurements (P, Q, S, PF)
- Sequence Components (Positive, Negative, Zero)
- Harmonics (THD, individual harmonics)
"""

import math
import random
import time
import numpy as np
from datetime import datetime, timezone
from influxdb import InfluxDBClient
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json

# ==================== Enums ====================

class OperatingStatus(Enum):
    """PMU operating status"""
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2
    OFFLINE = 3

class BreakerStatus(Enum):
    """Circuit breaker status"""
    OPEN = 0
    CLOSED = 1
    INTERMEDIATE = 2

# ==================== Configuration ====================

@dataclass
class PMUSimulatorConfig:
    """Industrial PMU Simulator Configuration"""
    # InfluxDB settings
    influx_host: str = "127.0.0.1"
    influx_port: int = 8086
    database: str = "pmu_data"

    # Sampling settings
    sample_rate: float = 30.0  # Hz (30 samples per second for PMU)
    reporting_rate: float = 1.0  # Hz (report to DB every second)

    # Nominal operating values
    voltage_nominal: float = 345000.0  # V (345 kV line-to-line)
    voltage_ln_nominal: float = 199186.0  # V (line-to-neutral, 345kV/sqrt(3))
    current_nominal: float = 1000.0    # A
    frequency_nominal: float = 60.0    # Hz
    power_factor_nominal: float = 0.95  # Leading

    # Normal fluctuation ranges (random noise)
    voltage_noise_pct: float = 0.3     # ±0.3%
    current_noise_pct: float = 0.5     # ±0.5%
    frequency_noise_hz: float = 0.015  # ±0.015 Hz
    angle_noise_deg: float = 0.2       # ±0.2 degrees

    # Anomaly injection settings
    anomaly_enabled: bool = True
    anomaly_interval_min: int = 20     # Minimum seconds between anomalies
    anomaly_interval_max: int = 60     # Maximum seconds between anomalies

    # Warning thresholds
    voltage_warning_pct: float = 3.0   # ±3% for WARNING
    voltage_critical_pct: float = 5.0  # ±5% for CRITICAL
    frequency_warning_hz: float = 0.1  # ±0.1 Hz for WARNING
    frequency_critical_hz: float = 0.2 # ±0.2 Hz for CRITICAL
    rocof_warning: float = 0.5         # Hz/s for WARNING
    rocof_critical: float = 1.0        # Hz/s for CRITICAL

class PMUDataPoint:
    """Complete PMU measurement data point"""
    def __init__(self):
        # Timestamp
        self.timestamp = datetime.now(timezone.utc)
        self.timestamp_us = self.timestamp.timestamp()

        # Operating status
        self.status = OperatingStatus.NORMAL

        # Boolean signals
        self.breaker_a = BreakerStatus.CLOSED
        self.breaker_b = BreakerStatus.CLOSED
        self.breaker_c = BreakerStatus.CLOSED
        self.relay_trip = False
        self.alarm_active = False
        self.data_valid = True

        # Frequency measurements
        self.frequency = 60.0  # Hz
        self.rocof = 0.0       # Rate of change of frequency (Hz/s)

        # 3-Phase Voltage (line-to-neutral)
        self.voltage_a_mag = 0.0  # V
        self.voltage_a_ang = 0.0  # degrees
        self.voltage_b_mag = 0.0
        self.voltage_b_ang = -120.0
        self.voltage_c_mag = 0.0
        self.voltage_c_ang = -240.0

        # 3-Phase Current
        self.current_a_mag = 0.0  # A
        self.current_a_ang = 0.0  # degrees
        self.current_b_mag = 0.0
        self.current_b_ang = -120.0
        self.current_c_mag = 0.0
        self.current_c_ang = -240.0

        # Power measurements (3-phase total)
        self.active_power = 0.0    # MW
        self.reactive_power = 0.0  # MVAr
        self.apparent_power = 0.0  # MVA
        self.power_factor = 0.0    # dimensionless

        # Sequence components
        self.positive_seq_voltage = 0.0  # V
        self.negative_seq_voltage = 0.0  # V
        self.zero_seq_voltage = 0.0      # V

        # Harmonics
        self.thd_voltage = 0.0  # %
        self.thd_current = 0.0  # %

class IndustrialPMUSimulator:
    """
    Industrial-Grade PMU Data Simulator

    Generates complete IEEE C37.118 compliant PMU data with:
    - High-frequency sampling (30 Hz)
    - Complete phasor measurements
    - Operating status and Boolean signals
    - ROCOF (Rate of Change of Frequency)
    - Power quality metrics
    """

    def __init__(self, config: PMUSimulatorConfig = None):
        self.config = config or PMUSimulatorConfig()
        self.client = InfluxDBClient(
            host=self.config.influx_host,
            port=self.config.influx_port,
            database=self.config.database
        )

        # Create database if needed
        databases = self.client.get_list_database()
        db_names = [db['name'] for db in databases]
        if self.config.database not in db_names:
            self.client.create_database(self.config.database)
            print(f"[PMU-SIM] Created database: {self.config.database}")

        # Simulation state
        self.start_time = time.time()
        self.sample_count = 0
        self.report_count = 0

        # Internal state
        self.last_frequency = self.config.frequency_nominal
        self.frequency_history = []  # For ROCOF calculation

        # Load state (varies sinusoidally)
        self.load_phase = random.random() * 2 * math.pi

        # Anomaly management
        self.active_anomaly = None
        self.next_anomaly_time = self.start_time + random.uniform(
            self.config.anomaly_interval_min,
            self.config.anomaly_interval_max
        )
        self.anomaly_history = []

        # Sample buffer (accumulate samples before reporting)
        self.sample_buffer = []
        self.samples_per_report = int(self.config.sample_rate / self.config.reporting_rate)

        print("[PMU-SIM] Industrial PMU Simulator initialized")
        print(f"[PMU-SIM] Sampling rate: {self.config.sample_rate} Hz")
        print(f"[PMU-SIM] Reporting rate: {self.config.reporting_rate} Hz")
        print(f"[PMU-SIM] Samples per report: {self.samples_per_report}")

    def _calculate_rocof(self, frequency: float, dt: float) -> float:
        """Calculate Rate of Change of Frequency (ROCOF)"""
        self.frequency_history.append(frequency)
        if len(self.frequency_history) > 10:
            self.frequency_history.pop(0)

        if len(self.frequency_history) >= 2:
            # Linear regression for better ROCOF estimate
            times = np.arange(len(self.frequency_history)) * dt
            freqs = np.array(self.frequency_history)
            rocof = np.polyfit(times, freqs, 1)[0]  # Slope = dF/dt
            return rocof
        return 0.0

    def _calculate_sequence_components(self, va: complex, vb: complex, vc: complex) -> Tuple[float, float, float]:
        """Calculate positive, negative, and zero sequence components"""
        a = np.exp(1j * 2 * np.pi / 3)  # 120° rotation operator

        # Symmetrical components transformation
        v_pos = (va + a * vb + a**2 * vc) / 3
        v_neg = (va + a**2 * vb + a * vc) / 3
        v_zero = (va + vb + vc) / 3

        return abs(v_pos), abs(v_neg), abs(v_zero)

    def _add_noise(self, base_value: float, noise_pct: float) -> float:
        """Add random Gaussian noise"""
        noise = base_value * noise_pct / 100.0
        return base_value + random.gauss(0, noise / 3)  # 3-sigma = noise

    def _generate_normal_sample(self, elapsed_time: float) -> PMUDataPoint:
        """Generate one normal PMU data sample"""
        data = PMUDataPoint()

        # Time
        data.timestamp = datetime.now(timezone.utc)
        data.timestamp_us = time.time()

        # Load variation (slow sinusoidal)
        load_factor = 0.7 + 0.25 * math.sin(elapsed_time / 30 + self.load_phase)

        # Frequency (with small natural fluctuation)
        base_freq = self.config.frequency_nominal
        freq_noise = random.gauss(0, self.config.frequency_noise_hz / 3)
        data.frequency = base_freq + freq_noise

        # ROCOF
        dt = 1.0 / self.config.sample_rate
        data.rocof = self._calculate_rocof(data.frequency, dt)

        # 3-Phase Voltages (balanced under normal conditions)
        v_nominal = self.config.voltage_ln_nominal
        for phase_idx, phase in enumerate(['a', 'b', 'c']):
            mag = self._add_noise(v_nominal, self.config.voltage_noise_pct)
            ang = phase_idx * (-120) + self._add_noise(0, self.config.angle_noise_deg)

            setattr(data, f'voltage_{phase}_mag', mag)
            setattr(data, f'voltage_{phase}_ang', ang)

        # 3-Phase Currents (proportional to load)
        i_nominal = self.config.current_nominal * load_factor
        pf_angle = math.acos(self.config.power_factor_nominal) * 180 / math.pi

        for phase_idx, phase in enumerate(['a', 'b', 'c']):
            mag = self._add_noise(i_nominal, self.config.current_noise_pct)
            # Current lags voltage by power factor angle
            v_ang = getattr(data, f'voltage_{phase}_ang')
            ang = v_ang - pf_angle + self._add_noise(0, self.config.angle_noise_deg)

            setattr(data, f'current_{phase}_mag', mag)
            setattr(data, f'current_{phase}_ang', ang)

        # Power calculations (3-phase)
        total_apparent = 3 * (data.voltage_a_mag / 1000) * (data.current_a_mag / 1000)  # MVA
        total_active = total_apparent * self.config.power_factor_nominal  # MW
        total_reactive = total_apparent * math.sin(math.acos(self.config.power_factor_nominal))  # MVAr

        data.active_power = total_active
        data.reactive_power = total_reactive
        data.apparent_power = total_apparent
        data.power_factor = self.config.power_factor_nominal

        # Sequence components
        va = data.voltage_a_mag * np.exp(1j * data.voltage_a_ang * np.pi / 180)
        vb = data.voltage_b_mag * np.exp(1j * data.voltage_b_ang * np.pi / 180)
        vc = data.voltage_c_mag * np.exp(1j * data.voltage_c_ang * np.pi / 180)

        v_pos, v_neg, v_zero = self._calculate_sequence_components(va, vb, vc)
        data.positive_seq_voltage = v_pos
        data.negative_seq_voltage = v_neg
        data.zero_seq_voltage = v_zero

        # Harmonics (very low under normal conditions)
        data.thd_voltage = random.uniform(0.5, 1.5)  # %
        data.thd_current = random.uniform(1.0, 3.0)  # %

        # Boolean signals (all normal)
        data.breaker_a = BreakerStatus.CLOSED
        data.breaker_b = BreakerStatus.CLOSED
        data.breaker_c = BreakerStatus.CLOSED
        data.relay_trip = False
        data.alarm_active = False
        data.data_valid = True

        # Status (check thresholds)
        data.status = self._determine_status(data)

        return data

    def _determine_status(self, data: PMUDataPoint) -> OperatingStatus:
        """Determine operating status based on thresholds"""
        v_nominal = self.config.voltage_ln_nominal
        f_nominal = self.config.frequency_nominal

        # Check voltage deviation
        v_avg = (data.voltage_a_mag + data.voltage_b_mag + data.voltage_c_mag) / 3
        v_dev_pct = abs(v_avg - v_nominal) / v_nominal * 100

        # Check frequency deviation
        f_dev = abs(data.frequency - f_nominal)

        # Check ROCOF
        rocof_abs = abs(data.rocof)

        # Determine status
        if (v_dev_pct > self.config.voltage_critical_pct or
            f_dev > self.config.frequency_critical_hz or
            rocof_abs > self.config.rocof_critical):
            return OperatingStatus.CRITICAL

        if (v_dev_pct > self.config.voltage_warning_pct or
            f_dev > self.config.frequency_warning_hz or
            rocof_abs > self.config.rocof_warning):
            return OperatingStatus.WARNING

        return OperatingStatus.NORMAL

    def _apply_anomaly(self, data: PMUDataPoint, anomaly: dict) -> PMUDataPoint:
        """Apply anomaly effects to data sample"""
        anom_type = anomaly['type']

        if anom_type == 'voltage_sag':
            multiplier = 1.0 - anomaly['magnitude_pct'] / 100
            data.voltage_a_mag *= multiplier
            data.voltage_b_mag *= multiplier
            data.voltage_c_mag *= multiplier

        elif anom_type == 'voltage_swell':
            multiplier = 1.0 + anomaly['magnitude_pct'] / 100
            data.voltage_a_mag *= multiplier
            data.voltage_b_mag *= multiplier
            data.voltage_c_mag *= multiplier

        elif anom_type == 'frequency_deviation':
            data.frequency += anomaly['offset_hz']

        elif anom_type == 'phase_imbalance':
            # Unbalance phases
            data.voltage_b_mag *= (1.0 - anomaly['imbalance_pct'] / 100)
            data.voltage_c_mag *= (1.0 + anomaly['imbalance_pct'] / 100)

        elif anom_type == 'breaker_trip':
            phase = anomaly['phase']
            setattr(data, f'breaker_{phase}', BreakerStatus.OPEN)
            setattr(data, f'current_{phase}_mag', 0.0)
            data.relay_trip = True
            data.alarm_active = True

        # Recalculate status after anomaly
        data.status = self._determine_status(data)

        return data

    def _inject_anomaly(self, current_time: float):
        """Inject a random anomaly"""
        anomaly_types = [
            'voltage_sag',
            'voltage_swell',
            'frequency_deviation',
            'phase_imbalance',
            'breaker_trip'
        ]

        anom_type = random.choice(anomaly_types)

        if anom_type == 'voltage_sag':
            duration = random.uniform(2, 5)
            magnitude = random.uniform(10, 30)
            params = {'magnitude_pct': magnitude}

        elif anom_type == 'voltage_swell':
            duration = random.uniform(2, 5)
            magnitude = random.uniform(10, 20)
            params = {'magnitude_pct': magnitude}

        elif anom_type == 'frequency_deviation':
            duration = random.uniform(3, 8)
            offset = random.uniform(0.15, 0.5) * random.choice([-1, 1])
            params = {'offset_hz': offset}

        elif anom_type == 'phase_imbalance':
            duration = random.uniform(5, 15)
            imbalance = random.uniform(5, 15)
            params = {'imbalance_pct': imbalance}

        elif anom_type == 'breaker_trip':
            duration = random.uniform(10, 30)
            phase = random.choice(['a', 'b', 'c'])
            params = {'phase': phase}

        self.active_anomaly = {
            'type': anom_type,
            'start_time': current_time,
            'end_time': current_time + duration,
            'params': params
        }

        self.anomaly_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': anom_type,
            'duration': duration,
            'params': params
        })

        print(f"\n[ANOMALY START] {anom_type.upper()}")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Parameters: {params}")

    def _write_to_influxdb(self, data: PMUDataPoint):
        """Write PMU data point to InfluxDB"""
        points = []
        ts = data.timestamp.isoformat()

        # Legacy compatibility measurements
        points.append({
            "measurement": "PPA:2",
            "fields": {"value": data.frequency},
            "time": ts
        })

        points.append({
            "measurement": "PPA:7",
            "fields": {"value": data.voltage_a_mag},
            "time": ts
        })

        # Complete PMU measurements
        measurements = {
            # Status and Boolean
            "PMU_status": data.status.value,
            "PMU_breaker_a": data.breaker_a.value,
            "PMU_breaker_b": data.breaker_b.value,
            "PMU_breaker_c": data.breaker_c.value,
            "PMU_relay_trip": 1 if data.relay_trip else 0,
            "PMU_alarm_active": 1 if data.alarm_active else 0,
            "PMU_data_valid": 1 if data.data_valid else 0,

            # Frequency
            "PMU_frequency": data.frequency,
            "PMU_rocof": data.rocof,

            # Voltages
            "PMU_voltage_a_mag": data.voltage_a_mag,
            "PMU_voltage_a_ang": data.voltage_a_ang,
            "PMU_voltage_b_mag": data.voltage_b_mag,
            "PMU_voltage_b_ang": data.voltage_b_ang,
            "PMU_voltage_c_mag": data.voltage_c_mag,
            "PMU_voltage_c_ang": data.voltage_c_ang,

            # Currents
            "PMU_current_a_mag": data.current_a_mag,
            "PMU_current_a_ang": data.current_a_ang,
            "PMU_current_b_mag": data.current_b_mag,
            "PMU_current_b_ang": data.current_b_ang,
            "PMU_current_c_mag": data.current_c_mag,
            "PMU_current_c_ang": data.current_c_ang,

            # Power
            "PMU_active_power": data.active_power,
            "PMU_reactive_power": data.reactive_power,
            "PMU_apparent_power": data.apparent_power,
            "PMU_power_factor": data.power_factor,

            # Sequence components
            "PMU_positive_seq_v": data.positive_seq_voltage,
            "PMU_negative_seq_v": data.negative_seq_voltage,
            "PMU_zero_seq_v": data.zero_seq_voltage,

            # Harmonics
            "PMU_thd_voltage": data.thd_voltage,
            "PMU_thd_current": data.thd_current,
        }

        for meas_name, value in measurements.items():
            points.append({
                "measurement": meas_name,
                "fields": {"value": float(value)},
                "time": ts
            })

        try:
            self.client.write_points(points)
        except Exception as e:
            print(f"[ERROR] Failed to write to InfluxDB: {e}")

    def run(self, duration: Optional[float] = None):
        """Run the simulator"""
        print(f"\n[PMU-SIM] Starting industrial PMU data generation...")
        print("[PMU-SIM] Press Ctrl+C to stop\n")

        try:
            while True:
                current_time = time.time()
                elapsed_time = current_time - self.start_time

                if duration and elapsed_time >= duration:
                    break

                # Check for anomaly injection
                if (self.config.anomaly_enabled and
                    current_time >= self.next_anomaly_time and
                    self.active_anomaly is None):
                    self._inject_anomaly(current_time)
                    self.next_anomaly_time = current_time + random.uniform(
                        self.config.anomaly_interval_min,
                        self.config.anomaly_interval_max
                    )

                # Generate sample
                sample = self._generate_normal_sample(elapsed_time)

                # Apply anomaly if active
                if self.active_anomaly:
                    if current_time < self.active_anomaly['end_time']:
                        sample = self._apply_anomaly(sample, self.active_anomaly)
                    else:
                        print(f"[ANOMALY END] {self.active_anomaly['type']}")
                        self.active_anomaly = None

                # Add to buffer
                self.sample_buffer.append(sample)
                self.sample_count += 1

                # Report to database when buffer is full
                if len(self.sample_buffer) >= self.samples_per_report:
                    # Average samples for reporting (30 Hz → 1 Hz)
                    avg_sample = self._average_samples(self.sample_buffer)
                    self._write_to_influxdb(avg_sample)
                    self.sample_buffer.clear()
                    self.report_count += 1

                    # Log status
                    if self.report_count % 10 == 0:
                        status_str = avg_sample.status.name
                        anom_str = f" | ANOMALY: {self.active_anomaly['type']}" if self.active_anomaly else ""
                        print(f"[{self.report_count:04d}] F={avg_sample.frequency:.4f}Hz | "
                              f"ROCOF={avg_sample.rocof:.3f}Hz/s | "
                              f"V={avg_sample.voltage_a_mag:.0f}V | "
                              f"Status={status_str}{anom_str}")

                # Sleep until next sample
                sleep_time = 1.0 / self.config.sample_rate
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n[PMU-SIM] Stopped by user")

        print(f"\n[PMU-SIM] Summary:")
        print(f"  Total samples: {self.sample_count}")
        print(f"  Reports sent: {self.report_count}")
        print(f"  Anomalies injected: {len(self.anomaly_history)}")

    def _average_samples(self, samples: List[PMUDataPoint]) -> PMUDataPoint:
        """Average multiple samples for reporting"""
        avg = PMUDataPoint()

        n = len(samples)
        if n == 0:
            return avg

        # Average scalar values
        avg.frequency = sum(s.frequency for s in samples) / n
        avg.rocof = sum(s.rocof for s in samples) / n

        for phase in ['a', 'b', 'c']:
            avg_mag = sum(getattr(s, f'voltage_{phase}_mag') for s in samples) / n
            avg_ang = sum(getattr(s, f'voltage_{phase}_ang') for s in samples) / n
            setattr(avg, f'voltage_{phase}_mag', avg_mag)
            setattr(avg, f'voltage_{phase}_ang', avg_ang)

            avg_mag = sum(getattr(s, f'current_{phase}_mag') for s in samples) / n
            avg_ang = sum(getattr(s, f'current_{phase}_ang') for s in samples) / n
            setattr(avg, f'current_{phase}_mag', avg_mag)
            setattr(avg, f'current_{phase}_ang', avg_ang)

        avg.active_power = sum(s.active_power for s in samples) / n
        avg.reactive_power = sum(s.reactive_power for s in samples) / n
        avg.apparent_power = sum(s.apparent_power for s in samples) / n
        avg.power_factor = sum(s.power_factor for s in samples) / n

        avg.positive_seq_voltage = sum(s.positive_seq_voltage for s in samples) / n
        avg.negative_seq_voltage = sum(s.negative_seq_voltage for s in samples) / n
        avg.zero_seq_voltage = sum(s.zero_seq_voltage for s in samples) / n

        avg.thd_voltage = sum(s.thd_voltage for s in samples) / n
        avg.thd_current = sum(s.thd_current for s in samples) / n

        # Use most recent status and booleans
        last_sample = samples[-1]
        avg.status = last_sample.status
        avg.breaker_a = last_sample.breaker_a
        avg.breaker_b = last_sample.breaker_b
        avg.breaker_c = last_sample.breaker_c
        avg.relay_trip = last_sample.relay_trip
        avg.alarm_active = last_sample.alarm_active
        avg.data_valid = last_sample.data_valid
        avg.timestamp = last_sample.timestamp

        return avg

# ==================== Main ====================

if __name__ == "__main__":
    config = PMUSimulatorConfig(
        sample_rate=30.0,  # 30 Hz sampling
        reporting_rate=1.0,  # 1 Hz reporting
        anomaly_interval_min=20,
        anomaly_interval_max=60,
    )

    simulator = IndustrialPMUSimulator(config)
    simulator.run()
