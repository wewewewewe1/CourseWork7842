import React, { useState, useEffect } from "react";

export default function SystemOverview({ signals = [] }) {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch("http://localhost:8000/analysis/health");
        const json = await res.json();
        setHealth(json);
      } catch (error) {
        console.error("Failed to fetch system health:", error);
      }
    }

    fetchHealth();
    const timer = setInterval(fetchHealth, 10000); // Check every 10 seconds
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      style={{
        background: "rgba(51, 65, 85, 0.3)",
        border: "1px solid #334155",
        borderRadius: "8px",
        padding: "12px",
      }}
    >
      <StatusRow
        label="Analysis System"
        value={health?.status || "unknown"}
        status={health?.status === "running"}
      />
      <StatusRow
        label="Monitored Signals"
        value={signals.length}
        status={signals.length > 0}
      />
      <StatusRow
        label="Analysis Interval"
        value={`${health?.analysis_interval || "?"}s`}
        status={true}
      />
      <StatusRow
        label="Sample Rate"
        value={`${health?.sample_rate || "?"} Hz`}
        status={true}
      />

      {health && (
        <div style={{ marginTop: "12px", fontSize: "10px", color: "#64748b", textAlign: "center" }}>
          Updated: {new Date().toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

function StatusRow({ label, value, status }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "8px",
        padding: "6px 0",
        borderBottom: "1px solid rgba(51, 65, 85, 0.5)",
      }}
    >
      <span style={{ fontSize: "12px", color: "#94a3b8" }}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontSize: "12px", fontWeight: "600", color: "#f1f5f9" }}>
          {value}
        </span>
        <div
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: status ? "#10b981" : "#64748b",
          }}
        />
      </div>
    </div>
  );
}
