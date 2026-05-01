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


def test_corporate_metrics_and_ddm():
    assert quant.dividend_discount_model_single_stage(2, 0.1, 0.04) == pytest.approx(33.333333, rel=1e-4)
    m = quant.dividend_discount_model_multi_stage([1.0, 1.2, 1.4], 0.03, 0.1)
    assert m > 0
    assert quant.dscr(200, 100) == 2
    assert quant.interest_coverage_ratio(150, 50) == 3


def test_performance_capm_and_parity():
    r = [0.02, 0.01, -0.01, 0.03]
    b = [0.01, 0.005, -0.015, 0.02]
    assert quant.sortino_ratio(r, 0.0) > 0
    assert quant.information_ratio(r, b) != 0
    beta = quant.beta_against_market(r, b)
    assert beta != 0
    capm = quant.capm_expected_return(0.02, beta, sum(b)/len(b))
    assert isinstance(capm, float)
    assert isinstance(quant.jensen_alpha(sum(r)/len(r), 0.02, beta, sum(b)/len(b)), float)
    assert isinstance(quant.treynor_ratio(sum(r)/len(r), 0.02, beta), float)
    parity = quant.put_call_parity_check(10, 5, 100, 100, 0.05, 1)
    assert 'difference' in parity


def test_binomial_and_operational_risk():
    euro_call = quant.crr_binomial_option_price(100, 100, 0.05, 0.2, 1, 100, 'call', 'european')
    amer_put = quant.crr_binomial_option_price(100, 100, 0.05, 0.2, 1, 100, 'put', 'american')
    assert euro_call > 0
    assert amer_put > 0
    risk = quant.operational_risk_lda(5, 2.0, 0.8, simulations=2000, seed=7)
    assert risk['var'] >= risk['mean_loss']


def test_new_quant_endpoints_smoke():
    corporate = client.post('/api/quant/corporate', json={'dividend_next':2.0,'required_return':0.1,'growth_rate':0.04,'dividends':[1.0,1.2,1.4],'terminal_growth':0.03,'net_operating_income':200,'debt_service':100,'ebit':150,'interest_expense':50})
    assert corporate.status_code == 200
    performance = client.post('/api/quant/performance', json={'returns':[0.02,0.01,-0.01,0.03],'benchmark_returns':[0.01,0.005,-0.015,0.02],'target_return':0.0})
    assert performance.status_code == 200
    capm = client.post('/api/quant/capm', json={'asset_returns':[0.02,0.01,-0.01,0.03],'market_returns':[0.01,0.005,-0.015,0.02],'risk_free_rate':0.02})
    assert capm.status_code == 200
    bino = client.post('/api/quant/binomial', json={'spot':100,'strike':100,'rate':0.05,'volatility':0.2,'maturity':1,'steps':100,'option_type':'call','style':'european'})
    assert bino.status_code == 200
    op = client.post('/api/quant/operational-risk', json={'lambda_frequency':5,'severity_mu':2.0,'severity_sigma':0.8,'simulations':2000,'seed':7,'confidence':0.99})
    assert op.status_code == 200


def test_binomial_zero_volatility_behavior():
    call = quant.crr_binomial_option_price(100, 100, 0.05, 0.0, 1, 10, 'call', 'european')
    put = quant.crr_binomial_option_price(90, 100, 0.05, 0.0, 1, 10, 'put', 'american')
    assert call == pytest.approx(max(100 - 100 * math.exp(-0.05), 0), rel=1e-6)
    assert put == pytest.approx(max(100 * math.exp(-0.05) - 90, 0), rel=1e-6)


def test_risk_endpoint_empty_returns_and_compounded_curve():
    empty = client.post('/api/quant/risk', json={'returns': [], 'confidence': 0.95})
    assert empty.status_code == 400
    resp = client.post('/api/quant/risk', json={'returns': [-0.5, -0.5], 'confidence': 0.95})
    assert resp.status_code == 200
    assert resp.json()['max_drawdown'] == pytest.approx(-0.5)
