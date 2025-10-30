import React, { useState, useEffect, useRef } from "react";
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
  Filler,
} from "chart.js";
import zoomPlugin from "chartjs-plugin-zoom";
import TimelineSlider from "../TimelineSlider";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  zoomPlugin
);

export default function RealTimeWaveform({ signalId = "PPA:2", refreshInterval = 2000 }) {
  const [data, setData] = useState([]);
  const [timeWindow, setTimeWindow] = useState(300); // seconds
  const [autoScroll, setAutoScroll] = useState(true);
  const chartRef = useRef(null);

  // Timeline slider state
  const [isLive, setIsLive] = useState(true);
  const [selectedTime, setSelectedTime] = useState(new Date());
  const [minTime, setMinTime] = useState(new Date(Date.now() - 3600000)); // 1 hour ago
  const [maxTime, setMaxTime] = useState(new Date());
  const [userInteracting, setUserInteracting] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        // Use selected time if not live, otherwise use current time
        const endTime = isLive ? Date.now() : selectedTime.getTime();
        const startTime = endTime - timeWindow * 1000;

        const res = await fetch(
          `http://localhost:8000/data/${signalId}?start=${startTime}&end=${endTime}`
        );
        const json = await res.json();

        if (Array.isArray(json)) {
          setData(json);

          // Update time bounds
          if (json.length > 0) {
            const times = json.map(d => new Date(d.time).getTime());
            setMinTime(new Date(Math.min(...times)));
            setMaxTime(new Date(Math.max(...times)));
          }
        }
      } catch (error) {
        console.error("Failed to fetch waveform data:", error);
      }
    }

    fetchData();

    // Only auto-refresh in live mode
    if (isLive) {
      const timer = setInterval(fetchData, refreshInterval);
      return () => clearInterval(timer);
    }
  }, [signalId, timeWindow, refreshInterval, isLive, selectedTime]);

  // Handle timeline slider changes
  const handleTimeChange = (newTime, nowIsLive) => {
    setUserInteracting(true);
    setSelectedTime(newTime);
    setIsLive(nowIsLive);
    setAutoScroll(nowIsLive);

    // Clear interaction flag after a short delay
    setTimeout(() => setUserInteracting(false), 100);
  };

  // Prepare chart data
  const timestamps = data.map((d) => new Date(d.time).toLocaleTimeString());
  const values = data.map((d) => parseFloat(d.value) || 0);

  const chartData = {
    labels: timestamps,
    datasets: [
      {
        label: signalId,
        data: values,
        borderColor: "rgb(37, 99, 235)",
        backgroundColor: "rgba(37, 99, 235, 0.1)",
        fill: true,
        tension: 0.2,
        pointRadius: 0,
        borderWidth: 2,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: "#cbd5e1",
          font: { size: 12 },
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleColor: "#f1f5f9",
        bodyColor: "#cbd5e1",
        borderColor: "#334155",
        borderWidth: 1,
      },
      zoom: {
        zoom: {
          wheel: {
            enabled: true,
            speed: 0.1,
          },
          pinch: {
            enabled: true,
          },
          mode: "x",
        },
        pan: {
          enabled: true,
          mode: "x",
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: "rgba(148, 163, 184, 0.1)",
        },
        ticks: {
          color: "#94a3b8",
          maxTicksLimit: 10,
        },
      },
      y: {
        grid: {
          color: "rgba(148, 163, 184, 0.1)",
        },
        ticks: {
          color: "#94a3b8",
        },
      },
    },
  };

  const handleResetZoom = () => {
    if (chartRef.current) {
      chartRef.current.resetZoom();
    }
  };

  const handleExport = () => {
    const csv = [
      ["Timestamp", "Value"],
      ...data.map((d) => [d.time, d.value]),
    ]
      .map((row) => row.join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${signalId}_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Controls */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        <select
          value={timeWindow}
          onChange={(e) => setTimeWindow(Number(e.target.value))}
          style={{
            background: "#334155",
            border: "1px solid #475569",
            color: "#f1f5f9",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "13px",
          }}
        >
          <option value={60}>1 min</option>
          <option value={300}>5 min</option>
          <option value={900}>15 min</option>
          <option value={3600}>1 hour</option>
        </select>

        <button
          onClick={handleResetZoom}
          style={{
            background: "#334155",
            border: "1px solid #475569",
            color: "#f1f5f9",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Reset Zoom
        </button>

        <button
          onClick={() => setAutoScroll(!autoScroll)}
          style={{
            background: autoScroll ? "#2563eb" : "#334155",
            border: "1px solid #475569",
            color: "#f1f5f9",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          {autoScroll ? "Auto-Scroll: ON" : "Auto-Scroll: OFF"}
        </button>

        <button
          onClick={handleExport}
          style={{
            background: "#10b981",
            border: "1px solid #059669",
            color: "white",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Export CSV
        </button>

        <div style={{ marginLeft: "auto", color: "#94a3b8", fontSize: "13px", padding: "6px" }}>
          {data.length} points
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, minHeight: "250px" }}>
        {data.length > 0 ? (
          <Line ref={chartRef} data={chartData} options={options} />
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#64748b" }}>
            Loading waveform data...
          </div>
        )}
      </div>

      {/* Timeline Slider */}
      <TimelineSlider
        onTimeChange={handleTimeChange}
        minTime={minTime}
        maxTime={maxTime}
        currentTime={isLive ? maxTime : selectedTime}
        isLive={isLive}
      />
    </div>
  );
}
