from __future__ import annotations

import math
from typing import Any

import pandas as pd

TRADING_DAYS = 252


def _validate_df(df: pd.DataFrame) -> pd.DataFrame:
    if "Close" not in df.columns:
        raise ValueError("Close column is required")
    out = df.copy()
    out["Close"] = pd.to_numeric(out["Close"], errors="coerce")
    out = out.dropna(subset=["Close"])
    if len(out) < 3:
        raise ValueError("Insufficient rows for backtest")
    if (out["Close"] <= 0).any():
        raise ValueError("Invalid non-positive Close price")
    return out.reset_index(drop=True)


def _signals(df: pd.DataFrame, strategy: str, params: dict[str, Any]) -> pd.Series:
    close = df["Close"]
    if strategy == "buy_and_hold":
        return pd.Series(1.0, index=df.index)
    if strategy == "sma_crossover":
        fast = int(params.get("fast_window", 5))
        slow = int(params.get("slow_window", 20))
        if fast <= 0 or slow <= 0 or fast >= slow:
            raise ValueError("Invalid windows: require fast_window < slow_window and both > 0")
        sma_fast = close.rolling(fast).mean()
        sma_slow = close.rolling(slow).mean()
        return (sma_fast > sma_slow).astype(float).fillna(0.0)
    if strategy == "momentum":
        lookback = int(params.get("lookback", 10))
        if lookback <= 0:
            raise ValueError("lookback must be positive")
        mom = close.pct_change(lookback)
        return (mom > 0).astype(float).fillna(0.0)
    if strategy == "mean_reversion":
        window = int(params.get("window", 20))
        z_threshold = float(params.get("z_threshold", 1.0))
        if window <= 1 or z_threshold <= 0:
            raise ValueError("window must be >1 and z_threshold >0")
        ma = close.rolling(window).mean()
        std = close.rolling(window).std()
        z = (close - ma) / std.replace(0, pd.NA)
        long_sig = (z < -z_threshold).astype(float)
        flat_sig = (z > 0).astype(float)
        sig = long_sig.copy()
        sig[flat_sig == 1.0] = 0.0
        return sig.fillna(0.0)
    raise ValueError("Invalid strategy name")


def run_vectorized_backtest(df: pd.DataFrame, strategy: str, params: dict[str, Any], initial_capital: float, transaction_cost_bps: float, slippage_bps: float) -> dict[str, Any]:
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if transaction_cost_bps < 0 or slippage_bps < 0:
        raise ValueError("cost bps must be non-negative")
    data = _validate_df(df)
    signals = _signals(data, strategy, params)

    returns = data["Close"].pct_change().fillna(0.0)
    positions = signals.shift(1).fillna(0.0)
    turnover = positions.diff().abs().fillna(abs(positions.iloc[0]))
    cost_rate = (transaction_cost_bps + slippage_bps) / 10000.0
    costs = turnover * cost_rate

    strategy_returns = positions * returns - costs
    equity = (1 + strategy_returns).cumprod() * initial_capital
    bench_equity = (1 + returns).cumprod() * initial_capital
    drawdown = equity / equity.cummax() - 1

    total_return = float(equity.iloc[-1] / initial_capital - 1)
    periods = len(strategy_returns)
    years = periods / TRADING_DAYS
    cagr = float((equity.iloc[-1] / initial_capital) ** (1 / years) - 1) if years > 0 else 0.0
    ann_vol = float(strategy_returns.std(ddof=0) * math.sqrt(TRADING_DAYS))
    ann_ret = float(strategy_returns.mean() * TRADING_DAYS)
    sharpe = float(ann_ret / ann_vol) if ann_vol > 0 else 0.0
    downside = strategy_returns[strategy_returns < 0]
    downside_vol = float(downside.std(ddof=0) * math.sqrt(TRADING_DAYS)) if len(downside) else 0.0
    sortino = float(ann_ret / downside_vol) if downside_vol > 0 else 0.0
    mdd = float(drawdown.min())
    calmar = float(cagr / abs(mdd)) if mdd < 0 else 0.0
    nonzero = strategy_returns[strategy_returns != 0]
    wins = nonzero[nonzero > 0]
    losses = nonzero[nonzero < 0]

    return {
        "equity_curve": [float(x) for x in equity],
        "drawdown_curve": [float(x) for x in drawdown],
        "positions": [float(x) for x in positions],
        "trade_count": int((turnover > 0).sum()),
        "cost_paid": float(costs.sum() * initial_capital),
        "final_return": total_return,
        "cagr": cagr,
        "annualized_volatility": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": mdd,
        "turnover": float(turnover.sum()),
        "win_rate": float(len(wins) / len(nonzero)) if len(nonzero) else 0.0,
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "exposure": float(positions.mean()),
        "benchmark_return": float(bench_equity.iloc[-1] / initial_capital - 1),
    }
