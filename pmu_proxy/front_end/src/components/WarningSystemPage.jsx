import React, { useState, useEffect } from 'react';
import './WarningSystemPage.css';

/**
 * Full-Page Warning System Dashboard
 *
 * Features:
 * - Full-screen warning management
 * - Real-time monitoring with live updates
 * - Historical analysis with advanced filtering
 * - Performance metrics and statistics
 * - Threshold configuration UI
 * - Event acknowledgment and management
 */
export default function WarningSystemPage({ onNavigateBack }) {
  const [activeTab, setActiveTab] = useState('realtime'); // 'realtime', 'historical', 'config', 'stats'
  const [activeWarnings, setActiveWarnings] = useState([]);
  const [historicalWarnings, setHistoricalWarnings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [filters, setFilters] = useState({
    severity: 'all',
    signal: 'all',
    state: 'all',
    startTime: '',
    endTime: '',
    limit: 100
  });

  const API_BASE = 'http://localhost:8000';

  // Fetch active warnings
  const fetchActiveWarnings = async () => {
    try {
      const response = await fetch(`${API_BASE}/warnings/active`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setActiveWarnings(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching active warnings:', err);
      setError(err.message);
    }
  };

  // Fetch historical warnings
  const fetchHistoricalWarnings = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: filters.limit.toString() });
      if (filters.severity !== 'all') params.append('severity', filters.severity);
      if (filters.signal !== 'all') params.append('signal_id', filters.signal);
      if (filters.startTime) params.append('start_time', filters.startTime);
      if (filters.endTime) params.append('end_time', filters.endTime);

      const response = await fetch(`${API_BASE}/warnings/historical?${params}`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setHistoricalWarnings(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching historical warnings:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/warnings/stats`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  // Acknowledge event
  const acknowledgeEvent = async (eventId) => {
    try {
      const response = await fetch(
        `${API_BASE}/warnings/${eventId}/acknowledge?user=operator`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to acknowledge');
      fetchActiveWarnings();
    } catch (err) {
      alert('Failed to acknowledge event: ' + err.message);
    }
  };

  // Auto-refresh for real-time tab
  useEffect(() => {
    fetchActiveWarnings();
    fetchStats();

    if (activeTab === 'realtime') {
      const interval = setInterval(() => {
        fetchActiveWarnings();
        fetchStats();
      }, 500);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  // Fetch historical when tab or filters change
  useEffect(() => {
    if (activeTab === 'historical') {
      fetchHistoricalWarnings();
    }
  }, [activeTab, filters]);

  // Format time
  const formatTime = (isoString) => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return 'Active';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  // Get severity class
  const getSeverityClass = (severity) => {
    return `severity-badge-${(severity || '').toLowerCase()}`;
  };

  // Render warning card
  const renderWarningCard = (warning, compact = false) => (
    <div key={warning.event_id} className={`warning-card-full ${compact ? 'compact' : ''}`}>
      <div className="card-header">
        <div className="card-left">
          <span className={getSeverityClass(warning.severity)}>
            {warning.severity}
          </span>
          <span className={`state-badge-${(warning.state || '').toLowerCase()}`}>
            {warning.state}
          </span>
        </div>
        <div className="card-right">
          <span className="event-time">{formatTime(warning.event_start_time)}</span>
        </div>
      </div>

      <div className="card-body">
        <div className="signal-info">
          <h3>{warning.signal_id}</h3>
          <span className="signal-type">{warning.signal_type}</span>
        </div>

        <div className="metrics-grid">
          <div className="metric">
            <span className="metric-label">Trigger Value</span>
            <span className="metric-value">{warning.trigger_value?.toFixed(3)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Threshold</span>
            <span className="metric-value">
              {warning.threshold_type} {warning.threshold_value?.toFixed(3)}
            </span>
          </div>
          <div className="metric">
            <span className="metric-label">Deviation</span>
            <span className="metric-value critical">{warning.max_deviation?.toFixed(3)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Duration</span>
            <span className="metric-value">{formatDuration(warning.duration)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Trigger Count</span>
            <span className="metric-value">{warning.trigger_count || 0}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Event ID</span>
            <span className="metric-value">{warning.event_id}</span>
          </div>
        </div>

        {warning.message && (
          <div className="warning-message">{warning.message}</div>
        )}
      </div>

      {!warning.acknowledged && activeTab === 'realtime' && (
        <div className="card-footer">
          <button
            className="ack-btn"
            onClick={() => acknowledgeEvent(warning.event_id)}
          >
            Acknowledge Event
          </button>
        </div>
      )}

      {warning.acknowledged && (
        <div className="card-footer acknowledged">
          Acknowledged by {warning.acknowledged_by} at {formatTime(warning.acknowledged_at)}
        </div>
      )}
    </div>
  );

  return (
    <div className="warning-system-page">
      {/* Header */}
      <header className="page-header">
        <div className="header-left">
          {onNavigateBack && (
            <button className="back-btn" onClick={onNavigateBack} title="Back to Dashboard">
              ← Back
            </button>
          )}
          <div>
            <h1>Warning System</h1>
            <p className="subtitle">Real-time monitoring and historical analysis</p>
          </div>
        </div>
        <div className="header-right">
          {stats && (
            <div className="stats-summary">
              <div className="stat-box">
                <span className="stat-number">{stats.active_warnings}</span>
                <span className="stat-label">Active</span>
              </div>
              <div className="stat-box">
                <span className="stat-number">{stats.performance?.avg_check_time_ms?.toFixed(2) || 0}ms</span>
                <span className="stat-label">Avg Response</span>
              </div>
              <div className="stat-box">
                <span className="stat-number">{stats.total_checks || 0}</span>
                <span className="stat-label">Total Checks</span>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'realtime' ? 'active' : ''}`}
          onClick={() => setActiveTab('realtime')}
        >
          <span className="tab-icon live-pulse"></span>
          Real-Time
          {activeWarnings.length > 0 && (
            <span className="tab-badge">{activeWarnings.length}</span>
          )}
        </button>
        <button
          className={`tab-btn ${activeTab === 'historical' ? 'active' : ''}`}
          onClick={() => setActiveTab('historical')}
        >
          <span className="tab-icon">📊</span>
          Historical
        </button>
        <button
          className={`tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          <span className="tab-icon">📈</span>
          Statistics
        </button>
      </nav>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠</span>
          {error}
        </div>
      )}

      {/* Content Area */}
      <div className="page-content">
        {/* Real-Time Tab */}
        {activeTab === 'realtime' && (
          <div className="realtime-content">
            {activeWarnings.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">✓</div>
                <h2>No Active Warnings</h2>
                <p>System operating normally. All signals within thresholds.</p>
              </div>
            ) : (
              <div className="warnings-grid">
                {activeWarnings.map(w => renderWarningCard(w))}
              </div>
            )}
          </div>
        )}

        {/* Historical Tab */}
        {activeTab === 'historical' && (
          <div className="historical-content">
            <div className="filters-panel">
              <h3>Filters</h3>
              <div className="filter-grid">
                <div className="filter-group">
                  <label>Severity</label>
                  <select
                    value={filters.severity}
                    onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
                  >
                    <option value="all">All</option>
                    <option value="WARNING">Warning</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Limit</label>
                  <select
                    value={filters.limit}
                    onChange={(e) => setFilters({ ...filters, limit: parseInt(e.target.value) })}
                  >
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                    <option value="500">500</option>
                  </select>
                </div>

                <button className="refresh-btn" onClick={fetchHistoricalWarnings}>
                  ↻ Refresh
                </button>
              </div>
            </div>

            {loading ? (
              <div className="loading-spinner">
                <div className="spinner"></div>
                <p>Loading historical data...</p>
              </div>
            ) : historicalWarnings.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📋</div>
                <h2>No Historical Data</h2>
                <p>Try adjusting your filters or check back later.</p>
              </div>
            ) : (
              <div className="warnings-grid">
                {historicalWarnings.map(w => renderWarningCard(w, true))}
              </div>
            )}
          </div>
        )}

        {/* Statistics Tab */}
        {activeTab === 'stats' && stats && (
          <div className="stats-content">
            <div className="stats-grid">
              <div className="stat-card">
                <h3>Active Warnings</h3>
                <div className="stat-big-number">{stats.active_warnings}</div>
                <div className="stat-detail">Currently triggering</div>
              </div>

              <div className="stat-card">
                <h3>Performance</h3>
                <div className="stat-big-number">{stats.performance?.avg_check_time_ms?.toFixed(3)}ms</div>
                <div className="stat-detail">Average check time</div>
                <div className="stat-detail">Max: {stats.performance?.max_check_time_ms?.toFixed(3)}ms</div>
              </div>

              <div className="stat-card">
                <h3>Total Checks</h3>
                <div className="stat-big-number">{stats.total_checks}</div>
                <div className="stat-detail">{stats.performance?.checks_per_second?.toFixed(2)} checks/sec</div>
              </div>

              <div className="stat-card">
                <h3>By Severity</h3>
                <div className="severity-breakdown">
                  <div className="severity-item warning">
                    <span>Warning:</span>
                    <span>{stats.by_severity?.WARNING || 0}</span>
                  </div>
                  <div className="severity-item critical">
                    <span>Critical:</span>
                    <span>{stats.by_severity?.CRITICAL || 0}</span>
                  </div>
                </div>
              </div>

              <div className="stat-card wide">
                <h3>By Signal</h3>
                <div className="signal-breakdown">
                  {Object.entries(stats.by_signal || {}).map(([signal, count]) => (
                    <div key={signal} className="signal-bar">
                      <span className="signal-name">{signal}</span>
                      <div className="bar-container">
                        <div
                          className="bar-fill"
                          style={{ width: `${(count / Math.max(...Object.values(stats.by_signal || {1: 1}))) * 100}%` }}
                        ></div>
                      </div>
                      <span className="signal-count">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="stat-card">
                <h3>System Status</h3>
                <div className="status-list">
                  <div className="status-item">
                    <span>Real-time Layer:</span>
                    <span className="status-active">{stats.realtime_layer_status}</span>
                  </div>
                  <div className="status-item">
                    <span>Storage Layer:</span>
                    <span className="status-active">{stats.storage_layer_status}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
