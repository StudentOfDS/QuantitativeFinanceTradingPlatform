import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.intelligence import MLEngine, RL_ACTIONS, build_ml_features, rl_action, rl_backtest
from backend.main import app

client = TestClient(app)


def make_rows(n=180):
    return [{"Date": f"2024-03-{(i%28)+1:02d}", "Open": 100+i*0.2, "High": 101+i*0.2, "Low": 99+i*0.2, "Close": 100+i*0.2 + ((-1)**i)*0.5, "Volume": 1000+i} for i in range(n)]


def test_target_shift_and_no_leakage():
    import pandas as pd
    raw = pd.DataFrame(make_rows())
    raw['ret_1'] = raw['Close'].pct_change()
    feat = build_ml_features(raw)
    raw2 = raw.reset_index(drop=True)
    start = len(raw2) - len(feat)
    for i in range(len(feat)-1):
        idx = start + i
        expected = int(raw2.loc[idx+1, 'ret_1'] > 0)
        assert int(feat.loc[i, 'target']) == expected
    future_ret = raw2['ret_1'].shift(-1).iloc[start:start+len(feat)].reset_index(drop=True)
    assert not np.allclose(feat['ret_1'].to_numpy(), future_ret.fillna(0).to_numpy())
    assert not np.array_equal(feat['ret_lag_1'].fillna(0).to_numpy(), feat['target'].to_numpy())


def test_small_dataset_fails_cleanly():
    import pandas as pd
    with pytest.raises(ValueError):
        MLEngine.validate(pd.DataFrame(make_rows(30)))


def test_ml_and_rl_endpoints_smoke():
    rows = make_rows()
    v = client.post('/api/ml/validate', json={'rows': rows})
    assert v.status_code == 200
    body = v.json()
    assert 0 <= body['latest_probability'] <= 1
    p = client.post('/api/ml/predict', json={'rows': rows})
    assert p.status_code == 200
    assert 0 <= p.json()['latest_probability'] <= 1

    ra = client.post('/api/rl/action', json={'rows': rows, 'current_exposure': 0.5})
    assert ra.status_code == 200
    assert ra.json()['allocation'] in RL_ACTIONS
    rb = client.post('/api/rl/backtest', json={'rows': rows, 'transaction_cost_bps': 5})
    assert rb.status_code == 200
    for k in ['final_return','max_drawdown','turnover','cost_paid','benchmark_comparison','reward_diagnostics']:
        assert k in rb.json()


def test_rl_deterministic_state_and_reward_cost_penalty():
    import pandas as pd
    df = pd.DataFrame(make_rows())
    a1 = rl_action(df, current_exposure=0.25, seed=42)
    a2 = rl_action(df, current_exposure=0.25, seed=42)
    assert a1['state'] == a2['state']
    b = rl_backtest(df, transaction_cost_bps=10, seed=42)
    assert b['cost_paid'] >= 0
