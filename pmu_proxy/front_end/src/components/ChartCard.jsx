import React, { useEffect, useMemo, useRef, useState } from "react";
import { getData } from "../api";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS, LineElement, CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend
} from "chart.js";
import zoomPlugin from "chartjs-plugin-zoom";

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend, zoomPlugin);

export default function ChartCard({ cfg, onEdit, onRename, onRemove }) {
  const [dataMap, setDataMap] = useState({});
  const timerRef = useRef(null);
  const chartRef = useRef(null);

  async function loadAll() {
    const next = {};
    await Promise.all(cfg.series.map(async s => {
      const rows = await getData(s.id, { limit: 300 });
      next[s.id] = rows;
    }));
    setDataMap(next);
  }

  useEffect(() => {
    loadAll();
    timerRef.current && clearInterval(timerRef.current);
    timerRef.current = setInterval(loadAll, cfg.refresh || 2000);
    return () => timerRef.current && clearInterval(timerRef.current);
  }, [JSON.stringify(cfg)]);

  const labels = useMemo(() => {
    const all = Object.values(dataMap).reduce((acc, arr) => (arr && acc.length < arr.length ? arr : acc), []);
    return (all || []).map(d => new Date(d.time).toLocaleTimeString());
  }, [dataMap]);

  const datasets = useMemo(() => (
    (cfg.series || []).map(s => ({
      label: s.id,
      data: (dataMap[s.id] || []).map(d => Number(d.value || 0)),
      borderColor: s.color || "#4e79a7",
      backgroundColor: (s.color || "#4e79a7") + "33",
      tension: 0.2,
      pointRadius: 0,
      fill: false
    }))
  ), [cfg.series, dataMap]);

  const chartData = { labels, datasets };
  const options = {
    responsive: true,
    plugins: {
      legend: { position: "top" },
      zoom: {
        zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
        pan: { enabled: true, mode: "x" }
      }
    },
    animation: false,
    scales: { x: { ticks: { maxTicksLimit: 10 } } }
  };

  return (
    <div style={{background:"#fff", borderRadius:10, padding:10, boxShadow:"0 2px 6px rgba(0,0,0,0.05)"}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
        <input
          style={{border:"none",fontWeight:600,width:"50%"}}
          defaultValue={cfg.name}
          onBlur={e=>onRename?.(e.target.value)}
        />
        <div style={{display:"flex",gap:6}}>
          <button onClick={onEdit}>Edit</button>
          <button onClick={()=>chartRef.current?.resetZoom?.()}>Reset</button>
          <button onClick={()=>onRemove?.()}>Remove</button>
        </div>
      </div>
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  );
}
