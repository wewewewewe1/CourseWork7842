import React, { useEffect, useState } from "react";
import { getSignals } from "./api";
import SignalSelector from "./components/SignalSelector";
import ChartPanel from "./components/ChartPanel";

export default function App() {
  const [signals, setSignals] = useState([]);
  const [selected, setSelected] = useState([]);

  useEffect(() => {
    getSignals().then(setSignals);
  }, []);

  function handleSelect(signalId, checked) {
    if (checked) setSelected([...selected, signalId]);
    else setSelected(selected.filter((id) => id !== signalId));
  }

  return (
    <div className="app">
      <h1>PMU Visualisation Dashboard v7.13</h1>
      <SignalSelector
        signals={signals}
        selected={selected}
        onChange={handleSelect}
      />

      <div className="charts">
        {selected.map((id) => (
          <ChartPanel key={id} signalId={id} />
        ))}
      </div>
    </div>
  );
}
