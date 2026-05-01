from __future__ import annotations

import math
from statistics import NormalDist
from typing import Iterable


def _as_float_list(values: Iterable[float], name: str) -> list[float]:
    result = [float(v) for v in values]
    if not result:
        raise ValueError(f"{name} must not be empty")
    if any(not math.isfinite(v) for v in result):
        raise ValueError(f"{name} contains non-finite values")
    return result


def present_value(future_value_amount: float, rate: float, periods: float) -> float:
    if periods < 0:
        raise ValueError("periods must be non-negative")
    if rate <= -1:
        raise ValueError("rate must be greater than -1")
    return float(future_value_amount / ((1 + rate) ** periods))


def future_value(present_value_amount: float, rate: float, periods: float) -> float:
    if periods < 0:
        raise ValueError("periods must be non-negative")
    if rate <= -1:
        raise ValueError("rate must be greater than -1")
    return float(present_value_amount * ((1 + rate) ** periods))


def net_present_value(rate: float, cash_flows: Iterable[float]) -> float:
    flows = _as_float_list(cash_flows, "cash_flows")
    if rate <= -1:
        raise ValueError("rate must be greater than -1")
    return float(sum(cf / ((1 + rate) ** t) for t, cf in enumerate(flows)))


def internal_rate_of_return(cash_flows: Iterable[float], guess: float = 0.1) -> float:
    flows = _as_float_list(cash_flows, "cash_flows")
    if not (any(cf > 0 for cf in flows) and any(cf < 0 for cf in flows)):
        raise ValueError("cash_flows must include at least one positive and one negative value")

    low, high = -0.9999, 10.0
    f_low = net_present_value(low, flows)
    f_high = net_present_value(high, flows)
    if f_low * f_high > 0:
        x = max(-0.95, min(guess, 1.0))
        for _ in range(100):
            f_x = net_present_value(x, flows)
            deriv = sum((-t * cf) / ((1 + x) ** (t + 1)) for t, cf in enumerate(flows) if t > 0)
            if abs(deriv) < 1e-12:
                break
            x_new = x - f_x / deriv
            if x_new <= -0.9999 or not math.isfinite(x_new):
                break
            if abs(x_new - x) < 1e-12:
                return float(x_new)
            x = x_new
        raise ValueError("Unable to solve IRR with robust fallback")

    for _ in range(200):
        mid = (low + high) / 2
        f_mid = net_present_value(mid, flows)
        if abs(f_mid) < 1e-10:
            return float(mid)
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return float((low + high) / 2)


def portfolio_expected_return(weights: Iterable[float], expected_returns: Iterable[float]) -> float:
    w = _as_float_list(weights, "weights")
    er = _as_float_list(expected_returns, "expected_returns")
    if len(w) != len(er):
        raise ValueError("weights and expected_returns must have same length")
    return float(sum(a * b for a, b in zip(w, er)))


def portfolio_variance(weights: Iterable[float], covariance_matrix: list[list[float]]) -> float:
    w = _as_float_list(weights, "weights")
    n = len(w)
    if len(covariance_matrix) != n or any(len(row) != n for row in covariance_matrix):
        raise ValueError("covariance_matrix shape must match weights length")
    var = 0.0
    for i in range(n):
        for j in range(n):
            cov = float(covariance_matrix[i][j])
            if not math.isfinite(cov):
                raise ValueError("covariance_matrix contains non-finite values")
            var += w[i] * cov * w[j]
    return float(var)


def portfolio_volatility(weights: Iterable[float], covariance_matrix: list[list[float]]) -> float:
    var = portfolio_variance(weights, covariance_matrix)
    if var < 0:
        raise ValueError("portfolio variance cannot be negative")
    return float(math.sqrt(var))


def sharpe_ratio(portfolio_return: float, risk_free_rate: float, volatility: float) -> float:
    if volatility <= 0:
        raise ValueError("volatility must be positive")
    return float((portfolio_return - risk_free_rate) / volatility)


def historical_var(returns: Iterable[float], confidence: float = 0.95) -> float:
    r = sorted(_as_float_list(returns, "returns"))
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    alpha = 1 - confidence
    idx = max(0, min(len(r) - 1, int(math.floor(alpha * len(r)))))
    return float(-r[idx])


