import React from "react";

export default function SignalSelector({ signals, selected, onChange }) {
  return (
    <div className="selector">
      <h3>Available Signals</h3>
      {signals.map((sig) => (
        <div key={sig.id}>
          <label>
            <input
              type="checkbox"
              checked={selected.includes(sig.id)}
              onChange={(e) => onChange(sig.id, e.target.checked)}
            />
            {sig.id} ({sig.type})
          </label>
        </div>
      ))}
    </div>
  );
}
