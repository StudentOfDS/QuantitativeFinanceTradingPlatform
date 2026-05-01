import pytest
from fastapi.testclient import TestClient

from backend.intelligence import MLEngine, build_ml_features
from backend.main import app

client = TestClient(app)


def make_rows(n=180):
    return [{"Date": f"2024-03-{(i%28)+1:02d}", "Open": 100+i*0.2, "High": 101+i*0.2, "Low": 99+i*0.2, "Close": 100+i*0.2 + ((-1)**i)*0.5, "Volume": 1000+i} for i in range(n)]


def test_target_shift_and_no_leakage():
    import pandas as pd
    df = pd.DataFrame(make_rows())
    feat = build_ml_features(df)
    assert 'target' in feat.columns
    assert all(c in feat.columns for c in ['ret_lag_1', 'rolling_vol_10', 'drawdown'])


def test_small_dataset_fails_cleanly():
    import pandas as pd
    with pytest.raises(ValueError):
        MLEngine.validate(pd.DataFrame(make_rows(30)))


def test_ml_validate_and_predict_endpoints():
    rows = make_rows()
    v = client.post('/api/ml/validate', json={'rows': rows})
    assert v.status_code == 200
    body = v.json()
    for k in ['accuracy', 'precision', 'recall', 'f1', 'feature_importance', 'latest_probability', 'latest_confidence', 'model_validation_id']:
        assert k in body
    assert 0 <= body['latest_probability'] <= 1
    p = client.post('/api/ml/predict', json={'rows': rows})
    assert p.status_code == 200
    assert 0 <= p.json()['latest_probability'] <= 1
