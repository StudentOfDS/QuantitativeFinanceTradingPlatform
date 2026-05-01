from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from backend.backtest import run_vectorized_backtest
from backend.data import DataEngine, InputAdapter
from backend.quant import cvar_expected_shortfall, historical_var, max_drawdown, parametric_var
from backend.intelligence import MLEngine, rl_backtest
from backend.time_series import time_series_context


def build_research_report(rows: list[dict], strategy: str, strategy_params: dict, initial_capital: float, transaction_cost_bps: float, slippage_bps: float, include_ml: bool = False, include_rl: bool = False, include_time_series: bool = False) -> dict:
    df = InputAdapter.from_manual_rows(rows)
    validated = DataEngine.validate(df)
    if not validated.report['valid']:
        raise ValueError('Input data failed validation')
    clean = validated.data.copy()
    close = clean['Close'].astype(float)
    returns = close.pct_change().dropna()
    if returns.empty:
        raise ValueError('Insufficient return history for report')

    backtest = run_vectorized_backtest(clean, strategy, strategy_params, initial_capital, transaction_cost_bps, slippage_bps)

    mean_r = float(returns.mean())
    vol_r = float(returns.std(ddof=0))
    risk_summary = {
        'historical_var_95': historical_var(returns.tolist(), 0.95),
        'parametric_var_95': parametric_var(mean_r, vol_r, 0.95),
        'cvar_95': cvar_expected_shortfall(returns.tolist(), 0.95),
        'max_drawdown': max_drawdown(backtest['equity_curve']),
    }

    ml_summary = None
    if include_ml:
        ml_summary = MLEngine.validate(clean)

    rl_summary = None
    if include_rl:
        try:
            rl_summary = rl_backtest(clean, transaction_cost_bps=max(transaction_cost_bps, 0.0))
        except ValueError as exc:
            rl_summary = {'warnings': [str(exc)]}

    ts_summary = None
    if include_time_series:
        ts_summary = time_series_context(clean)

    report = {
        'metadata': {'strategy': strategy, 'row_count': len(clean)},
        'data_validation': validated.report,
        'price_summary': {
            'start_close': float(close.iloc[0]),
            'end_close': float(close.iloc[-1]),
            'return_mean': mean_r,
            'return_std': vol_r,
        },
        'risk_summary': risk_summary,
        'backtest_summary': backtest,
        'warnings': validated.report.get('warnings', []),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
    if include_ml:
        report['ml_summary'] = ml_summary
    if include_rl:
        report['rl_summary'] = rl_summary
    if include_time_series:
        report['time_series_summary'] = ts_summary
    return report
