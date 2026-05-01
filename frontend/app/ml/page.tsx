'use client';
import { useState } from 'react';
import { validateML } from '../../lib/api';

export default function MLPage() {
  const [rows, setRows] = useState('[{"Date":"2024-03-01","Open":100,"High":101,"Low":99,"Close":100.5,"Volume":1000}]');
  const [result, setResult] = useState<any>(null);
  const run = async () => setResult(await validateML({ rows: JSON.parse(rows) }));
  return <main className="p-8 bg-slate-950 text-white min-h-screen"><h1 className="text-2xl mb-2">ML Validation</h1><textarea className="w-full h-40 text-black" value={rows} onChange={e=>setRows(e.target.value)} /><button className="bg-blue-600 px-3 my-2" onClick={run}>Run ML Validate</button>{result && <pre>{JSON.stringify(result, null, 2)}</pre>}</main>;
}
