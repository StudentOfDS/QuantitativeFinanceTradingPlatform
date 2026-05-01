import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.time_series import (
    autocorrelation_summary,
    current_drawdown,
    ewma_volatility,
    garch_forecast,
    historical_annualized_volatility,
    log_returns,
    rolling_drawdown,
    simple_returns,
    time_series_context,
    volatility_regime_classification,
    adf_stationarity,
)

client = TestClient(app)


def make_df(n=120):
    return pd.DataFrame([{"Date": f"2024-05-{(i%28)+1:02d}", "Close": 100 + i*0.3 + ((-1)**i)*0.4} for i in range(n)])


def test_returns_correctness():
    s = pd.Series([100, 110, 121])
    r = simple_returns(s)
    lr = log_returns(s)
    assert r.iloc[0] == pytest.approx(0.1)
    assert lr.iloc[0] == pytest.approx(math.log(1.1))


def test_vol_drawdown_regime_and_acf_shapes():
    df = make_df()
    r = simple_returns(df['Close'])
    assert math.isfinite(historical_annualized_volatility(r))
    assert math.isfinite(float(ewma_volatility(r).dropna().iloc[-1]))
    rd = rolling_drawdown(df['Close'])
    assert rd.min() <= 0
    assert current_drawdown(df['Close']) <= 0
    assert volatility_regime_classification(0.1, 0.1) == 'normal'
    acf = autocorrelation_summary(r)
    assert len(acf) == 5


def test_optional_fallback_behaviors():
    df = make_df()
    r = simple_returns(df['Close'])
    adf, _ = adf_stationarity(r)
    assert 'available' in adf
    garch, _ = garch_forecast(r)
    assert 'available' in garch


def test_time_series_context_and_endpoint():
    df = make_df()
    ctx = time_series_context(df)
    for k in ['latest_return','latest_log_return','historical_volatility','ewma_volatility','rolling_volatility_latest','max_drawdown','current_drawdown','volatility_regime','autocorrelation_summary','adf_result','garch_forecast','warnings','generated_at']:
        assert k in ctx
    rows = [{"Date": f"2024-05-{(i%28)+1:02d}", "Open": 100+i, "High": 101+i, "Low": 99+i, "Close": 100+i + ((-1)**i)*0.5, "Volume": 1000} for i in range(120)]
    r = client.post('/api/time-series/context', json={'rows': rows})
    assert r.status_code == 200
