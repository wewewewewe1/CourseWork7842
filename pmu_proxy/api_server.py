# ==========================
# api_server.py  (更新版)
# 后端提供 /signals /data /alerts 三个接口
# /data 支持 start、end 参数（ISO8601 或 epoch）
# ==========================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb import InfluxDBClient
from datetime import datetime
from proxy_core import PMUMonitor
from config import HOST, PORT, SOURCE_DB, TARGET_DB, SIGNALS

app = FastAPI(title="PMU Monitor API", version="7.14")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

monitor = PMUMonitor()
monitor.start()


def _to_influx_time(ts: str):
    """支持 epoch(秒/毫秒) 或 RFC3339"""
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


@app.get("/")
def root():
    return {"status": "ok", "message": "PMU Monitor API running"}


@app.get("/signals")
def list_signals():
    return [{"id": k, **v} for k, v in SIGNALS.items()]


@app.get("/data/{signal_id}")
def get_data(signal_id: str, limit: int = 300, start: str = "", end: str = ""):
    """从 pmu_data 取数据；支持 start、end（RFC3339 或 epoch）"""
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
    return {"status": "stopped"}
