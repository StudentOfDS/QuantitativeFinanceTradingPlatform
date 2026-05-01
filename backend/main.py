from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.data import DataEngine, InputAdapter

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ManualDataRequest(BaseModel):
    rows: list[dict] = Field(default_factory=list)


class PreviewRequest(BaseModel):
    source: str
    rows: list[dict] | None = None
    symbol: str | None = None
    period: str | None = None
    interval: str | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.post("/api/data/manual")
def data_manual(request: ManualDataRequest) -> dict:
    df = InputAdapter.from_manual_rows(request.rows)
    result = DataEngine.validate(df)
    return result.report


@app.post("/api/data/upload")
async def data_upload(file: UploadFile = File(...), trusted_pickle: bool = False) -> dict:
    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_mb}MB")
    if trusted_pickle and not settings.allow_trusted_pickle:
        raise HTTPException(status_code=400, detail="Trusted pickle disabled by server configuration.")
    try:
        df, warnings = InputAdapter.from_upload(content, file.filename or "upload", trusted_pickle=trusted_pickle)
        result = DataEngine.validate(df, warnings=warnings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.report


@app.post("/api/data/preview")
def data_preview(request: PreviewRequest) -> dict:
    try:
        if request.source == "manual":
            df = InputAdapter.from_manual_rows(request.rows or [])
            result = DataEngine.validate(df)
            return result.report
        if request.source == "yfinance":
            if not request.symbol:
                raise HTTPException(status_code=400, detail="symbol is required for yfinance source")
            df, warnings = InputAdapter.from_yfinance(
                request.symbol,
                request.period or settings.yfinance_default_period,
                request.interval or settings.yfinance_default_interval,
            )
            result = DataEngine.validate(df, warnings=warnings)
            return result.report
        raise HTTPException(status_code=400, detail="Unsupported source. Use 'manual' or 'yfinance'.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
