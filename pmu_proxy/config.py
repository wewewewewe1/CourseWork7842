# =======================
# config_v7_14.py
# =======================

# InfluxDB (1.x) 连接
HOST = "127.0.0.1"
PORT = 8086

# 库名（你已确认）
SOURCE_DB = "pmu_data"       # 连续数据（由 openHistorian 写入）
TARGET_DB = "pmu_alerts"     # 报警/事件窗口（由本服务写入）
MEAS_OUT  = "pmu_monitor_alerts"

# 监测信号与阈值
SIGNALS = {
    "PPA:2": {  # 频率
        "type": "frequency",
        "base": 60.00,
        "threshold": 0.10,  # ±0.10 Hz
    },
    "PPA:7": {  # 电压
        "type": "voltage",
        "base": 299646.0,
        "threshold_ratio": 0.05,  # ±5%
    },
}

# 采样/窗口（保持默认）
BUFFER_SECONDS = 10          # 环形缓存总时长
SAMPLE_INTERVAL = 0.05       # 采样时间粒度（决定缓存长度）
WINDOW_BEFORE = 5            # 报警前窗口
WINDOW_AFTER  = 5            # 报警后窗口
POLL_INTERVAL = 0.5          # 轮询检测周期（秒）
