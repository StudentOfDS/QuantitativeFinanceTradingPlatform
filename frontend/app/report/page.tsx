'use client';

import { useState } from 'react';
import { runFullReport } from '../../lib/api';

export default function ReportPage() {
  const [rows, setRows] = useState('[{"Date":"2024-01-01","Open":100,"High":101,"Low":99,"Close":100,"Volume":1000},{"Date":"2024-01-02","Open":101,"High":102,"Low":100,"Close":101,"Volume":1000},{"Date":"2024-01-03","Open":102,"High":103,"Low":101,"Close":102,"Volume":1000},{"Date":"2024-01-04","Open":103,"High":104,"Low":102,"Close":103,"Volume":1000}]');
  const [strategy, setStrategy] = useState('buy_and_hold');
  const [result, setResult] = useState<any>(null);

  const submit = async () => {
    const res = await runFullReport({ rows: JSON.parse(rows), strategy, initial_capital: 10000, transaction_cost_bps: 5, slippage_bps: 5 });
    setResult(res);
  };

  return <main className="p-8 text-white bg-slate-950 min-h-screen">
    <h1 className="text-2xl mb-3">Research Report</h1>
    <textarea className="w-full h-40 text-black" value={rows} onChange={e=>setRows(e.target.value)} />
    <div className="my-2">
      <select className="text-black" value={strategy} onChange={e=>setStrategy(e.target.value)}><option>buy_and_hold</option><option>sma_crossover</option><option>momentum</option><option>mean_reversion</option></select>
      <button className="bg-blue-600 px-3 ml-2" onClick={submit}>Run Full Report</button>
    </div>
    {result && <div>
      <div className="grid grid-cols-2 gap-2 my-3">
        <div>Valid: {String(result.report.data_validation.valid)}</div>
        <div>Final Return: {result.report.backtest_summary.final_return}</div>
        <div>Max Drawdown: {result.report.backtest_summary.max_drawdown}</div>
        <div>Sharpe: {result.report.backtest_summary.sharpe}</div>
        <div>VaR: {result.report.risk_summary.historical_var_95}</div>
        <div>CVaR: {result.report.risk_summary.cvar_95}</div>
      </div>
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </div>}
  </main>;
}
