import React, { useEffect, useState } from "react";

/**
 * SignalQualityPanel - Display SNR and signal quality metrics
 *
 * Shows:
 * - SNR in dB
 * - Quality rating (excellent/good/fair/poor)
 * - THD (Total Harmonic Distortion)
 * - Signal and noise power levels
 */
export default function SignalQualityPanel({
  signalId,
  refreshInterval = 5000,
  apiBaseUrl = "http://localhost:8000"
}) {
  const [snrData, setSnrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadSNRData() {
    try {
      const res = await fetch(
        `${apiBaseUrl}/analysis/snr/${signalId}?limit=1`
      );

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();

      if (data && data.length > 0) {
        setSnrData(data[0]);
        setError(null);
      }

      setLoading(false);
    } catch (err) {
      console.error("Failed to load SNR data:", err);
      setError(err.message);
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSNRData();
    const timer = setInterval(loadSNRData, refreshInterval);
    return () => clearInterval(timer);
  }, [signalId, refreshInterval]);

  // Quality color mapping
  const getQualityColor = (quality) => {
    switch (quality) {
      case "excellent":
        return "#4caf50"; // Green
      case "good":
        return "#8bc34a"; // Light green
      case "fair":
        return "#ff9800"; // Orange
      case "poor":
        return "#f44336"; // Red
      default:
        return "#9e9e9e"; // Gray
    }
  };

  const getQualityBadge = (quality) => {
    const color = getQualityColor(quality);
    return (
      <span
        style={{
          backgroundColor: color,
          color: "white",
          padding: "4px 12px",
          borderRadius: "12px",
          fontSize: "12px",
          fontWeight: "bold",
          textTransform: "uppercase",
        }}
      >
        {quality}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="chart-card" style={{ padding: "20px", textAlign: "center" }}>
        <p style={{ color: "#999" }}>Loading quality metrics...</p>
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

  if (!snrData) {
    return (
      <div className="chart-card" style={{ padding: "20px", textAlign: "center" }}>
        <p style={{ color: "#999" }}>No quality data available yet...</p>
      </div>
    );
  }

  return (
    <div className="chart-card" style={{ padding: "20px" }}>
      <h3 style={{ margin: "0 0 15px 0", fontSize: "18px" }}>
        Signal Quality - {signalId}
      </h3>

      {/* Quality Badge */}
      <div style={{ marginBottom: "20px", textAlign: "center" }}>
        {getQualityBadge(snrData.quality)}
      </div>

      {/* SNR Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
        <div className="metric-box">
          <div className="metric-label">SNR (Combined)</div>
          <div className="metric-value">
            {snrData.snr_db?.toFixed(2)} dB
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">SNR (Linear)</div>
          <div className="metric-value">
            {snrData.snr_linear?.toFixed(2)}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">SNR (Frequency)</div>
          <div className="metric-value">
            {snrData.snr_freq_db?.toFixed(2)} dB
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">SNR (Time)</div>
          <div className="metric-value">
            {snrData.snr_time_db?.toFixed(2)} dB
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">Signal Power</div>
          <div className="metric-value">
            {snrData.signal_power?.toExponential(2)}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">Noise Power</div>
          <div className="metric-value">
            {snrData.noise_power?.toExponential(2)}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">THD</div>
          <div className="metric-value">
            {snrData.thd_percent?.toFixed(2)}%
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">DC Offset</div>
          <div className="metric-value">
            {snrData.dc_offset?.toFixed(4)}
          </div>
        </div>
      </div>

      {/* Timestamp */}
      <div
        style={{
          marginTop: "15px",
          fontSize: "11px",
          color: "#666",
          textAlign: "center",
        }}
      >
        Updated: {new Date(snrData.time).toLocaleString()}
      </div>

      <style jsx>{`
        .metric-box {
          background-color: #f5f5f5;
          padding: 12px;
          border-radius: 6px;
          text-align: center;
        }

        .metric-label {
          font-size: 11px;
          color: #666;
          text-transform: uppercase;
          margin-bottom: 6px;
          font-weight: 500;
        }

        .metric-value {
          font-size: 16px;
          font-weight: bold;
          color: #333;
        }
      `}</style>
    </div>
  );
}
