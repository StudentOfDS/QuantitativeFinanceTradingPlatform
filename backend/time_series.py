from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.stattools import adfuller
except Exception:
    adfuller = None

try:
    from arch import arch_model
except Exception:
    arch_model = None


def simple_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().dropna()


def log_returns(prices: pd.Series) -> pd.Series:
    return np.log(prices / prices.shift(1)).dropna()


def rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    return returns.rolling(window).std()


def historical_annualized_volatility(returns: pd.Series, periods: int = 252) -> float:
    return float(returns.std(ddof=0) * np.sqrt(periods))


def ewma_volatility(returns: pd.Series, span: int = 20) -> pd.Series:
    return returns.ewm(span=span, adjust=False).std()


def rolling_drawdown(prices: pd.Series) -> pd.Series:
    return prices / prices.cummax() - 1


def current_drawdown(prices: pd.Series) -> float:
    dd = rolling_drawdown(prices)
    return float(dd.iloc[-1])


def volatility_regime_classification(current_vol: float, hist_vol: float) -> str:
    if current_vol < hist_vol * 0.8:
        return 'low'
    if current_vol > hist_vol * 1.2:
        return 'high'
    return 'normal'


def autocorrelation_summary(returns: pd.Series, max_lag: int = 5) -> dict:
    return {f'lag_{lag}': float(returns.autocorr(lag=lag)) for lag in range(1, max_lag + 1)}


def adf_stationarity(series: pd.Series) -> tuple[dict, list[str]]:
    warnings = []
    if adfuller is None:
        return {'available': False, 'reason': 'statsmodels unavailable'}, ['statsmodels unavailable: ADF skipped']
    res = adfuller(series.dropna().to_numpy())
    return {'available': True, 'statistic': float(res[0]), 'p_value': float(res[1]), 'critical_values': {k: float(v) for k,v in res[4].items()}}, warnings


def garch_forecast(returns: pd.Series) -> tuple[dict, list[str]]:
    warnings = []
    if arch_model is None:
        return {'available': False, 'reason': 'arch unavailable', 'fallback': 'ewma'}, ['arch unavailable: GARCH skipped, EWMA used']
    try:
        model = arch_model((returns.dropna() * 100), mean='Zero', vol='GARCH', p=1, q=1, dist='normal')
        fit = model.fit(disp='off')
        f = fit.forecast(horizon=1)
        v = float(np.sqrt(f.variance.iloc[-1, 0]) / 100)
        return {'available': True, 'forecast_volatility': v}, warnings
    except Exception as exc:
        return {'available': False, 'reason': str(exc), 'fallback': 'ewma'}, [f'GARCH fit failed: {exc}']


def time_series_context(df: pd.DataFrame) -> dict:
    prices = pd.to_numeric(df['Close'], errors='coerce').dropna()
    if len(prices) < 30:
        raise ValueError('Insufficient rows for time-series context (need >=30 close prices)')
    r = simple_returns(prices)
    lr = log_returns(prices)
    rv = rolling_volatility(r)
    hv = historical_annualized_volatility(r)
    ew = ewma_volatility(r)
    dd = rolling_drawdown(prices)
    cdd = current_drawdown(prices)
    regime = volatility_regime_classification(float(rv.dropna().iloc[-1]) if not rv.dropna().empty else float(ew.dropna().iloc[-1]), hv)
    acf = autocorrelation_summary(r)
    adf, w1 = adf_stationarity(r)
    garch, w2 = garch_forecast(r)
    return {
        'latest_return': float(r.iloc[-1]),
        'latest_log_return': float(lr.iloc[-1]),
        'historical_volatility': hv,
        'ewma_volatility': float(ew.dropna().iloc[-1]),
        'rolling_volatility_latest': float(rv.dropna().iloc[-1]) if not rv.dropna().empty else float(ew.dropna().iloc[-1]),
        'max_drawdown': float(dd.min()),
        'current_drawdown': cdd,
        'volatility_regime': regime,
        'autocorrelation_summary': acf,
        'adf_result': adf,
        'garch_forecast': garch,
        'warnings': w1 + w2,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
