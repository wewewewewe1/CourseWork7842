import React, { useEffect, useMemo, useRef, useState } from "react";
import { getData } from "../api";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import zoomPlugin from "chartjs-plugin-zoom";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
  zoomPlugin
);

export default function ChartCard({ cfg, onEdit, onRename, onRemove }) {
  const [dataMap, setDataMap] = useState({});
  const chartRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // ----------------------------
  // 加载数据 & 自动刷新
  // ----------------------------
  async function loadAll() {
    const chart = chartRef.current;
    const currentRange = chart?.scales?.x
      ? { min: chart.scales.x.min, max: chart.scales.x.max }
      : null;

    const next = {};
    await Promise.all(
      cfg.series.map(async (s) => {
        const rows = await getData(s.id, { limit: 800 });
        next[s.id] = rows;
      })
    );
    setDataMap(next);

    // 保留当前缩放与平移状态
    if (chart && currentRange && !autoScroll) {
      setTimeout(() => {
        try {
          chart.zoomScale("x", currentRange);
        } catch {}
      }, 200);
    }
  }

  useEffect(() => {
    loadAll();
    const timer = setInterval(loadAll, cfg.refresh || 2000);
    return () => clearInterval(timer);
  }, [JSON.stringify(cfg)]);

  // ----------------------------
  // 数据处理
  // ----------------------------
  const labels = useMemo(() => {
    const all = Object.values(dataMap).reduce(
      (acc, arr) => (arr && acc.length < arr.length ? arr : acc),
      []
    );
    return (all || []).map((d) => new Date(d.time).toLocaleTimeString());
  }, [dataMap]);

  const datasets = useMemo(
    () =>
      (cfg.series || []).map((s) => ({
        label: s.id,
        data: (dataMap[s.id] || []).map((d) => Number(d.value || 0)),
        borderColor: s.color || "#4e79a7",
        backgroundColor: (s.color || "#4e79a7") + "33",
        tension: 0.2,
        pointRadius: 0,
        fill: false,
      })),
    [cfg.series, dataMap]
  );

  // ----------------------------
  // Chart.js 配置
  // ----------------------------
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { position: "top" },
      zoom: {
        pan: { enabled: true, mode: "x" },
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          drag: { enabled: true },
          mode: "x",
        },
      },
    },
    scales: { x: { ticks: { maxTicksLimit: 10 } } },
  };

  // ----------------------------
  // 导出全部 CSV
  // ----------------------------
  function exportAllCSV() {
    const keys = Object.keys(dataMap);
    if (keys.length === 0) {
      alert("暂无数据可导出！");
      return;
    }
    const times = dataMap[keys[0]]?.map((d) => d.time) || [];
    let rows = [];
    rows.push(["time", ...keys].join(","));
    for (let i = 0; i < times.length; i++) {
      const row = [times[i]];
      for (const k of keys) {
        const val = dataMap[k]?.[i]?.value ?? "";
        row.push(val);
      }
      rows.push(row.join(","));
    }
    const csv = rows.join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${cfg.name || "chart"}_${Date.now()}.csv`;
    link.click();
  }

  // ----------------------------
  // 缩放操作
  // ----------------------------
  function zoomIn() {
    const chart = chartRef.current;
    chart?.zoom(1.2);
    setAutoScroll(false);
  }

  function zoomOut() {
    const chart = chartRef.current;
    chart?.zoom(0.8);
    setAutoScroll(false);
  }

  function resetZoom() {
    const chart = chartRef.current;
    chart?.resetZoom();
    setAutoScroll(true);
  }

  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 10,
        padding: 10,
        boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
        height: 340,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* 顶部栏 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6,
          alignItems: "center",
        }}
      >
        <input
          style={{ border: "none", fontWeight: 600, width: "50%" }}
          defaultValue={cfg.name}
          onBlur={(e) => onRename?.(e.target.value)}
        />
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={onEdit}>✏️</button>
          <button title="zoom in" onClick={zoomIn}>🔍＋</button>
          <button title="zoom out" onClick={zoomOut}>🔍－</button>
          <button title="reset zoom" onClick={resetZoom}>↺</button>
          <button title="export all data" onClick={exportAllCSV}>💾</button>
          <button onClick={() => onRemove?.()}>❌</button>
        </div>
      </div>

      {/* 主图 */}
      <div style={{ flex: 1 }}>
        <Line ref={chartRef} data={{ labels, datasets }} options={options} />
      </div>
    </div>
  );
}
