import Link from 'next/link';

export default function Home() {
  return <main className="p-8 bg-slate-950 text-white min-h-screen">
    <h1 className="text-2xl font-bold mb-4">EQIP</h1>
    <ul className="space-y-2">
      <li><Link className="text-blue-300" href="/">Data Input</Link></li>
      <li><Link className="text-blue-300" href="/backtesting">Backtesting</Link></li>
      <li><Link className="text-blue-300" href="/report">Research Report</Link></li>
          <li><Link className="text-blue-300" href="/ml">ML Validation</Link></li>
          <li><Link className="text-blue-300" href="/rl">RL Allocation</Link></li>
    </ul>
  </main>;
}
