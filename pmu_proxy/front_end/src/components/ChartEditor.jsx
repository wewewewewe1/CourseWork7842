import React, { useEffect, useState } from "react";
import { getSignals } from "../api";

export default function ChartEditor({ initial, onSave, onCancel }) {
  const [allSignals, setAllSignals] = useState([]);
  const [name, setName] = useState(initial?.name || "New Chart");
  const [series, setSeries] = useState(initial?.series || []);
  const [refresh, setRefresh] = useState(initial?.refresh || 2000);

  useEffect(() => { getSignals().then(setAllSignals); }, []);

  function toggleSignal(sigId) {
    const exists = series.find(s => s.id === sigId);
    if (exists) setSeries(series.filter(s => s.id !== sigId));
    else setSeries([...series, { id: sigId, color: randomColor() }]);
  }

  function setColor(sigId, color) {
    setSeries(series.map(s => s.id === sigId ? { ...s, color } : s));
  }

  function randomColor() {
    return "#" + Math.floor(Math.random()*0xffffff).toString(16).padStart(6, "0");
  }

  return (
    <div style={{padding:12, minWidth:420}}>
      <h3>Chart Editor</h3>
      <div>
        <label>Chart name: </label>
        <input value={name} onChange={e=>setName(e.target.value)} style={{width:260}} />
      </div>
      <div style={{marginTop:10}}>
        <strong>Signals:</strong>
        <div style={{maxHeight:200, overflow:"auto", border:"1px solid #eee", padding:6}}>
          {allSignals.map(sig => {
            const checked = !!series.find(s => s.id === sig.id);
            const color = series.find(s => s.id === sig.id)?.color || "#777";
            return (
              <div key={sig.id} style={{display:"flex",alignItems:"center",marginBottom:4}}>
                <input type="checkbox" checked={checked} onChange={()=>toggleSignal(sig.id)} />
                <span style={{marginLeft:8,width:150}}>{sig.id} ({sig.type})</span>
                {checked && <input type="color" value={color} onChange={e=>setColor(sig.id,e.target.value)} />}
              </div>
            );
          })}
        </div>
      </div>
      <div style={{marginTop:10}}>
        <label>Refresh(ms): </label>
        <input type="number" min={500} value={refresh} onChange={e=>setRefresh(Number(e.target.value))}/>
      </div>
      <div style={{marginTop:10}}>
        <button onClick={()=>onSave({ name, series, refresh })}>Save</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
