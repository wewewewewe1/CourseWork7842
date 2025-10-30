import React, { useState, useEffect } from "react";

export default function SignalQuality({ signalId = "PPA:2", refreshInterval = 5000 }) {
  const [snrData, setSnrData] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch(`http://localhost:8000/analysis/snr/${signalId}?limit=1`);
        const json = await res.json();
        if (Array.isArray(json) && json.length > 0) {
          setSnrData(json[0]);
        }
      } catch (error) {
        console.error("Failed to fetch SNR data:", error);
      }
    }

    fetchData();
    const timer = setInterval(fetchData, refreshInterval);
    return () => clearInterval(timer);
  }, [signalId, refreshInterval]);

  const getQualityColor = (quality) => {
    switch (quality?.toLowerCase()) {
      case "excellent": return "#10b981";
      case "good": return "#3b82f6";
      case "fair": return "#f59e0b";
      case "poor": return "#ef4444";
      default: return "#64748b";
    }
  };

  if (!snrData) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#64748b" }}>
        Loading quality data...
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Quality Badge */}
      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <div
          style={{
            display: "inline-block",
            background: getQualityColor(snrData.quality),
            color: "white",
            padding: "12px 32px",
            borderRadius: "24px",
            fontSize: "18px",
            fontWeight: "700",
            textTransform: "uppercase",
            letterSpacing: "1px",
            boxShadow: `0 0 20px ${getQualityColor(snrData.quality)}40`,
          }}
        >
          {snrData.quality}
        </div>
      </div>

      {/* Metrics Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
        }}
      >
        <MetricCard label="SNR (Combined)" value={`${snrData.snr_db?.toFixed(2)} dB`} />
        <MetricCard label="SNR (Linear)" value={snrData.snr_linear?.toFixed(2)} />
        <MetricCard label="THD" value={`${snrData.thd_percent?.toFixed(2)}%`} />
        <MetricCard label="Signal Power" value={snrData.signal_power?.toExponential(2)} />
        <MetricCard label="Noise Power" value={snrData.noise_power?.toExponential(2)} />
        <MetricCard label="DC Offset" value={snrData.dc_offset?.toFixed(4)} />
      </div>

      <div style={{ marginTop: "16px", fontSize: "11px", color: "#64748b", textAlign: "center" }}>
        Updated: {new Date(snrData.time).toLocaleString()}
      </div>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div
      style={{
        background: "rgba(51, 65, 85, 0.5)",
        border: "1px solid #334155",
        borderRadius: "8px",
        padding: "12px",
      }}
    >
      <div style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "4px", textTransform: "uppercase" }}>
        {label}
      </div>
      <div style={{ fontSize: "16px", fontWeight: "700", color: "#f1f5f9" }}>
        {value}
      </div>
    </div>
  );
}
