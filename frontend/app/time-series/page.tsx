'use client';
import { useState } from 'react';
import { timeSeriesContext } from '../../lib/api';

export default function TimeSeriesPage() {
  const sample = JSON.stringify(Array.from({length: 120}, (_, i) => ({Date: `2024-05-${String((i%28)+1).padStart(2,'0')}`, Open: 100+i, High: 101+i, Low: 99+i, Close: 100+i + (i%2===0?0.5:-0.5), Volume: 1000})));
  const [rows, setRows] = useState(sample);
  const [result, setResult] = useState<any>(null);
  return <main className="p-8 bg-slate-950 text-white min-h-screen"><h1 className="text-2xl mb-2">Time Series Context</h1><textarea className="w-full h-40 text-black" value={rows} onChange={e=>setRows(e.target.value)} /><button className="bg-blue-600 px-3 my-2" onClick={async()=>setResult(await timeSeriesContext({rows: JSON.parse(rows)}))}>Run Context</button>{result && <pre>{JSON.stringify(result,null,2)}</pre>}</main>;
}
