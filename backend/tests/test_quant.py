import math

import pytest

from backend import quant
from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_tvm_and_irr():
    assert quant.present_value(110, 0.1, 1) == pytest.approx(100)
    assert quant.future_value(100, 0.1, 1) == pytest.approx(110)
    assert quant.net_present_value(0.1, [-100, 60, 60]) == pytest.approx(4.132231, rel=1e-4)
    irr = quant.internal_rate_of_return([-100, 60, 60])
    assert 0.13 < irr < 0.14


def test_invalid_rates():
    with pytest.raises(ValueError):
        quant.present_value(100, -1.0, 1)


def test_portfolio_and_shape_mismatch():
    w = [0.5, 0.5]
    er = [0.1, 0.2]
    cov = [[0.04, 0.01], [0.01, 0.09]]
    assert quant.portfolio_expected_return(w, er) == pytest.approx(0.15)
    assert quant.portfolio_variance(w, cov) == pytest.approx(0.0375)
    assert quant.portfolio_volatility(w, cov) == pytest.approx(0.193649, rel=1e-4)
    assert quant.sharpe_ratio(0.15, 0.02, 0.193649) == pytest.approx(0.67132, rel=1e-3)
    with pytest.raises(ValueError):
        quant.portfolio_expected_return([1.0], [0.1, 0.2])


def test_var_cvar_and_drawdown():
    returns = [-0.03, -0.01, 0.0, 0.01, 0.02]
    assert quant.historical_var(returns, 0.95) == pytest.approx(0.03)
    assert quant.parametric_var(0.0, 0.02, 0.95) == pytest.approx(0.032897, rel=1e-4)
    assert quant.cvar_expected_shortfall(returns, 0.95) == pytest.approx(0.03)
    assert quant.cvar_expected_shortfall([0.01, 0.02], 0.5) >= 0
    assert quant.max_drawdown([100, 110, 90, 95, 120]) == pytest.approx(-0.181818, rel=1e-4)


def test_black_scholes_and_expiry_behavior():
    call = quant.black_scholes_price(100, 100, 0.05, 0.2, 1, 'call')
    put = quant.black_scholes_price(100, 100, 0.05, 0.2, 1, 'put')
    assert call > put
    greeks = quant.black_scholes_greeks(100, 100, 0.05, 0.2, 1, 'call')
    assert set(greeks.keys()) == {'delta', 'gamma', 'vega', 'theta', 'rho'}
    expiry_price = quant.black_scholes_price(90, 100, 0.05, 0.0, 0, 'put')
    assert expiry_price == 10


def test_bond_and_credit():
    price = quant.bond_price(1000, 0.05, 0.04, 5, 1)
    assert price > 1000
    mac = quant.macaulay_duration(1000, 0.05, 0.04, 5, 1)
    mod = quant.modified_duration(1000, 0.05, 0.04, 5, 1)
    conv = quant.convexity(1000, 0.05, 0.04, 5, 1)
    assert mac > mod > 0
    assert conv > 0
    assert quant.expected_loss(0.02, 0.45, 1_000_000) == pytest.approx(9000)


def test_zero_volatility_discounted_forward_pricing():
    call = quant.black_scholes_price(100, 100, 0.05, 0.0, 1, 'call')
    put = quant.black_scholes_price(90, 100, 0.05, 0.0, 1, 'put')
    assert call == pytest.approx(max(100 - 100 * math.exp(-0.05), 0), rel=1e-6)
    assert put == pytest.approx(max(100 * math.exp(-0.05) - 90, 0), rel=1e-6)


def test_expiry_still_intrinsic_value():
    assert quant.black_scholes_price(105, 100, 0.05, 0.2, 0, 'call') == 5
    assert quant.black_scholes_price(95, 100, 0.05, 0.2, 0, 'put') == 5


def test_quant_endpoints_smoke():
    tvm = client.post('/api/quant/tvm', json={'present_value_amount': 100, 'future_value_amount': 110, 'rate': 0.1, 'periods': 1, 'cash_flows': [-100, 60, 60]})
    assert tvm.status_code == 200
    portfolio = client.post('/api/quant/portfolio', json={'weights': [0.5,0.5], 'expected_returns':[0.1,0.2], 'covariance_matrix': [[0.04,0.01],[0.01,0.09]], 'risk_free_rate': 0.02})
    assert portfolio.status_code == 200
    risk = client.post('/api/quant/risk', json={'returns': [-0.03,-0.01,0.0,0.01,0.02], 'confidence': 0.95, 'equity_curve':[100,110,90,95,120]})
    assert risk.status_code == 200
    options = client.post('/api/quant/options', json={'spot':100,'strike':100,'rate':0.05,'volatility':0.2,'maturity':1,'option_type':'call'})
    assert options.status_code == 200
    bonds = client.post('/api/quant/bonds', json={'face_value':1000,'coupon_rate':0.05,'yield_rate':0.04,'periods':5,'frequency':1})
    assert bonds.status_code == 200
    credit = client.post('/api/quant/credit', json={'pd':0.02,'lgd':0.45,'ead':1000000})
    assert credit.status_code == 200
