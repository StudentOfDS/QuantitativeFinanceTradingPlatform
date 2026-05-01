'use client';
import { useState } from 'react';
import { rlAction, rlBacktest } from '../../lib/api';

export default function RLPage() {
  const sample = JSON.stringify(Array.from({length: 140}, (_, i) => ({Date: `2024-04-${String((i%28)+1).padStart(2,'0')}`, Open: 100+i*0.2, High: 101+i*0.2, Low: 99+i*0.2, Close: 100+i*0.2 + (i%2===0?0.5:-0.5), Volume: 1000+i})));
  const [rows, setRows] = useState(sample);
  const [action, setAction] = useState<any>(null);
  const [backtest, setBacktest] = useState<any>(null);
  return <main className="p-8 bg-slate-950 text-white min-h-screen"><h1 className="text-2xl mb-2">RL Allocation Helper</h1><textarea className="w-full h-40 text-black" value={rows} onChange={e=>setRows(e.target.value)} /><div className="my-2"><button className="bg-blue-600 px-3 mr-2" onClick={async()=>setAction(await rlAction({rows: JSON.parse(rows), current_exposure: 0.5}))}>Get Action</button><button className="bg-green-600 px-3" onClick={async()=>setBacktest(await rlBacktest({rows: JSON.parse(rows), transaction_cost_bps: 5}))}>Run RL Backtest</button></div>{action && <pre>{JSON.stringify(action,null,2)}</pre>}{backtest && <pre>{JSON.stringify(backtest,null,2)}</pre>}</main>;
}
