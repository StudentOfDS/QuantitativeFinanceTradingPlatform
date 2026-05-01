from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    run([sys.executable, "-m", "compileall", "backend"])
    run([sys.executable, "-m", "pytest", "backend/tests", "-q"])
    run([sys.executable, "-c", "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); assert c.get('/api/health').status_code==200"])
    run([
        sys.executable,
        "-c",
        "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); payload={'rows':[{'Date':'2024-01-01','Open':1,'High':2,'Low':1,'Close':1.5,'Volume':10}]}; r=c.post('/api/data/manual',json=payload); assert r.status_code==200 and 'valid' in r.json()",
    ])
    run([sys.executable, "-c", "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); rows=[{'Date':'2024-01-01','Open':100,'High':101,'Low':99,'Close':100,'Volume':1000},{'Date':'2024-01-02','Open':101,'High':102,'Low':100,'Close':101,'Volume':1000},{'Date':'2024-01-03','Open':102,'High':103,'Low':101,'Close':102,'Volume':1000},{'Date':'2024-01-04','Open':103,'High':104,'Low':102,'Close':103,'Volume':1000}]; r=c.post('/api/report/full',json={'rows':rows,'strategy':'buy_and_hold'}); assert r.status_code==200 and 'report_id' in r.json()"] )
    run([sys.executable, "-c", "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); rows=[{'Date':f'2024-03-{(i%28)+1:02d}','Open':100+i*0.2,'High':101+i*0.2,'Low':99+i*0.2,'Close':100+i*0.2+((-1)**i)*0.5,'Volume':1000+i} for i in range(180)]; r=c.post('/api/ml/validate',json={'rows':rows}); assert r.status_code==200 and 0<=r.json()['latest_probability']<=1"] )
    run([sys.executable, "-c", "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); rows=[{'Date':f'2024-03-{(i%28)+1:02d}','Open':100+i*0.2,'High':101+i*0.2,'Low':99+i*0.2,'Close':100+i*0.2+((-1)**i)*0.5,'Volume':1000+i} for i in range(180)]; r=c.post('/api/rl/action',json={'rows':rows}); assert r.status_code==200 and r.json()['allocation'] in [0.0,0.25,0.5,0.75,1.0]"])
    run([sys.executable, "-c", "from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); rows=[{'Date':f'2024-05-{(i%28)+1:02d}','Open':100+i,'High':101+i,'Low':99+i,'Close':100+i+((-1)**i)*0.5,'Volume':1000} for i in range(120)]; r=c.post('/api/time-series/context',json={'rows':rows}); assert r.status_code==200 and 'volatility_regime' in r.json()"] )
    print("Validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
