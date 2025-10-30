// ===================================================
// api.js — 本地稳定版（仅开发用）
// 后端固定地址：http://127.0.0.1:8000
// ===================================================

import axios from "axios";

// 后端固定地址
const BASE_URL = "http://127.0.0.1:8000";

// ---- 获取信号列表 ----
export async function getSignals() {
  const { data } = await axios.get(`${BASE_URL}/signals`);
  return data;
}

// ---- 获取指定信号数据 ----
export async function getData(signalId, { limit = 300, start = "", end = "" } = {}) {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (start) params.set("start", String(start));
  if (end) params.set("end", String(end));
  const url = `${BASE_URL}/data/${encodeURIComponent(signalId)}?${params.toString()}`;
  const { data } = await axios.get(url);
  return data;
}

// ---- 获取告警数据 ----
export async function getAlerts(limit = 100) {
  const { data } = await axios.get(`${BASE_URL}/alerts?limit=${limit}`);
  return data;
}

// ---- 停止监控线程（可选） ----
export async function stopMonitor() {
  const { data } = await axios.get(`${BASE_URL}/stop`);
  return data;
}

// ---- 控制台调试 ----
console.log(`🧭 后端接口地址: ${BASE_URL}`);
