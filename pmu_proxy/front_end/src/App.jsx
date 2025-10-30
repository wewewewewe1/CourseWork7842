// ================================================
// App_New.jsx — Professional PMU Monitoring Dashboard
// Complete reconstruction with modern design and full analysis integration
// ================================================
import React, { useState, useEffect } from "react";
import { getSignals } from "./api";

// Core analysis components
import RealTimeWaveform from "./components/dashboard/RealTimeWaveform";
import FrequencySpectrum from "./components/dashboard/FrequencySpectrum";
import SignalQuality from "./components/dashboard/SignalQuality";
import EventTimeline from "./components/dashboard/EventTimeline";
import SystemOverview from "./components/dashboard/SystemOverview";
import AnalysisMetrics from "./components/dashboard/AnalysisMetrics";
import WarningSystemPage from "./components/WarningSystemPage";

// Legacy custom chart support
import ChartCard from "./components/ChartCard";
import ChartEditor from "./components/ChartEditor";

// Styles
import "./styles/Dashboard.css";

document.title = "PMU Analysis & Monitoring Platform";

export default function App() {
  // Page routing
  const [currentPage, setCurrentPage] = useState("dashboard"); // 'dashboard' or 'warnings'

  // System state
  const [signals, setSignals] = useState([]);
  const [selectedSignal, setSelectedSignal] = useState("PPA:2");
  const [systemStatus, setSystemStatus] = useState("loading");

  // Custom charts (legacy feature)
  const [customCharts, setCustomCharts] = useState([]);
  const [showCustomCharts, setShowCustomCharts] = useState(false);
  const [editing, setEditing] = useState(null);

  // Layout state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Initialize system
  useEffect(() => {
    async function init() {
      try {
        const sigs = await getSignals();
        setSignals(sigs);
        setSystemStatus("online");

        // Set default selected signal
        if (sigs.length > 0 && !selectedSignal) {
          setSelectedSignal(sigs[0].id);
        }
      } catch (error) {
        console.error("Failed to initialize:", error);
        setSystemStatus("error");
      }
    }
    init();
  }, []);

  // Custom chart handlers (legacy feature retained)
  const handleAddChart = () => setEditing({});
  const handleSaveChart = (cfg) => {
    if (editing.index != null) {
      const next = [...customCharts];
      next[editing.index] = cfg;
      setCustomCharts(next);
    } else {
      setCustomCharts([...customCharts, cfg]);
    }
    setEditing(null);
  };
  const handleRemoveChart = (idx) => {
    setCustomCharts(customCharts.filter((_, i) => i !== idx));
  };
  const handleEditChart = (idx) => {
    setEditing({ ...customCharts[idx], index: idx });
  };
  const handleRenameChart = (idx, newName) => {
    const next = [...customCharts];
    next[idx] = { ...next[idx], name: newName };
    setCustomCharts(next);
  };

  // Render Warning System Page
  if (currentPage === "warnings") {
    return <WarningSystemPage onNavigateBack={() => setCurrentPage("dashboard")} />;
  }

  // Render Main Dashboard
  return (
    <div className="dashboard-container">
      {/* Top Navigation Bar */}
      <nav className="top-navbar">
        <div className="nav-brand">
          <div className="brand-icon">⚡</div>
          <div className="brand-text">
            <div className="brand-title">PMU Analysis Platform</div>
            <div className="brand-subtitle">Real-Time Grid Monitoring</div>
          </div>
        </div>

        <div className="nav-controls">
          {/* Page Navigation */}
          <button
            onClick={() => setCurrentPage("warnings")}
            className="nav-btn warning-nav-btn"
            title="Warning System"
          >
            <span className="nav-icon">⚠</span>
            Warning System
          </button>

          {/* Signal Selector */}
          <div className="signal-selector">
            <label>Active Signal:</label>
            <select
              value={selectedSignal}
              onChange={(e) => setSelectedSignal(e.target.value)}
              className="signal-dropdown"
            >
              {signals.map((sig) => (
                <option key={sig.id} value={sig.id}>
                  {sig.id} ({sig.type})
                </option>
              ))}
            </select>
          </div>

          {/* System Status */}
          <div className={`system-status status-${systemStatus}`}>
            <span className="status-dot"></span>
            {systemStatus === "online" ? "ONLINE" : systemStatus === "error" ? "ERROR" : "LOADING"}
          </div>
        </div>
      </nav>

      {/* Main Layout */}
      <div className="main-layout">
        {/* Sidebar */}
        <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
          <button
            className="collapse-btn"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            {sidebarCollapsed ? "»" : "«"}
          </button>

          {!sidebarCollapsed && (
            <div className="sidebar-content">
              <div className="sidebar-section">
                <h3>System Overview</h3>
                <SystemOverview signals={signals} />
              </div>

              <div className="sidebar-section">
                <h3>Monitored Signals</h3>
                <div className="signal-list">
                  {signals.map((sig) => (
                    <div
                      key={sig.id}
                      className={`signal-item ${sig.id === selectedSignal ? "active" : ""}`}
                      onClick={() => setSelectedSignal(sig.id)}
                    >
                      <div className="signal-name">{sig.id}</div>
                      <div className="signal-type">{sig.type}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* Main Content */}
        <main className="main-content">
          {/* Core Analysis Dashboard (Always Visible) */}
          <div className="analysis-dashboard">
            {/* Row 1: Real-Time Waveform (Full Width) */}
            <div className="dashboard-row row-full">
              <div className="panel panel-large">
                <div className="panel-header">
                  <h2>Real-Time Waveform</h2>
                  <div className="panel-subtitle">
                    Live PMU measurement with pan & zoom controls
                  </div>
                </div>
                <div className="panel-content">
                  <RealTimeWaveform signalId={selectedSignal} />
                </div>
              </div>
            </div>

            {/* Row 2: FFT Spectrum + Signal Quality */}
            <div className="dashboard-row row-split">
              <div className="panel panel-medium">
                <div className="panel-header">
                  <h2>Frequency Spectrum (FFT)</h2>
                  <div className="panel-subtitle">
                    Dominant modes and frequency decomposition
                  </div>
                </div>
                <div className="panel-content">
                  <FrequencySpectrum signalId={selectedSignal} />
                </div>
              </div>

              <div className="panel panel-medium">
                <div className="panel-header">
                  <h2>Signal Quality (SNR)</h2>
                  <div className="panel-subtitle">
                    Noise analysis and quality metrics
                  </div>
                </div>
                <div className="panel-content">
                  <SignalQuality signalId={selectedSignal} />
                </div>
              </div>
            </div>

            {/* Row 3: Analysis Metrics + Event Timeline */}
            <div className="dashboard-row row-split">
              <div className="panel panel-medium">
                <div className="panel-header">
                  <h2>Analysis Metrics</h2>
                  <div className="panel-subtitle">
                    Oscillation and fault detection
                  </div>
                </div>
                <div className="panel-content">
                  <AnalysisMetrics signalId={selectedSignal} />
                </div>
              </div>

              <div className="panel panel-medium">
                <div className="panel-header">
                  <h2>Event Timeline</h2>
                  <div className="panel-subtitle">
                    Recent faults, oscillations, and anomalies
                  </div>
                </div>
                <div className="panel-content">
                  <EventTimeline />
                </div>
              </div>
            </div>
          </div>

          {/* Custom Charts Section (Toggle Visibility) */}
          {showCustomCharts && customCharts.length > 0 && (
            <div className="custom-charts-section">
              <div className="section-header">
                <h2>Custom Charts</h2>
                <button onClick={() => setShowCustomCharts(false)}>Hide</button>
              </div>
              <div className="custom-charts-grid">
                {customCharts.map((cfg, idx) => (
                  <ChartCard
                    key={idx}
                    cfg={cfg}
                    onEdit={() => handleEditChart(idx)}
                    onRename={(name) => handleRenameChart(idx, name)}
                    onRemove={() => handleRemoveChart(idx)}
                  />
                ))}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Chart Editor Modal */}
      {editing && (
        <div className="modal-overlay">
          <div className="modal-content">
            <ChartEditor
              initial={editing}
              onSave={handleSaveChart}
              onCancel={() => setEditing(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
