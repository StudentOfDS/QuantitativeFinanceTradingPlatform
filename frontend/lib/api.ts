const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function postManualData(rows: Record<string, unknown>[]) {
  const resp = await fetch(`${API_BASE}/api/data/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rows }),
  });
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(err);
  }
  return resp.json();
}

export async function runVectorizedBacktest(payload: Record<string, unknown>) {
  const resp = await fetch(`${API_BASE}/api/backtest/vectorized`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function runFullReport(payload: Record<string, unknown>) {
  const resp = await fetch(`${API_BASE}/api/report/full`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function fetchReportHistory() {
  const resp = await fetch(`${API_BASE}/api/history/reports`);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function validateML(payload: Record<string, unknown>) {
  const resp = await fetch(`${API_BASE}/api/ml/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}