def parametric_var(mean_return: float, volatility: float, confidence: float = 0.95) -> float:
    if volatility < 0:
        raise ValueError("volatility must be non-negative")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    z = NormalDist().inv_cdf(1 - confidence)
    return float(-(mean_return + z * volatility))


def cvar_expected_shortfall(returns: Iterable[float], confidence: float = 0.95) -> float:
    r = sorted(_as_float_list(returns, "returns"))
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    threshold = -historical_var(r, confidence)
    tail = [x for x in r if x <= threshold and x < 0]
    if not tail:
        return 0.0
    return float(-sum(tail) / len(tail))


def max_drawdown(values: Iterable[float]) -> float:
    series = _as_float_list(values, "values")
    peak = series[0]
    mdd = 0.0
    for v in series:
        if v <= 0:
            raise ValueError("values must be positive for drawdown calculation")
        peak = max(peak, v)
        dd = (v / peak) - 1
        mdd = min(mdd, dd)
    return float(mdd)


def _d1_d2(spot: float, strike: float, rate: float, volatility: float, maturity: float) -> tuple[float, float]:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if maturity < 0:
        raise ValueError("maturity must be non-negative")
    if volatility < 0:
        raise ValueError("volatility must be non-negative")
    if maturity == 0 or volatility == 0:
        intrinsic = math.log(spot / strike) if spot > 0 and strike > 0 else 0.0
        inf = float("inf") if intrinsic > 0 else float("-inf")
        return inf, inf
    d1 = (math.log(spot / strike) + (rate + 0.5 * volatility**2) * maturity) / (volatility * math.sqrt(maturity))
    d2 = d1 - volatility * math.sqrt(maturity)
    return d1, d2


def black_scholes_price(spot: float, strike: float, rate: float, volatility: float, maturity: float, option_type: str) -> float:
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if maturity == 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        return float(intrinsic)
    if volatility == 0:
        discounted_strike = strike * math.exp(-rate * maturity)
        deterministic = max(spot - discounted_strike, 0.0) if option_type == "call" else max(discounted_strike - spot, 0.0)
        return float(deterministic)
    d1, d2 = _d1_d2(spot, strike, rate, volatility, maturity)
    n = NormalDist()
    disc_k = strike * math.exp(-rate * maturity)
    if option_type == "call":
        return float(spot * n.cdf(d1) - disc_k * n.cdf(d2))
    return float(disc_k * n.cdf(-d2) - spot * n.cdf(-d1))


