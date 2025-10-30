import React, { useEffect, useState } from "react";

/**
 * EventMarkersPanel - Display detected events (faults, oscillations)
 *
 * Shows:
 * - Recent fault events with severity
 * - Oscillation alerts
 * - Event timestamps and details
 */
export default function EventMarkersPanel({
  refreshInterval = 5000,
  apiBaseUrl = "http://localhost:8000",
  maxEvents = 20
}) {
  const [faults, setFaults] = useState([]);
  const [oscillations, setOscillations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("faults");

  async function loadEvents() {
    try {
      // Load faults
      const faultsRes = await fetch(
        `${apiBaseUrl}/analysis/faults?limit=${maxEvents}`
      );
      if (faultsRes.ok) {
        const faultsData = await faultsRes.json();
        setFaults(Array.isArray(faultsData) ? faultsData : []);
      }

      // Load oscillations
      const oscRes = await fetch(
        `${apiBaseUrl}/analysis/oscillations?limit=${maxEvents}&detected_only=true`
      );
      if (oscRes.ok) {
        const oscData = await oscRes.json();
        setOscillations(Array.isArray(oscData) ? oscData : []);
      }

      setLoading(false);
    } catch (err) {
      console.error("Failed to load events:", err);
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents();
    const timer = setInterval(loadEvents, refreshInterval);
    return () => clearInterval(timer);
  }, [refreshInterval]);

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case "critical":
        return "#d32f2f"; // Dark red
      case "high":
        return "#f44336"; // Red
      case "medium":
        return "#ff9800"; // Orange
      case "low":
        return "#ffc107"; // Yellow
      default:
        return "#9e9e9e"; // Gray
    }
  };

  const SeverityBadge = ({ severity }) => (
    <span
      style={{
        backgroundColor: getSeverityColor(severity),
        color: "white",
        padding: "2px 8px",
        borderRadius: "10px",
        fontSize: "10px",
        fontWeight: "bold",
        textTransform: "uppercase",
      }}
    >
      {severity}
    </span>
  );

  const EventItem = ({ event, type }) => (
    <div
      style={{
        padding: "12px",
        marginBottom: "8px",
        backgroundColor: "#f9f9f9",
        borderRadius: "6px",
        borderLeft: `4px solid ${getSeverityColor(event.severity)}`,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "6px",
        }}
      >
        <div style={{ fontWeight: "bold", fontSize: "13px" }}>
          {event.signal_id || "Unknown Signal"}
        </div>
        <SeverityBadge severity={event.severity} />
      </div>

      <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
        {event.message || `${type} event detected`}
      </div>

      {type === "fault" && (
        <div style={{ fontSize: "11px", color: "#888" }}>
          Type: {event.fault_type} | Deviation: {(event.deviation_ratio * 100).toFixed(2)}%
        </div>
      )}

      {type === "oscillation" && (
        <div style={{ fontSize: "11px", color: "#888" }}>
          Type: {event.type} | Freq: {event.frequency?.toFixed(2)} Hz | Damping: {(event.damping * 100).toFixed(1)}%
        </div>
      )}

      <div style={{ fontSize: "10px", color: "#999", marginTop: "4px" }}>
        {new Date(event.time).toLocaleString()}
      </div>
    </div>
  );

  const TabButton = ({ name, label, count }) => (
    <button
      onClick={() => setActiveTab(name)}
      style={{
        flex: 1,
        padding: "10px",
        backgroundColor: activeTab === name ? "#2196f3" : "#e0e0e0",
        color: activeTab === name ? "white" : "#333",
        border: "none",
        borderRadius: "4px 4px 0 0",
        cursor: "pointer",
        fontSize: "13px",
        fontWeight: activeTab === name ? "bold" : "normal",
        transition: "all 0.2s",
      }}
    >
      {label} ({count})
    </button>
  );

  if (loading) {
    return (
      <div className="chart-card" style={{ padding: "20px", textAlign: "center" }}>
        <p style={{ color: "#999" }}>Loading events...</p>
      </div>
    );
  }

  return (
    <div className="chart-card" style={{ padding: "0" }}>
      {/* Tab Headers */}
      <div style={{ display: "flex", gap: "2px", padding: "10px 10px 0 10px" }}>
        <TabButton name="faults" label="Faults" count={faults.length} />
        <TabButton name="oscillations" label="Oscillations" count={oscillations.length} />
      </div>

      {/* Tab Content */}
      <div
        style={{
          padding: "15px",
          maxHeight: "500px",
          overflowY: "auto",
          backgroundColor: "white",
        }}
      >
        {activeTab === "faults" && (
          <div>
            <h4 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>
              Fault Events
            </h4>
            {faults.length === 0 ? (
              <p style={{ color: "#999", fontSize: "13px" }}>No fault events detected</p>
            ) : (
              faults.map((fault, idx) => (
                <EventItem key={idx} event={fault} type="fault" />
              ))
            )}
          </div>
        )}

        {activeTab === "oscillations" && (
          <div>
            <h4 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>
              Oscillation Events
            </h4>
            {oscillations.length === 0 ? (
              <p style={{ color: "#999", fontSize: "13px" }}>No oscillation events detected</p>
            ) : (
              oscillations.map((osc, idx) => (
                <EventItem key={idx} event={osc} type="oscillation" />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
