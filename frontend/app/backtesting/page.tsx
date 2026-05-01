'use client';

import { useState } from 'react';
import { runVectorizedBacktest } from '../../lib/api';

export default function BacktestingPage() {
  const [rows, setRows] = useState('[{"Date":"2024-01-01","Open":100,"High":101,"Low":99,"Close":100,"Volume":1000},{"Date":"2024-01-02","Open":101,"High":102,"Low":100,"Close":101,"Volume":1000},{"Date":"2024-01-03","Open":102,"High":103,"Low":101,"Close":102,"Volume":1000}]');
  const [strategy, setStrategy] = useState('buy_and_hold');
  const [fast, setFast] = useState(5);
  const [slow, setSlow] = useState(20);
  const [cost, setCost] = useState(0);
  const [slippage, setSlippage] = useState(0);
  const [out, setOut] = useState<any>(null);

  const run = async () => {
    const payload = {
      rows: JSON.parse(rows),
      strategy,
      strategy_params: { fast_window: fast, slow_window: slow },
      initial_capital: 10000,
      transaction_cost_bps: cost,
      slippage_bps: slippage,
    };
    setOut(await runVectorizedBacktest(payload));
  };

  return <main className="p-8 text-white bg-slate-950 min-h-screen">
    <h1 className="text-2xl mb-4">Backtesting</h1>
    <textarea className="w-full h-40 text-black" value={rows} onChange={e=>setRows(e.target.value)} />
    <div className="flex gap-2 my-2">
      <select className="text-black" value={strategy} onChange={e=>setStrategy(e.target.value)}><option>buy_and_hold</option><option>sma_crossover</option><option>momentum</option><option>mean_reversion</option></select>
      <input className="text-black" type="number" value={fast} onChange={e=>setFast(Number(e.target.value))} />
      <input className="text-black" type="number" value={slow} onChange={e=>setSlow(Number(e.target.value))} />
      <input className="text-black" type="number" value={cost} onChange={e=>setCost(Number(e.target.value))} />
      <input className="text-black" type="number" value={slippage} onChange={e=>setSlippage(Number(e.target.value))} />
      <button className="bg-blue-600 px-3" onClick={run}>Run Backtest</button>
    </div>
    {out && <pre>{JSON.stringify(out, null, 2)}</pre>}
  </main>;
}
