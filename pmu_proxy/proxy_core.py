# =======================
# proxy_core_v7_14.py
# =======================
import time
from datetime import datetime, timezone
from threading import Thread
from collections import deque
from influxdb import InfluxDBClient
from config import (
    HOST, PORT, SOURCE_DB, TARGET_DB, MEAS_OUT,
    SIGNALS, BUFFER_SECONDS, SAMPLE_INTERVAL,
    WINDOW_BEFORE, WINDOW_AFTER, POLL_INTERVAL
)

class PMUMonitor:
    """
    从 InfluxDB(SOURCE_DB=pmu_data) 读取最新数据；
    依据阈值检查，触发时把 ±5s 窗口写入 TARGET_DB=pmu_alerts。
    """
    def __init__(self):
        # 源/目标库
        self.src = InfluxDBClient(host=HOST, port=PORT, database=SOURCE_DB)
        self.dst = InfluxDBClient(host=HOST, port=PORT, database=TARGET_DB)
        # 环形缓存：每个信号维护最近 BUFFER_SECONDS / SAMPLE_INTERVAL 个点
        self.buffers = {
            k: deque(maxlen=int(BUFFER_SECONDS / SAMPLE_INTERVAL))
            for k in SIGNALS.keys()
        }
        # 事件状态
        self.events = {
            k: {"active": False, "start_ts": None}
            for k in SIGNALS.keys()
        }
        self.running = False
        self.thread = None
        print("[INIT] v7.14 PMU Monitor initialized.")

    # ---------- 基础查询 ----------
    def _fetch_latest(self, measurement):
        """
        从 pmu_data 中取 measurement 最新一条
        返回 dict 或 None: {"value":..., "time":...}
        """
        q = f'SELECT "value","time" FROM "{measurement}" ORDER BY time DESC LIMIT 1'
        try:
            res = self.src.query(q)
            pts = list(res.get_points())
            return pts[0] if pts else None
        except Exception as e:
            print(f"[ERROR] query latest {measurement}: {e}")
            return None

    # ---------- 构造写入点 ----------
    def _build_point(self, device, sigtype, val, dev, ts_iso):
        return {
            "measurement": MEAS_OUT,
            "tags": {"device": device, "signal_type": sigtype},
            "fields": {"value": float(val), "deviation": float(dev)},
            "time": ts_iso
        }

    def _write_points(self, points):
        if not points:
            return
        try:
            self.dst.write_points(points)
            # print(f"[WRITE] {len(points)} pts -> {TARGET_DB}")
        except Exception as e:
            print(f"[ERROR] write_points: {e}")

    # ---------- 核心检查逻辑（每次轮询调用） ----------
    def check_signals(self):
        for dev, cfg in SIGNALS.items():
            rec = self._fetch_latest(dev)
            if not rec:
                # 源库目前没有这个 measurement；跳过
                continue

            try:
                val = float(rec["value"])
            except Exception:
                # 兼容 value 不是数值的情况
                continue

            ts_iso = rec["time"]
            # InfluxDB 1.x 返回 ISO8601 带Z；转 epoch 便于窗口筛选
            ts_epoch = datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).timestamp()

            # 缓存
            self.buffers[dev].append({"t": ts_epoch, "val": val})

            base = cfg["base"]
            if "threshold_ratio" in cfg:
                deviation = (val - base) / base
                exceed = abs(deviation) > cfg["threshold_ratio"]
            else:
                deviation = val - base
                exceed = abs(deviation) > cfg["threshold"]

            ev = self.events[dev]

            # 触发：写入「前5秒窗口」
            if exceed and not ev["active"]:
                ev["active"] = True
                ev["start_ts"] = ts_epoch
                pre_points = []
                # 从缓存中过滤 [t-5s, t] 的点
                for p in list(self.buffers[dev]):
                    if ts_epoch - WINDOW_BEFORE <= p["t"] <= ts_epoch:
                        dev_val = (p["val"] - base) / base if "threshold_ratio" in cfg else p["val"] - base
                        pre_points.append(
                            self._build_point(
                                dev, cfg["type"], p["val"], dev_val,
                                datetime.fromtimestamp(p["t"], tz=timezone.utc).isoformat()
                            )
                        )
                self._write_points(pre_points)
                print(f"[EVENT START] {dev} exceed at {ts_iso}")

            # 事件活跃期：写入「后5秒窗口」
            elif ev["active"]:
                if ts_epoch - ev["start_ts"] <= WINDOW_AFTER:
                    self._write_points([
                        self._build_point(dev, cfg["type"], val, deviation, ts_iso)
                    ])
                else:
                    ev["active"] = False
                    ev["start_ts"] = None
                    print(f"[EVENT END] {dev} window complete")

    # ---------- 线程控制 ----------
    def _loop(self):
        print("[START] v7.14 PMU Monitor thread running...")
        while self.running:
            self.check_signals()
            time.sleep(POLL_INTERVAL)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        print("[STOP] v7.14 PMU Monitor stopped.")
