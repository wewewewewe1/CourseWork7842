import React, { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend
);

/**
 * FrequencySpectrumChart - Display FFT frequency spectrum
 *
 * Shows frequency-domain representation of PMU signal with:
 * - Frequency bins on X-axis
 * - Magnitude on Y-axis
 * - Dominant frequency indicator
 * - Auto-refresh capability
 */
export default function FrequencySpectrumChart({
  signalId,
  refreshInterval = 5000,
  apiBaseUrl = "http://localhost:8000"
}) {
  const [spectrumData, setSpectrumData] = useState([]);
  const [dominantFreq, setDominantFreq] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadFFTData() {
    try {
      // Fetch FFT spectrum
      const spectrumRes = await fetch(
        `${apiBaseUrl}/analysis/fft/${signalId}/spectrum`
      );

      if (!spectrumRes.ok) {
        throw new Error(`HTTP error! status: ${spectrumRes.status}`);
      }

      const spectrum = await spectrumRes.json();

      // Fetch FFT summary for dominant frequency
      const summaryRes = await fetch(
        `${apiBaseUrl}/analysis/fft/${signalId}?limit=1`
      );

      if (!summaryRes.ok) {
        throw new Error(`HTTP error! status: ${summaryRes.status}`);
      }

      const summary = await summaryRes.json();

      if (Array.isArray(spectrum) && spectrum.length > 0) {
        setSpectrumData(spectrum);
        setError(null);
      } else {
        setSpectrumData([]);
      }

      if (summary && summary.length > 0) {
        setDominantFreq(summary[0]);
      }

      setLoading(false);
    } catch (err) {
      console.error("Failed to load FFT data:", err);
      setError(err.message);
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFFTData();
    const timer = setInterval(loadFFTData, refreshInterval);
    return () => clearInterval(timer);
  }, [signalId, refreshInterval]);

  if (loading) {
    return (
      <div className="chart-card" style={{ padding: "20px", textAlign: "center" }}>
        <p style={{ color: "#999" }}>Loading FFT data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chart-card" style={{ padding: "20px", textAlign: "center" }}>
        <p style={{ color: "#f44336" }}>Error: {error}</p>
      </div>
    );
  }

  if (spectrumData.length === 0) {
    return (
      <div className="chart-card" style={{ padding: "20px", textAlign: "center" }}>
        <p style={{ color: "#999" }}>No FFT data available yet...</p>
      </div>
    );
  }

  // Prepare chart data
  const frequencies = spectrumData.map((d) => parseFloat(d.frequency).toFixed(2));
  const magnitudes = spectrumData.map((d) => parseFloat(d.magnitude));

  // Create color array - highlight dominant frequency
  const backgroundColors = frequencies.map((freq) => {
    if (
      dominantFreq &&
      Math.abs(parseFloat(freq) - dominantFreq.dominant_freq) < 0.1
    ) {
      return "rgba(255, 99, 132, 0.8)"; // Red for dominant
    }
    return "rgba(54, 162, 235, 0.6)"; // Blue for others
  });

  const chartData = {
    labels: frequencies,
    datasets: [
      {
        label: "FFT Magnitude",
        data: magnitudes,
        backgroundColor: backgroundColors,
        borderColor: "rgba(54, 162, 235, 1)",
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "top",
      },
      title: {
        display: true,
        text: `Frequency Spectrum - ${signalId}`,
        font: { size: 16 },
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            return `Magnitude: ${context.parsed.y.toFixed(4)}`;
          },
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Frequency (Hz)",
        },
        ticks: {
          maxTicksLimit: 20,
          autoSkip: true,
        },
      },
      y: {
        title: {
          display: true,
          text: "Magnitude",
        },
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="chart-card" style={{ padding: "15px" }}>
      <div style={{ height: "400px" }}>
        <Bar data={chartData} options={options} />
      </div>

      {dominantFreq && (
        <div
          style={{
            marginTop: "15px",
            padding: "10px",
            backgroundColor: "#f5f5f5",
            borderRadius: "4px",
          }}
        >
          <h4 style={{ margin: "0 0 8px 0", fontSize: "14px" }}>
            Dominant Frequency Analysis
          </h4>
          <div style={{ fontSize: "13px", lineHeight: "1.6" }}>
            <div>
              <strong>Frequency:</strong> {dominantFreq.dominant_freq?.toFixed(3)} Hz
            </div>
            <div>
              <strong>Magnitude:</strong> {dominantFreq.dominant_magnitude?.toFixed(4)}
            </div>
            <div>
              <strong>Sample Rate:</strong> {dominantFreq.sample_rate} Hz
            </div>
            <div style={{ fontSize: "11px", color: "#666", marginTop: "5px" }}>
              Updated: {new Date(dominantFreq.time).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