def black_scholes_greeks(spot: float, strike: float, rate: float, volatility: float, maturity: float, option_type: str) -> dict[str, float]:
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if maturity == 0 or volatility == 0:
        delta = 1.0 if (option_type == "call" and spot > strike) else -1.0 if (option_type == "put" and spot < strike) else 0.0
        return {"delta": float(delta), "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
    d1, d2 = _d1_d2(spot, strike, rate, volatility, maturity)
    n = NormalDist()
    pdf_d1 = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    gamma = pdf_d1 / (spot * volatility * math.sqrt(maturity))
    vega = spot * pdf_d1 * math.sqrt(maturity)
    if option_type == "call":
        delta = n.cdf(d1)
        theta = -(spot * pdf_d1 * volatility) / (2 * math.sqrt(maturity)) - rate * strike * math.exp(-rate * maturity) * n.cdf(d2)
        rho = strike * maturity * math.exp(-rate * maturity) * n.cdf(d2)
    else:
        delta = n.cdf(d1) - 1
        theta = -(spot * pdf_d1 * volatility) / (2 * math.sqrt(maturity)) + rate * strike * math.exp(-rate * maturity) * n.cdf(-d2)
        rho = -strike * maturity * math.exp(-rate * maturity) * n.cdf(-d2)
    return {"delta": float(delta), "gamma": float(gamma), "vega": float(vega), "theta": float(theta), "rho": float(rho)}


def bond_price(face_value: float, coupon_rate: float, yield_rate: float, periods: int, frequency: int = 1) -> float:
    if face_value <= 0 or periods <= 0 or frequency <= 0:
        raise ValueError("face_value, periods, and frequency must be positive")
    if yield_rate <= -1:
        raise ValueError("yield_rate must be greater than -1")
    coupon = face_value * coupon_rate / frequency
    y = yield_rate / frequency
    total_periods = periods * frequency
    pv_coupons = sum(coupon / ((1 + y) ** t) for t in range(1, total_periods + 1))
    pv_face = face_value / ((1 + y) ** total_periods)
    return float(pv_coupons + pv_face)


def macaulay_duration(face_value: float, coupon_rate: float, yield_rate: float, periods: int, frequency: int = 1) -> float:
    price = bond_price(face_value, coupon_rate, yield_rate, periods, frequency)
    coupon = face_value * coupon_rate / frequency
    y = yield_rate / frequency
    total_periods = periods * frequency
    weighted = 0.0
    for t in range(1, total_periods + 1):
        cf = coupon if t < total_periods else coupon + face_value
        pv = cf / ((1 + y) ** t)
        weighted += t * pv
    return float(weighted / price / frequency)


def modified_duration(face_value: float, coupon_rate: float, yield_rate: float, periods: int, frequency: int = 1) -> float:
    mac = macaulay_duration(face_value, coupon_rate, yield_rate, periods, frequency)
    return float(mac / (1 + yield_rate / frequency))


def convexity(face_value: float, coupon_rate: float, yield_rate: float, periods: int, frequency: int = 1) -> float:
    price = bond_price(face_value, coupon_rate, yield_rate, periods, frequency)
    coupon = face_value * coupon_rate / frequency
    y = yield_rate / frequency
    total_periods = periods * frequency
    acc = 0.0
    for t in range(1, total_periods + 1):
        cf = coupon if t < total_periods else coupon + face_value
        acc += cf * t * (t + 1) / ((1 + y) ** (t + 2))
    return float(acc / price / (frequency**2))


def expected_loss(pd: float, lgd: float, ead: float) -> float:
    if not 0 <= pd <= 1 or not 0 <= lgd <= 1:
        raise ValueError("pd and lgd must be in [0,1]")
    if ead < 0:
        raise ValueError("ead must be non-negative")
    return float(pd * lgd * ead)


def dividend_discount_model_single_stage(dividend_next: float, required_return: float, growth_rate: float) -> float:
    if required_return <= growth_rate:
        raise ValueError("required_return must be greater than growth_rate")
    if dividend_next < 0:
        raise ValueError("dividend_next must be non-negative")
    return float(dividend_next / (required_return - growth_rate))


def dividend_discount_model_multi_stage(dividends: Iterable[float], terminal_growth: float, required_return: float) -> float:
    ds = _as_float_list(dividends, "dividends")
    if required_return <= terminal_growth:
        raise ValueError("required_return must be greater than terminal_growth")
    if any(d < 0 for d in ds):
        raise ValueError("dividends must be non-negative")
    pv_stages = sum(d / ((1 + required_return) ** (i + 1)) for i, d in enumerate(ds))
    terminal_next = ds[-1] * (1 + terminal_growth)
    terminal_value = terminal_next / (required_return - terminal_growth)
    pv_terminal = terminal_value / ((1 + required_return) ** len(ds))
    return float(pv_stages + pv_terminal)


def dscr(net_operating_income: float, debt_service: float) -> float:
    if debt_service <= 0:
        raise ValueError("debt_service must be positive")
    return float(net_operating_income / debt_service)


def interest_coverage_ratio(ebit: float, interest_expense: float) -> float:
    if interest_expense <= 0:
        raise ValueError("interest_expense must be positive")
    return float(ebit / interest_expense)


def sortino_ratio(returns: Iterable[float], target_return: float = 0.0) -> float:
    r = _as_float_list(returns, "returns")
    downside = [(x - target_return) ** 2 for x in r if x < target_return]
    if not downside:
        raise ValueError("downside deviation is zero")
    downside_dev = math.sqrt(sum(downside) / len(r))
    mean_r = sum(r) / len(r)
    return float((mean_r - target_return) / downside_dev)


def information_ratio(portfolio_returns: Iterable[float], benchmark_returns: Iterable[float]) -> float:
    p = _as_float_list(portfolio_returns, "portfolio_returns")
    b = _as_float_list(benchmark_returns, "benchmark_returns")
    if len(p) != len(b):
        raise ValueError("portfolio and benchmark returns length mismatch")
    active = [x - y for x, y in zip(p, b)]
    tracking_error = math.sqrt(sum(a * a for a in active) / len(active))
    if tracking_error == 0:
        raise ValueError("tracking error is zero")
    return float((sum(active) / len(active)) / tracking_error)


def capm_expected_return(risk_free_rate: float, beta: float, market_return: float) -> float:
    return float(risk_free_rate + beta * (market_return - risk_free_rate))


def beta_against_market(asset_returns: Iterable[float], market_returns: Iterable[float]) -> float:
    a = _as_float_list(asset_returns, "asset_returns")
    m = _as_float_list(market_returns, "market_returns")
    if len(a) != len(m):
        raise ValueError("asset and market returns length mismatch")
    ma = sum(a) / len(a)
    mm = sum(m) / len(m)
    cov = sum((x - ma) * (y - mm) for x, y in zip(a, m)) / len(a)
    var_m = sum((y - mm) ** 2 for y in m) / len(m)
    if var_m == 0:
        raise ValueError("market variance is zero")
    return float(cov / var_m)


def jensen_alpha(asset_return: float, risk_free_rate: float, beta: float, market_return: float) -> float:
    expected = capm_expected_return(risk_free_rate, beta, market_return)
    return float(asset_return - expected)


def treynor_ratio(asset_return: float, risk_free_rate: float, beta: float) -> float:
    if beta == 0:
        raise ValueError("beta must be non-zero")
    return float((asset_return - risk_free_rate) / beta)


def put_call_parity_check(call_price: float, put_price: float, spot: float, strike: float, rate: float, maturity: float) -> dict[str, float]:
    pv_strike = strike * math.exp(-rate * maturity)
    lhs = call_price - put_price
    rhs = spot - pv_strike
    return {"lhs": float(lhs), "rhs": float(rhs), "difference": float(lhs - rhs), "parity_holds": float(abs(lhs-rhs))}


def crr_binomial_option_price(spot: float, strike: float, rate: float, volatility: float, maturity: float, steps: int, option_type: str, style: str = "european") -> float:
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")
    if style not in {"european", "american"}:
        raise ValueError("style must be 'european' or 'american'")
    if steps <= 0 or maturity <= 0 or spot <= 0 or strike <= 0 or volatility < 0:
        raise ValueError("invalid binomial inputs")
    dt = maturity / steps
    u = math.exp(volatility * math.sqrt(dt))
    d = 1 / u if u != 0 else 0
    disc = math.exp(-rate * dt)
    p = (math.exp(rate * dt) - d) / (u - d)
    if not 0 <= p <= 1:
        raise ValueError("risk-neutral probability out of bounds")
    values = []
    for j in range(steps + 1):
        s_t = spot * (u ** (steps - j)) * (d ** j)
        intrinsic = max(s_t - strike, 0.0) if option_type == "call" else max(strike - s_t, 0.0)
        values.append(intrinsic)
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            continuation = disc * (p * values[j] + (1 - p) * values[j + 1])
            if style == "american":
                s_t = spot * (u ** (i - j)) * (d ** j)
                intrinsic = max(s_t - strike, 0.0) if option_type == "call" else max(strike - s_t, 0.0)
                values[j] = max(intrinsic, continuation)
            else:
                values[j] = continuation
    return float(values[0])


def operational_risk_lda(lambda_frequency: float, severity_mu: float, severity_sigma: float, simulations: int = 10000, confidence: float = 0.99, seed: int = 42) -> dict[str, float]:
    if lambda_frequency < 0 or severity_sigma < 0 or simulations <= 0:
        raise ValueError("invalid operational risk parameters")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    import numpy as np

    rng = np.random.default_rng(seed)
    freqs = rng.poisson(lambda_frequency, size=simulations)
    losses = np.zeros(simulations)
    for i, n in enumerate(freqs):
        if n > 0:
            severities = rng.lognormal(mean=severity_mu, sigma=severity_sigma, size=n)
            losses[i] = float(np.sum(severities))
    var = float(np.quantile(losses, confidence))
    tail = losses[losses >= var]
    es = float(np.mean(tail)) if len(tail) else var
    return {"mean_loss": float(np.mean(losses)), "var": var, "expected_shortfall": es}
