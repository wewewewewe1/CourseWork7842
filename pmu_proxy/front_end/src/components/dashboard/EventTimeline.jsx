import React, { useState, useEffect } from "react";

export default function EventTimeline({ maxEvents = 20, refreshInterval = 5000 }) {
  const [faults, setFaults] = useState([]);
  const [oscillations, setOscillations] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    async function fetchEvents() {
      try {
        const [faultsRes, oscRes] = await Promise.all([
          fetch(`http://localhost:8000/analysis/faults?limit=${maxEvents}`),
          fetch(`http://localhost:8000/analysis/oscillations?limit=${maxEvents}&detected_only=true`),
        ]);

        const faultsData = await faultsRes.json();
        const oscData = await oscRes.json();

        if (Array.isArray(faultsData)) setFaults(faultsData);
        if (Array.isArray(oscData)) setOscillations(oscData);
      } catch (error) {
        console.error("Failed to fetch events:", error);
      }
    }

    fetchEvents();
    const timer = setInterval(fetchEvents, refreshInterval);
    return () => clearInterval(timer);
  }, [maxEvents, refreshInterval]);

  // Combine and sort all events
  const allEvents = [
    ...faults.map((e) => ({ ...e, type: "fault" })),
    ...oscillations.map((e) => ({ ...e, type: "oscillation" })),
  ].sort((a, b) => new Date(b.time) - new Date(a.time));

  const filteredEvents = filter === "all" ? allEvents : allEvents.filter((e) => e.type === filter);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "12px" }}>
        <FilterTab
          label={`All (${allEvents.length})`}
          active={filter === "all"}
          onClick={() => setFilter("all")}
        />
        <FilterTab
          label={`Faults (${faults.length})`}
          active={filter === "fault"}
          onClick={() => setFilter("fault")}
        />
        <FilterTab
          label={`Oscillations (${oscillations.length})`}
          active={filter === "oscillation"}
          onClick={() => setFilter("oscillation")}
        />
      </div>

      {/* Event List */}
      <div style={{ flex: 1, overflowY: "auto", maxHeight: "400px" }}>
        {filteredEvents.length === 0 ? (
          <div style={{ textAlign: "center", color: "#64748b", padding: "20px" }}>
            No events detected
          </div>
        ) : (
          filteredEvents.map((event, idx) => (
            <EventCard key={idx} event={event} />
          ))
        )}
      </div>
    </div>
  );
}

function FilterTab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        background: active ? "#2563eb" : "#334155",
        border: "1px solid" + (active ? "#2563eb" : "#475569"),
        color: "white",
        padding: "8px",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "12px",
        fontWeight: active ? "600" : "400",
        transition: "all 0.15s",
      }}
    >
      {label}
    </button>
  );
}

function EventCard({ event }) {
  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case "critical": return "#dc2626";
      case "high": return "#ef4444";
      case "medium": return "#f59e0b";
      case "low": return "#eab308";
      default: return "#64748b";
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case "fault": return "⚠️";
      case "oscillation": return "〰️";
      default: return "•";
    }
  };

  const timeAgo = (timestamp) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return `${seconds}s ago`;
  };

  return (
    <div
      style={{
        background: "rgba(51, 65, 85, 0.5)",
        border: "1px solid #334155",
        borderLeft: `4px solid ${getSeverityColor(event.severity)}`,
        borderRadius: "6px",
        padding: "12px",
        marginBottom: "8px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span>{getTypeIcon(event.type)}</span>
          <span style={{ fontWeight: "600", fontSize: "14px", color: "#f1f5f9" }}>
            {event.signal_id || "Unknown Signal"}
          </span>
          <span
            style={{
              background: getSeverityColor(event.severity),
              color: "white",
              padding: "2px 8px",
              borderRadius: "10px",
              fontSize: "10px",
              fontWeight: "700",
              textTransform: "uppercase",
            }}
          >
            {event.severity}
          </span>
        </div>
        <div style={{ fontSize: "11px", color: "#94a3b8" }}>
          {timeAgo(event.time)}
        </div>
      </div>

      <div style={{ fontSize: "13px", color: "#cbd5e1", marginBottom: "4px" }}>
        {event.message || `${event.type} event detected`}
      </div>

      <div style={{ fontSize: "11px", color: "#64748b" }}>
        {new Date(event.time).toLocaleString()}
      </div>
    </div>
  );
}
