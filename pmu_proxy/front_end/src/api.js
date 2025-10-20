import axios from "axios";
const BASE_URL = "http://127.0.0.1:8000";

export async function getSignals() {
  const { data } = await axios.get(`${BASE_URL}/signals`);
  return data;
}

export async function getData(signalId, { limit=300, start="", end="" } = {}) {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (start) params.set("start", String(start));
  if (end)   params.set("end", String(end));
  const { data } = await axios.get(`${BASE_URL}/data/${encodeURIComponent(signalId)}?${params.toString()}`);
  return data;
}

export async function getAlerts(limit = 100) {
  const { data } = await axios.get(`${BASE_URL}/alerts?limit=${limit}`);
  return data;
}
