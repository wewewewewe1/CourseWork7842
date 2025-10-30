import React, { useState, useEffect } from "react";

export default function AnalysisMetrics({ signalId = "PPA:2", refreshInterval = 5000 }) {
  const [oscillation, setOscillation] = useState(null);
  const [fault, setFault] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [oscRes, faultRes] = await Promise.all([
          fetch(`http://localhost:8000/analysis/oscillations/${signalId}?limit=1`),
          fetch(`http://localhost:8000/analysis/faults?limit=1`),
        ]);

        const oscData = await oscRes.json();
        const faultData = await faultRes.json();

        if (Array.isArray(oscData) && oscData.length > 0) setOscillation(oscData[0]);
        if (Array.isArray(faultData) && faultData.length > 0) setFault(faultData[0]);
      } catch (error) {
        console.error("Failed to fetch analysis metrics:", error);
      }
    }

    fetchData();
    const timer = setInterval(fetchData, refreshInterval);
    return () => clearInterval(timer);
  }, [signalId, refreshInterval]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: "12px" }}>
      {/* Oscillation Metrics */}
      <MetricPanel
        title="Oscillation Detection"
        icon="〰️"
        data={oscillation}
        status={oscillation?.detected === "True" || oscillation?.detected === true}
      >
        {oscillation ? (
          <>
            <MetricRow label="Frequency" value={`${oscillation.oscillation_frequency?.toFixed(2)} Hz`} />
            <MetricRow label="Type" value={oscillation.oscillation_type || "none"} />
            <MetricRow label="Damping" value={`${(oscillation.damping_ratio * 100).toFixed(1)}%`} />
            <MetricRow label="Power" value={oscillation.oscillation_power?.toExponential(2)} />
          </>
        ) : (
          <div style={{ color: "#64748b", fontSize: "13px" }}>No data</div>
        )}
      </MetricPanel>

      {/* Fault Metrics */}
      <MetricPanel
        title="Fault Detection"
        icon="⚠️"
        data={fault}
        status={fault !== null}
      >
        {fault ? (
          <>
            <MetricRow label="Type" value={fault.fault_type || "none"} />
            <MetricRow label="Severity" value={fault.severity || "normal"} />
            <MetricRow label="Deviation" value={`${(fault.deviation_ratio * 100).toFixed(2)}%`} />
            <MetricRow label="Signal" value={fault.signal_id} />
          </>
        ) : (
          <div style={{ color: "#64748b", fontSize: "13px" }}>No faults detected</div>
        )}
      </MetricPanel>
    </div>
  );
}

function MetricPanel({ title, icon, data, status, children }) {
  const statusColor = status ? "#ef4444" : "#10b981";

  return (
    <div
      style={{
        background: "rgba(51, 65, 85, 0.5)",
        border: "1px solid #334155",
        borderRadius: "8px",
        padding: "12px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "18px" }}>{icon}</span>
          <span style={{ fontSize: "14px", fontWeight: "600", color: "#f1f5f9" }}>
            {title}
          </span>
        </div>
        <div
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: statusColor,
            boxShadow: `0 0 8px ${statusColor}`,
          }}
        />
      </div>
      <div>{children}</div>
    </div>
  );
}

function MetricRow({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
      <span style={{ fontSize: "12px", color: "#94a3b8" }}>{label}:</span>
      <span style={{ fontSize: "12px", fontWeight: "600", color: "#cbd5e1" }}>{value}</span>
    </div>
  );
}
