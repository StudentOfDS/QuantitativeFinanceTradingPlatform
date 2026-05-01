from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.data import DataEngine, InputAdapter
from backend.backtest import run_vectorized_backtest
from backend.reports import build_research_report
from backend.storage import initialize_storage, list_recent_reports, record_audit_event, record_backtest_run, record_report_run

app = FastAPI(title=settings.app_name)

initialize_storage()
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
        if not request.returns:
            raise ValueError('returns must not be empty')
        mean_return = request.mean_return if request.mean_return is not None else sum(request.returns)/len(request.returns)
        vol = request.volatility if request.volatility is not None else (sum((r-mean_return)**2 for r in request.returns)/len(request.returns))**0.5
        if request.equity_curve:
            curve = request.equity_curve
        else:
            equity = 100.0
            curve = []
            for r in request.returns:
                equity *= (1 + r)
                curve.append(equity)
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


class CorporateRequest(BaseModel):
    dividend_next: float
    required_return: float
    growth_rate: float
    dividends: list[float] | None = None
    terminal_growth: float | None = None
    net_operating_income: float = 0.0
    debt_service: float = 1.0
    ebit: float = 0.0
    interest_expense: float = 1.0


class PerformanceRequest(BaseModel):
    returns: list[float]
    target_return: float = 0.0
    benchmark_returns: list[float]


class CapmRequest(BaseModel):
    asset_returns: list[float]
    market_returns: list[float]
    risk_free_rate: float


class BinomialRequest(BaseModel):
    spot: float
    strike: float
    rate: float
    volatility: float
    maturity: float
    steps: int
    option_type: str
    style: str = 'european'


class OperationalRiskRequest(BaseModel):
    lambda_frequency: float
    severity_mu: float
    severity_sigma: float
    simulations: int = 10000
    confidence: float = 0.99
    seed: int = 42


@app.post('/api/quant/corporate')
def quant_corporate(request: CorporateRequest) -> dict:
    try:
        multi_stage = None
        if request.dividends and request.terminal_growth is not None:
            multi_stage = quant.dividend_discount_model_multi_stage(request.dividends, request.terminal_growth, request.required_return)
        return {
            'ddm_single_stage': quant.dividend_discount_model_single_stage(request.dividend_next, request.required_return, request.growth_rate),
            'ddm_multi_stage': multi_stage,
            'dscr': quant.dscr(request.net_operating_income, request.debt_service),
            'interest_coverage_ratio': quant.interest_coverage_ratio(request.ebit, request.interest_expense),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/performance')
def quant_performance(request: PerformanceRequest) -> dict:
    try:
        return {
            'sortino_ratio': quant.sortino_ratio(request.returns, request.target_return),
            'information_ratio': quant.information_ratio(request.returns, request.benchmark_returns),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/capm')
def quant_capm(request: CapmRequest) -> dict:
    try:
        beta = quant.beta_against_market(request.asset_returns, request.market_returns)
        asset_mean = sum(request.asset_returns) / len(request.asset_returns)
        market_mean = sum(request.market_returns) / len(request.market_returns)
        return {
            'beta': beta,
            'capm_expected_return': quant.capm_expected_return(request.risk_free_rate, beta, market_mean),
            'jensen_alpha': quant.jensen_alpha(asset_mean, request.risk_free_rate, beta, market_mean),
            'treynor_ratio': quant.treynor_ratio(asset_mean, request.risk_free_rate, beta),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/binomial')
def quant_binomial(request: BinomialRequest) -> dict:
    try:
        return {
            'price': quant.crr_binomial_option_price(request.spot, request.strike, request.rate, request.volatility, request.maturity, request.steps, request.option_type, request.style)
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/quant/operational-risk')
def quant_operational_risk(request: OperationalRiskRequest) -> dict:
    try:
        return quant.operational_risk_lda(
            request.lambda_frequency,
            request.severity_mu,
            request.severity_sigma,
            request.simulations,
            request.confidence,
            request.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class BacktestRequest(BaseModel):
    rows: list[dict]
    strategy: str
    strategy_params: dict = {}
    initial_capital: float = 10000
    transaction_cost_bps: float = 0
    slippage_bps: float = 0
    persist: bool = True


@app.post('/api/backtest/vectorized')
def backtest_vectorized(request: BacktestRequest) -> dict:
    try:
        df = InputAdapter.from_manual_rows(request.rows)
        normalized, _ = DataEngine.normalize_market_data(df)
        result = run_vectorized_backtest(
            normalized,
            request.strategy,
            request.strategy_params,
            request.initial_capital,
            request.transaction_cost_bps,
            request.slippage_bps,
        )
        if request.persist:
            backtest_id = record_backtest_run(result)
            record_audit_event('backtest_run', {'backtest_id': backtest_id, 'strategy': request.strategy})
            result['backtest_id'] = backtest_id
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class FullReportRequest(BaseModel):
    rows: list[dict]
    strategy: str = 'buy_and_hold'
    strategy_params: dict = {}
    initial_capital: float = 10000
    transaction_cost_bps: float = 0
    slippage_bps: float = 0


@app.post('/api/report/full')
def report_full(request: FullReportRequest) -> dict:
    try:
        report = build_research_report(request.rows, request.strategy, request.strategy_params, request.initial_capital, request.transaction_cost_bps, request.slippage_bps)
        report_id = record_report_run(report)
        record_audit_event('report_run', {'report_id': report_id, 'strategy': request.strategy})
        return {'report_id': report_id, 'report': report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get('/api/history/reports')
def report_history(limit: int = 20) -> dict:
    return {'items': list_recent_reports(limit)}
