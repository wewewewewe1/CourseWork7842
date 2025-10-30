import React, { useState, useRef, useEffect } from 'react';
import './TimelineSlider.css';

/**
 * TimelineSlider - Draggable timeline bar for viewing historical data
 *
 * Features:
 * - Drag to navigate through time
 * - Live/Paused mode toggle
 * - Time range display
 * - Smooth dragging interaction
 *
 * @param {Function} onTimeChange - Callback when time selection changes
 * @param {Date} minTime - Earliest available time
 * @param {Date} maxTime - Latest available time (current time)
 * @param {Date} currentTime - Currently selected time
 * @param {Boolean} isLive - Whether in live mode
 */
export default function TimelineSlider({
  onTimeChange,
  minTime,
  maxTime,
  currentTime,
  isLive = true
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [sliderPosition, setSliderPosition] = useState(100); // 0-100%
  const sliderRef = useRef(null);
  const animationRef = useRef(null);

  // Convert time to percentage position
  const timeToPosition = (time) => {
    if (!minTime || !maxTime) return 100;
    const total = maxTime.getTime() - minTime.getTime();
    const current = time.getTime() - minTime.getTime();
    return (current / total) * 100;
  };

  // Convert percentage to time
  const positionToTime = (position) => {
    if (!minTime || !maxTime) return maxTime;
    const total = maxTime.getTime() - minTime.getTime();
    const offset = (position / 100) * total;
    return new Date(minTime.getTime() + offset);
  };

  // Update position when currentTime changes (but NOT while dragging)
  useEffect(() => {
    if (currentTime && !isDragging && isLive) {
      // Only auto-update position if in live mode and not dragging
      setSliderPosition(timeToPosition(currentTime));
    }
  }, [currentTime, minTime, maxTime, isDragging, isLive]);

  // Handle mouse down - start dragging
  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
    updatePosition(e.clientX);
  };

  // Handle mouse move - dragging
  const handleMouseMove = (e) => {
    if (isDragging) {
      updatePosition(e.clientX);
    }
  };

  // Handle mouse up - stop dragging
  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Update position based on mouse X coordinate
  const updatePosition = (clientX) => {
    if (!sliderRef.current) return;

    const rect = sliderRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));

    setSliderPosition(percentage);

    // Calculate selected time
    const selectedTime = positionToTime(percentage);
    const nowIsLive = percentage >= 99; // Consider 99%+ as "live"

    if (onTimeChange) {
      onTimeChange(selectedTime, nowIsLive);
    }
  };

  // Toggle live mode
  const handleLiveToggle = () => {
    if (isLive) {
      // Pause - stay at current position
      if (onTimeChange) {
        onTimeChange(currentTime || maxTime, false);
      }
    } else {
      // Go live - jump to end
      setSliderPosition(100);
      if (onTimeChange) {
        onTimeChange(maxTime, true);
      }
    }
  };

  // Format time for display
  const formatTime = (time) => {
    if (!time) return '--:--:--';
    return time.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Format time range
  const formatTimeRange = () => {
    if (!minTime || !maxTime) return 'Loading...';

    const diffMs = maxTime.getTime() - minTime.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);

    if (diffHours > 0) {
      return `${diffHours}h ${diffMinutes % 60}m range`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes}m range`;
    } else {
      return `${Math.floor(diffMs / 1000)}s range`;
    }
  };

  // Add/remove event listeners
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);

      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);

  return (
    <div className="timeline-slider-container">
      <div className="timeline-controls">
        <button
          className={`live-toggle-btn ${isLive ? 'live' : 'paused'}`}
          onClick={handleLiveToggle}
          title={isLive ? 'Click to pause' : 'Click to go live'}
        >
          {isLive ? (
            <>
              <span className="live-indicator"></span>
              Live
            </>
          ) : (
            <>
              <span className="pause-icon">II</span>
              Paused
            </>
          )}
        </button>

        <div className="time-info">
          <span className="current-time">{formatTime(currentTime || maxTime)}</span>
          <span className="time-range">{formatTimeRange()}</span>
        </div>
      </div>

      <div
        className="timeline-slider"
        ref={sliderRef}
        onMouseDown={handleMouseDown}
      >
        <div className="timeline-track">
          <div
            className="timeline-progress"
            style={{ width: `${sliderPosition}%` }}
          ></div>
        </div>

        <div
          className="timeline-handle"
          style={{ left: `${sliderPosition}%` }}
        >
          <div className="handle-knob"></div>
          <div className="handle-line"></div>
        </div>
      </div>

      <div className="timeline-labels">
        <span className="label-start">{formatTime(minTime)}</span>
        <span className="label-end">{formatTime(maxTime)}</span>
      </div>
    </div>
  );
}
