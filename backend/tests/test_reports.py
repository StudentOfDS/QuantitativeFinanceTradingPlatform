from fastapi.testclient import TestClient

from backend.main import app
from backend.reports import build_research_report

client = TestClient(app)


def rows():
    import pandas as pd
    dates = pd.date_range("2024-01-01", periods=180, freq="D")
    return [{"Date": d.strftime("%Y-%m-%d"), "Open": 100+i, "High": 101+i, "Low": 99+i, "Close": 100+i, "Volume": 1000} for i, d in enumerate(dates)]


def test_report_sections_present():
    report = build_research_report(rows(), 'buy_and_hold', {}, 10000, 0, 0)
    for key in ['metadata', 'data_validation', 'price_summary', 'risk_summary', 'backtest_summary', 'warnings', 'generated_at']:
        assert key in report


def test_report_bad_data_clean_error():
    bad = [{"Date":"2024-01-01","Open":1,"High":0.5,"Low":1,"Close":1,"Volume":10}]
    r = client.post('/api/report/full', json={'rows': bad, 'strategy': 'buy_and_hold'})
    assert r.status_code == 400


def test_report_persistence_and_history_endpoint():
    r = client.post('/api/report/full', json={'rows': rows(), 'strategy': 'momentum', 'strategy_params': {'lookback': 5}})
    assert r.status_code == 200
    assert r.json()['report_id'] > 0
    h = client.get('/api/history/reports')
    assert h.status_code == 200
    assert len(h.json()['items']) >= 1


def test_report_includes_ml_summary_when_requested():
    r = client.post('/api/report/full', json={'rows': rows(), 'strategy': 'buy_and_hold', 'include_ml': True})
    assert r.status_code == 200
    assert 'ml_summary' in r.json()['report']


def test_report_includes_rl_summary_when_requested():
    r = client.post('/api/report/full', json={'rows': rows(), 'strategy': 'buy_and_hold', 'include_rl': True})
    assert r.status_code == 200
    assert 'rl_summary' in r.json()['report']


def test_report_includes_time_series_summary_when_requested():
    r = client.post('/api/report/full', json={'rows': rows(), 'strategy': 'buy_and_hold', 'include_time_series': True})
    assert r.status_code == 200
    assert 'time_series_summary' in r.json()['report']
