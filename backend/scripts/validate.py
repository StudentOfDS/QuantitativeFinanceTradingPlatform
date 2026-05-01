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
    print("Validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
