# fake_writer.py  —— 仅用于联调验证
import math, random, time
from datetime import datetime, timezone
from influxdb import InfluxDBClient

HOST, PORT, DB = "127.0.0.1", 8086, "pmu_data"
cli = InfluxDBClient(host=HOST, port=PORT, database=DB)

print("[FAKE] start writing to pmu_data ... Ctrl+C to stop")
t0 = time.time()
try:
    while True:
        t = time.time() - t0
        f = 60.0 + 0.05 * math.sin(t)             # PPA:2 ~ 60 ±0.05
        v = 299646.0 * (1 + 0.01*(random.random()-0.5))  # PPA:7 ~ ±0.5%
        ts = datetime.now(timezone.utc).isoformat()
        points = [
            {"measurement": "PPA:2", "fields": {"value": float(f)}, "time": ts},
            {"measurement": "PPA:7", "fields": {"value": float(v)}, "time": ts},
        ]
        cli.write_points(points)
        time.sleep(1.0)
except KeyboardInterrupt:
    print("\n[FAKE] stopped.")
