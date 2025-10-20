import React, { useEffect, useState } from "react";
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
import { getData } from "../api";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend
);

export default function ChartPanel({ signalId, refreshInterval = 2000 }) {
  const [data, setData] = useState([]);

  async function loadData() {
    try {
      const res = await getData(signalId);
      if (Array.isArray(res)) {
        setData(res);
      } else {
        console.warn("Unexpected data format:", res);
        setData([]);
      }
    } catch (err) {
      console.error("Failed to load data:", err);
      setData([]);
    }
  }

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, refreshInterval);
    return () => clearInterval(timer);
  }, [signalId]);

  const labels = data.map((d) => {
    try {
      return new Date(d.time).toLocaleTimeString();
    } catch {
      return "";
    }
  });

  const values = data.map((d) => parseFloat(d.value) || 0);

  const chartData = {
    labels,
    datasets: [
      {
        label: signalId,
        data: values,
        borderColor: "#4e79a7",
        backgroundColor: "rgba(78,121,167,0.3)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: true, position: "top" },
      title: { display: true, text: signalId },
    },
    scales: {
      x: { ticks: { maxTicksLimit: 10 } },
      y: { beginAtZero: false },
    },
  };

  return (
    <div className="chart-card">
      {data.length === 0 ? (
        <p style={{ textAlign: "center", color: "#999" }}>
          Loading or no data yet...
        </p>
      ) : (
        <Line data={chartData} options={options} />
      )}
    </div>
  );
}
