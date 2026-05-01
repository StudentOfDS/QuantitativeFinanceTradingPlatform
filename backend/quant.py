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
    if maturity == 0 or volatility == 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        return float(intrinsic)
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
