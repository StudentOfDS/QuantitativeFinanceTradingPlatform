import io
import pickle

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def sample_rows():
    return [
        {"Date": "2024-01-01", "Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 1000},
        {"Date": "2024-01-02", "Open": 101, "High": 103, "Low": 100, "Close": 102, "Volume": 1100},
    ]


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_manual_input_and_adj_close_fallback():
    response = client.post("/api/data/manual", json={"rows": sample_rows()})
    assert response.status_code == 200
    body = response.json()
    assert "Adj Close" in body["preview"][0]
    assert "Adj Close missing: fallback copied from Close." in body["warnings"]


def test_duplicate_timestamps_and_invalid_rows():
    rows = sample_rows() + [{"Date": "2024-01-02", "Open": -1, "High": 90, "Low": 95, "Close": 0, "Volume": 100}]
    response = client.post("/api/data/manual", json={"rows": rows})
    body = response.json()
    assert body["duplicate_timestamps"] == 1
    assert body["invalid_high_low_rows"] >= 1
    assert body["non_positive_price_rows"] >= 1
    assert body["valid"] is False


def test_csv_upload():
    df = pd.DataFrame(sample_rows())
    csv_bytes = df.to_csv(index=False).encode()
    response = client.post("/api/data/upload", files={"file": ("prices.csv", csv_bytes, "text/csv")})
    assert response.status_code == 200
    assert response.json()["raw_rows"] == 2


def test_excel_upload():
    df = pd.DataFrame(sample_rows())
    b = io.BytesIO()
    df.to_excel(b, index=False)
    response = client.post(
        "/api/data/upload",
        files={"file": ("prices.xlsx", b.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200


def test_parquet_upload_if_available():
    df = pd.DataFrame(sample_rows())
    b = io.BytesIO()
    try:
        df.to_parquet(b, index=False)
    except Exception:
        return
    response = client.post("/api/data/upload", files={"file": ("prices.parquet", b.getvalue(), "application/octet-stream")})
    assert response.status_code == 200


def test_pickle_trusted_warning_behavior():
    df = pd.DataFrame(sample_rows())
    pbytes = pickle.dumps(df)
    blocked = client.post("/api/data/upload", files={"file": ("prices.pkl", pbytes, "application/octet-stream")})
    assert blocked.status_code == 400
    assert "Pickle upload blocked" in blocked.json()["detail"]
