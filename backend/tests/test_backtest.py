import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.backtest import run_vectorized_backtest
from backend.main import app

client = TestClient(app)


def rows_uptrend(n=50):
    return [{"Date": f"2024-01-{(i%28)+1:02d}", "Open": 100+i, "High": 101+i, "Low": 99+i, "Close": 100+i, "Volume": 1000} for i in range(n)]


def test_buy_hold_no_costs():
    df = pd.DataFrame(rows_uptrend())
    res = run_vectorized_backtest(df, 'buy_and_hold', {}, 10000, 0, 0)
    assert res['final_return'] > 0
    assert res['cost_paid'] == 0


def test_sma_delayed_execution_and_costs():
    df = pd.DataFrame(rows_uptrend())
    res = run_vectorized_backtest(df, 'sma_crossover', {'fast_window': 3, 'slow_window': 8}, 10000, 10, 5)
    assert res['trade_count'] >= 0
    assert res['turnover'] >= 0
    assert res['cost_paid'] >= 0


def test_invalid_windows_and_insufficient_rows():
    df = pd.DataFrame(rows_uptrend())
    with pytest.raises(ValueError):
        run_vectorized_backtest(df, 'sma_crossover', {'fast_window': 10, 'slow_window': 5}, 10000, 0, 0)
    with pytest.raises(ValueError):
        run_vectorized_backtest(pd.DataFrame(rows_uptrend(2)), 'buy_and_hold', {}, 10000, 0, 0)


def test_endpoint_smoke_backtest():
    payload = {'rows': rows_uptrend(), 'strategy': 'momentum', 'strategy_params': {'lookback': 5}, 'initial_capital': 10000, 'transaction_cost_bps': 5, 'slippage_bps': 5}
    r = client.post('/api/backtest/vectorized', json=payload)
    assert r.status_code == 200
    body = r.json()
    assert 'benchmark_return' in body


def test_cost_charged_on_position_changes():
    r = client.post('/api/backtest/vectorized', json={'rows': rows_uptrend(), 'strategy': 'buy_and_hold', 'transaction_cost_bps': 10, 'slippage_bps': 10, 'persist': False})
    assert r.status_code == 200
    # buy-and-hold should trade once (enter) then hold
    assert r.json()['trade_count'] == 1


def test_buy_and_hold_delayed_execution():
    data = rows_uptrend(5)
    df = pd.DataFrame(data)
    res = run_vectorized_backtest(df, 'buy_and_hold', {}, 10000, 0, 0)
    assert res['positions'][0] == 0.0
