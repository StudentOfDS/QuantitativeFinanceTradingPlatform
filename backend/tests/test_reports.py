from fastapi.testclient import TestClient

from backend.main import app
from backend.reports import build_research_report

client = TestClient(app)


def rows():
    return [{"Date": f"2024-02-{i+1:02d}", "Open": 100+i, "High": 101+i, "Low": 99+i, "Close": 100+i, "Volume": 1000} for i in range(40)]


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
