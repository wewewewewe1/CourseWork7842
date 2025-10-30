# fake_writer.py  —— Enhanced test data generator with anomaly injection
import math, random, time
from datetime import datetime, timezone
from influxdb import InfluxDBClient

HOST, PORT, DB = "127.0.0.1", 8086, "pmu_data"
cli = InfluxDBClient(host=HOST, port=PORT, database=DB)

# Anomaly configuration
ANOMALY_PROBABILITY = 0.10  # 10% chance of anomaly per second
ANOMALY_DURATION = 5  # seconds

# Anomaly state
anomaly_active = False
anomaly_type = None
anomaly_start = 0
anomaly_count = 0

# Historical data for ROCOF calculation
frequency_history = []

def inject_anomaly():
    """Randomly select and return anomaly type"""
    anomalies = [
        'frequency_high',      # Frequency spike to 60.3+ Hz
        'frequency_low',       # Frequency drop to 59.7- Hz
        'voltage_sag',         # Voltage drop to 70% nominal
        'voltage_swell',       # Voltage spike to 130% nominal
        'oscillation',         # 0.5 Hz oscillation
        'extreme_spike'        # Very extreme values to test critical warnings
    ]
    return random.choice(anomalies)

def apply_anomaly(base_freq, base_volt, base_current, anomaly_type, t):
    """Apply anomaly to base values"""
    freq = base_freq
    volt = base_volt
    current = base_current
    status = 1  # Normal

    if anomaly_type == 'frequency_high':
        # WARNING level: 60.15-60.5 Hz, CRITICAL: >60.5 Hz
        freq = 60.25 + random.uniform(0, 0.15)
        status = 2  # Warning

    elif anomaly_type == 'frequency_low':
        # WARNING level: 59.5-59.85 Hz, CRITICAL: <59.5 Hz
        freq = 59.75 - random.uniform(0, 0.15)
        status = 2  # Warning

    elif anomaly_type == 'voltage_sag':
        # WARNING: -10%, CRITICAL: -30%
        volt = base_volt * (0.75 + random.uniform(-0.05, 0.05))
        current = current * 0.8  # Current also drops
        status = 3  # Critical

    elif anomaly_type == 'voltage_swell':
        # WARNING: +10%, CRITICAL: +30%
        volt = base_volt * (1.25 + random.uniform(-0.05, 0.05))
        current = current * 1.2  # Current also rises
        status = 3  # Critical

    elif anomaly_type == 'oscillation':
        # Add 0.5 Hz oscillation
        osc = 0.3 * math.sin(2 * math.pi * 0.5 * t)
        freq = base_freq + osc
        status = 2  # Warning

    elif anomaly_type == 'extreme_spike':
        # CRITICAL level - extreme values
        if random.random() > 0.5:
            freq = 60.6 + random.uniform(0, 0.5)  # Extreme frequency
        else:
            volt = base_volt * (1.4 + random.uniform(0, 0.2))  # Extreme voltage
            current = current * 1.5  # Extreme current
        status = 3  # Critical

    return freq, volt, current, status

print("="*60)
print("[FAKE WRITER] Enhanced PMU Test Data Generator")
print("="*60)
print(f"Database: {DB} @ {HOST}:{PORT}")
print(f"Signals Generated:")
print(f"  - PPA:2 (frequency)")
print(f"  - PPA:7 (voltage)")
print(f"  - PMU_current (current)")
print(f"  - PMU_status (operating status: 0=OFFLINE, 1=NORMAL, 2=WARNING, 3=CRITICAL)")
print(f"  - PMU_rocof (rate of change of frequency)")
print(f"Anomaly injection: {ANOMALY_PROBABILITY*100}% chance every second")
print(f"Anomaly duration: {ANOMALY_DURATION} seconds")
print("-"*60)
print("Press Ctrl+C to stop")
print("="*60)

t0 = time.time()
iteration = 0

try:
    while True:
        t = time.time() - t0
        iteration += 1

        # Base values (normal operation)
        base_freq = 60.0 + 0.02 * math.sin(t * 0.1)  # Small natural variation
        base_volt = 299646.0 + random.uniform(-500, 500)  # Small noise
        base_current = 1000.0 + random.uniform(-50, 50)  # Nominal 1000A ±50A

        # Anomaly injection logic
        if not anomaly_active:
            # Check if we should start an anomaly
            if random.random() < ANOMALY_PROBABILITY:
                anomaly_active = True
                anomaly_type = inject_anomaly()
                anomaly_start = t
                anomaly_count += 1
                print(f"\n[ANOMALY #{anomaly_count}] Injecting '{anomaly_type}' at t={t:.1f}s")
        else:
            # Check if anomaly should end
            if (t - anomaly_start) >= ANOMALY_DURATION:
                print(f"[ANOMALY #{anomaly_count}] Ended '{anomaly_type}' after {ANOMALY_DURATION}s")
                anomaly_active = False
                anomaly_type = None

        # Apply anomaly if active
        if anomaly_active:
            freq, volt, current, status = apply_anomaly(base_freq, base_volt, base_current, anomaly_type, t)
        else:
            freq, volt, current, status = base_freq, base_volt, base_current, 1  # Normal status

        # Add small random noise
        freq += random.uniform(-0.005, 0.005)
        volt += random.uniform(-100, 100)

        # Update frequency history for ROCOF calculation
        frequency_history.append(freq)
        if len(frequency_history) > 30:  # Keep last 30 seconds
            frequency_history.pop(0)

        # Calculate ROCOF (Rate of Change of Frequency) in Hz/s
        if len(frequency_history) >= 3:
            # Calculate derivative over 2-second window
            rocof = (frequency_history[-1] - frequency_history[-3]) / 2.0
        else:
            rocof = 0.0

        # Write to database with time_precision='s' to avoid caching issues
        ts = datetime.now(timezone.utc).isoformat()
        points = [
            {
                "measurement": "PPA:2",
                "fields": {"value": float(freq)},
                "time": ts
            },
            {
                "measurement": "PPA:7",
                "fields": {"value": float(volt)},
                "time": ts
            },
            {
                "measurement": "PMU_current",
                "fields": {"value": float(current)},
                "time": ts
            },
            {
                "measurement": "PMU_status",
                "fields": {"value": int(status)},
                "time": ts
            },
            {
                "measurement": "PMU_rocof",
                "fields": {"value": float(rocof)},
                "time": ts
            },
        ]

        cli.write_points(points, time_precision='s')

        # Status output every 10 iterations
        if iteration % 10 == 0:
            status_labels = ["OFFLINE", "NORMAL", "WARNING", "CRITICAL"]
            status_str = status_labels[status] if 0 <= status < len(status_labels) else "UNKNOWN"
            print(f"[{status_str}] t={t:.1f}s | Freq: {freq:.3f} Hz | ROCOF: {rocof:.4f} Hz/s | Volt: {volt:.1f} V | Current: {current:.1f} A | Iter: {iteration}")

        time.sleep(1.0)

except KeyboardInterrupt:
    print("\n" + "="*60)
    print(f"[FAKE WRITER] Stopped after {iteration} iterations ({t:.1f}s)")
    print(f"Total anomalies injected: {anomaly_count}")
    print("="*60)
