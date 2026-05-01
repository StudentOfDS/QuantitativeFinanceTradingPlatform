'use client';
import { useState } from 'react';
import { validateML } from '../../lib/api';

export default function MLPage() {
  const sample = JSON.stringify(Array.from({length: 120}, (_, i) => ({Date: `2024-03-${String((i%28)+1).padStart(2,'0')}`, Open: 100+i*0.2, High: 101+i*0.2, Low: 99+i*0.2, Close: 100+i*0.2 + (i%2===0?0.5:-0.5), Volume: 1000+i}));
  const [rows, setRows] = useState(sample);
  const [result, setResult] = useState<any>(null);
  const run = async () => setResult(await validateML({ rows: JSON.parse(rows) }));
  return <main className="p-8 bg-slate-950 text-white min-h-screen"><h1 className="text-2xl mb-2">ML Validation</h1><textarea className="w-full h-40 text-black" value={rows} onChange={e=>setRows(e.target.value)} /><p className="text-sm text-slate-300">ML validation needs enough history (60+ feature rows). A 120-row sample is prefilled.</p><button className="bg-blue-600 px-3 my-2" onClick={run}>Run ML Validate</button>{result && <pre>{JSON.stringify(result, null, 2)}</pre>}</main>;
}
