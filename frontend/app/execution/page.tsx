'use client';
import { useState } from 'react';
import { paperOrder, paperPortfolio } from '../../lib/api';

export default function ExecutionPage(){
 const [report,setReport]=useState<any>(null); const [portfolio,setPortfolio]=useState<any>(null);
 return <main className="p-8 bg-slate-950 text-white min-h-screen"><h1 className="text-2xl">Execution (Paper)</h1><p className="text-red-300">Live trading is disabled by default and dangerous.</p><button className="bg-blue-600 px-3 mr-2" onClick={async()=>setReport(await paperOrder({symbol:'AAPL',side:'BUY',quantity:1,order_type:'market',bid:99,ask:101,last:100}))}>Send Paper Order</button><button className="bg-green-600 px-3" onClick={async()=>setPortfolio(await paperPortfolio())}>Load Portfolio</button>{report&&<pre>{JSON.stringify(report,null,2)}</pre>}{portfolio&&<pre>{JSON.stringify(portfolio,null,2)}</pre>}</main>
}
