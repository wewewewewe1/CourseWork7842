import React, { useState } from "react";
import FrequencySpectrumChart from "./FrequencySpectrumChart";
import SignalQualityPanel from "./SignalQualityPanel";
import EventMarkersPanel from "./EventMarkersPanel";
import ChartPanel from "./ChartPanel";

/**
 * AnalysisDashboard - Comprehensive analysis view
 *
 * Combines time-domain and frequency-domain visualization with quality metrics
 * and event detection in a single dashboard layout.
 *
 * Usage:
 *   <AnalysisDashboard signalId="PPA:2" />
 */
export default function AnalysisDashboard({
  signalId = "PPA:2",
  apiBaseUrl = "http://localhost:8000"
}) {
  const [selectedSignal, setSelectedSignal] = useState(signalId);
  const [signals] = useState(["PPA:2", "PPA:7"]); // Available signals

  return (
    <div style={{ padding: "20px", backgroundColor: "#f5f5f5", minHeight: "100vh" }}>
      {/* Header */}
      <div
        style={{
          marginBottom: "20px",
          padding: "20px",
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
        }}
      >
        <h1 style={{ margin: "0 0 15px 0", fontSize: "24px", color: "#333" }}>
          PMU Signal Analysis Dashboard
        </h1>

        {/* Signal Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <label style={{ fontSize: "14px", fontWeight: "500" }}>
            Select Signal:
          </label>
          <select
            value={selectedSignal}
            onChange={(e) => setSelectedSignal(e.target.value)}
            style={{
              padding: "8px 12px",
              fontSize: "14px",
              borderRadius: "4px",
              border: "1px solid #ccc",
              cursor: "pointer",
            }}
          >
            {signals.map((sig) => (
              <option key={sig} value={sig}>
                {sig}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "20px",
          marginBottom: "20px",
        }}
      >
        {/* Left Column - Time Domain */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Time-Domain Chart */}
          <div
            style={{
              backgroundColor: "white",
              borderRadius: "8px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              overflow: "hidden",
            }}
          >
            <ChartPanel signalId={selectedSignal} refreshInterval={2000} />
          </div>

          {/* Frequency Spectrum */}
          <div
            style={{
              backgroundColor: "white",
              borderRadius: "8px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              overflow: "hidden",
            }}
          >
            <FrequencySpectrumChart
              signalId={selectedSignal}
              refreshInterval={5000}
              apiBaseUrl={apiBaseUrl}
            />
          </div>
        </div>

        {/* Right Column - Quality & Events */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Signal Quality Panel */}
          <div
            style={{
              backgroundColor: "white",
              borderRadius: "8px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              overflow: "hidden",
            }}
          >
            <SignalQualityPanel
              signalId={selectedSignal}
              refreshInterval={5000}
              apiBaseUrl={apiBaseUrl}
            />
          </div>

          {/* Event Markers */}
          <div
            style={{
              backgroundColor: "white",
              borderRadius: "8px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              overflow: "hidden",
            }}
          >
            <EventMarkersPanel
              refreshInterval={5000}
              apiBaseUrl={apiBaseUrl}
              maxEvents={15}
            />
          </div>
        </div>
      </div>

      {/* System Status Footer */}
      <div
        style={{
          padding: "15px 20px",
          backgroundColor: "white",
          borderRadius: "8px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          fontSize: "12px",
          color: "#666",
          textAlign: "center",
        }}
      >
        <div>
          PMU Analysis System | Monitoring: {signals.join(", ")} |{" "}
          <span style={{ color: "#4caf50", fontWeight: "bold" }}>● ONLINE</span>
        </div>
      </div>
    </div>
  );
}
