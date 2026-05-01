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


from backend import quant


class TVMRequest(BaseModel):
    present_value_amount: float | None = None
    future_value_amount: float | None = None
    rate: float
    periods: float
    cash_flows: list[float] | None = None


class PortfolioRequest(BaseModel):
    weights: list[float]
    expected_returns: list[float]
    covariance_matrix: list[list[float]]
    risk_free_rate: float = 0.0


class RiskRequest(BaseModel):
    returns: list[float]
    confidence: float = 0.95
    mean_return: float | None = None
    volatility: float | None = None
    equity_curve: list[float] | None = None


class OptionsRequest(BaseModel):
    spot: float
    strike: float
    rate: float
    volatility: float
    maturity: float
    option_type: str


class BondsRequest(BaseModel):
    face_value: float
    coupon_rate: float
    yield_rate: float
    periods: int
    frequency: int = 1


class CreditRequest(BaseModel):
    pd: float
    lgd: float
    ead: float


@app.post('/api/quant/tvm')
def quant_tvm(request: TVMRequest) -> dict:
    try:
        result = {
            'pv': quant.present_value(request.future_value_amount, request.rate, request.periods) if request.future_value_amount is not None else None,
            'fv': quant.future_value(request.present_value_amount, request.rate, request.periods) if request.present_value_amount is not None else None,
            'npv': quant.net_present_value(request.rate, request.cash_flows) if request.cash_flows else None,
            'irr': quant.internal_rate_of_return(request.cash_flows) if request.cash_flows else None,
        }
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/portfolio')
def quant_portfolio(request: PortfolioRequest) -> dict:
    try:
        exp = quant.portfolio_expected_return(request.weights, request.expected_returns)
        var = quant.portfolio_variance(request.weights, request.covariance_matrix)
        vol = quant.portfolio_volatility(request.weights, request.covariance_matrix)
        return {'expected_return': exp, 'variance': var, 'volatility': vol, 'sharpe_ratio': quant.sharpe_ratio(exp, request.risk_free_rate, vol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/risk')
def quant_risk(request: RiskRequest) -> dict:
    try:
        mean_return = request.mean_return if request.mean_return is not None else sum(request.returns)/len(request.returns)
        vol = request.volatility if request.volatility is not None else (sum((r-mean_return)**2 for r in request.returns)/len(request.returns))**0.5
        curve = request.equity_curve if request.equity_curve else [100*(1+r) for r in request.returns]
        return {
            'historical_var': quant.historical_var(request.returns, request.confidence),
            'parametric_var': quant.parametric_var(mean_return, vol, request.confidence),
            'cvar': quant.cvar_expected_shortfall(request.returns, request.confidence),
            'max_drawdown': quant.max_drawdown(curve),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/options')
def quant_options(request: OptionsRequest) -> dict:
    try:
        return {
            'price': quant.black_scholes_price(request.spot, request.strike, request.rate, request.volatility, request.maturity, request.option_type),
            'greeks': quant.black_scholes_greeks(request.spot, request.strike, request.rate, request.volatility, request.maturity, request.option_type),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/bonds')
def quant_bonds(request: BondsRequest) -> dict:
    try:
        return {
            'price': quant.bond_price(request.face_value, request.coupon_rate, request.yield_rate, request.periods, request.frequency),
            'macaulay_duration': quant.macaulay_duration(request.face_value, request.coupon_rate, request.yield_rate, request.periods, request.frequency),
            'modified_duration': quant.modified_duration(request.face_value, request.coupon_rate, request.yield_rate, request.periods, request.frequency),
            'convexity': quant.convexity(request.face_value, request.coupon_rate, request.yield_rate, request.periods, request.frequency),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/credit')
def quant_credit(request: CreditRequest) -> dict:
    try:
        return {'expected_loss': quant.expected_loss(request.pd, request.lgd, request.ead)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
