import React, { useState, useEffect } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import TimelineSlider from "../TimelineSlider";

ChartJS.register(BarElement, CategoryScale, LinearScale, Title, Tooltip, Legend);

export default function FrequencySpectrum({ signalId = "PPA:2", refreshInterval = 5000 }) {
  const [spectrumData, setSpectrumData] = useState([]);
  const [summary, setSummary] = useState(null);

  // Timeline slider state
  const [isLive, setIsLive] = useState(true);
  const [selectedTime, setSelectedTime] = useState(new Date());
  const [minTime, setMinTime] = useState(new Date(Date.now() - 3600000)); // 1 hour ago
  const [maxTime, setMaxTime] = useState(new Date());

  useEffect(() => {
    async function fetchData() {
      try {
        const [specRes, summRes] = await Promise.all([
          fetch(`http://localhost:8000/analysis/fft/${signalId}/spectrum`),
          fetch(`http://localhost:8000/analysis/fft/${signalId}?limit=1`),
        ]);

        const spectrum = await specRes.json();
        const summaryData = await summRes.json();

        if (Array.isArray(spectrum)) setSpectrumData(spectrum);
        if (Array.isArray(summaryData) && summaryData.length > 0) {
          setSummary(summaryData[0]);

          // Update time bounds from data
          if (summaryData[0].time) {
            const dataTime = new Date(summaryData[0].time);
            setMaxTime(dataTime);
            setMinTime(new Date(dataTime.getTime() - 3600000)); // 1 hour before
          }
        }
      } catch (error) {
        console.error("Failed to fetch FFT data:", error);
      }
    }

    fetchData();

    // Only auto-refresh in live mode
    if (isLive) {
      const timer = setInterval(fetchData, refreshInterval);
      return () => clearInterval(timer);
    }
  }, [signalId, refreshInterval, isLive]);

  // Handle timeline slider changes
  const handleTimeChange = (newTime, nowIsLive) => {
    setSelectedTime(newTime);
    setIsLive(nowIsLive);
  };

  const frequencies = spectrumData.map((d) => parseFloat(d.frequency).toFixed(2));
  const magnitudes = spectrumData.map((d) => parseFloat(d.magnitude));

  const chartData = {
    labels: frequencies,
    datasets: [
      {
        label: "FFT Magnitude",
        data: magnitudes,
        backgroundColor: "rgba(37, 99, 235, 0.7)",
        borderColor: "rgb(37, 99, 235)",
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleColor: "#f1f5f9",
        bodyColor: "#cbd5e1",
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Frequency (Hz)",
          color: "#94a3b8",
        },
        grid: {
          color: "rgba(148, 163, 184, 0.1)",
        },
        ticks: {
          color: "#94a3b8",
          maxTicksLimit: 20,
        },
      },
      y: {
        title: {
          display: true,
          text: "Magnitude",
          color: "#94a3b8",
        },
        grid: {
          color: "rgba(148, 163, 184, 0.1)",
        },
        ticks: {
          color: "#94a3b8",
        },
      },
    },
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {summary && (
        <div
          style={{
            background: "rgba(37, 99, 235, 0.1)",
            border: "1px solid rgba(37, 99, 235, 0.3)",
            borderRadius: "6px",
            padding: "12px",
            marginBottom: "12px",
          }}
        >
          <div style={{ fontSize: "13px", color: "#cbd5e1", marginBottom: "6px" }}>
            Dominant Frequency
          </div>
          <div style={{ fontSize: "24px", fontWeight: "700", color: "#3b82f6" }}>
            {summary.dominant_freq?.toFixed(3)} Hz
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
            Magnitude: {summary.dominant_magnitude?.toFixed(4)}
          </div>
        </div>
      )}

      <div style={{ flex: 1, minHeight: "200px" }}>
        {spectrumData.length > 0 ? (
          <Bar data={chartData} options={options} />
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#64748b" }}>
            Loading spectrum data...
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
