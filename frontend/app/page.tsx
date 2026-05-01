'use client';

import { useState } from 'react';
import { postManualData } from '../lib/api';

export default function Home() {
  const [rowsText, setRowsText] = useState('[{"Date":"2024-01-01","Open":100,"High":101,"Low":99,"Close":100.5,"Volume":1000}]');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  const submit = async () => {
    setError('');
    try {
      const rows = JSON.parse(rowsText);
      const res = await postManualData(rows);
      setResult(res);
    } catch (e: any) {
      setError(e.message || 'Request failed');
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <h1 className="text-2xl font-bold mb-4">EQIP Data Input</h1>
      <textarea className="w-full h-40 text-black p-2 rounded" value={rowsText} onChange={(e) => setRowsText(e.target.value)} />
      <button className="mt-4 px-4 py-2 bg-blue-600 rounded" onClick={submit}>Validate Manual Data</button>
      {error && <p className="text-red-400 mt-3">{error}</p>}
      {result && <pre className="mt-4 bg-slate-900 p-4 rounded overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
    </main>
  );
}
