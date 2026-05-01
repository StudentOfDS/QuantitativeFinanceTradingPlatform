from fastapi.testclient import TestClient

from backend.execution import GenericRestBroker, KillSwitch, MarketSnapshot, OrderRequest, PaperBroker, RiskManager
from backend.main import app

client = TestClient(app)


def test_paper_market_and_limit_behaviors():
    b = PaperBroker(commission_bps=0, slippage_bps=0)
    snap = MarketSnapshot('AAPL', bid=99, ask=101, last=100)
    buy = b.execute(OrderRequest('AAPL','BUY',10,'market'), snap)
    assert buy.fill_price == 101
    sell = b.execute(OrderRequest('AAPL','SELL',5,'market'), snap)
    assert sell.fill_price == 99
    fill_buy_limit = b.execute(OrderRequest('AAPL','BUY',1,'limit',limit_price=102), snap)
    assert fill_buy_limit.status == 'filled'
    nofill_buy_limit = b.execute(OrderRequest('AAPL','BUY',1,'limit',limit_price=100), snap)
    assert nofill_buy_limit.status == 'unfilled'
    fill_sell_limit = b.execute(OrderRequest('AAPL','SELL',1,'limit',limit_price=98), snap)
    assert fill_sell_limit.status == 'filled'
    nofill_sell_limit = b.execute(OrderRequest('AAPL','SELL',1,'limit',limit_price=100), snap)
    assert nofill_sell_limit.status == 'unfilled'


def test_risk_and_live_gates():
    risk = RiskManager({'AAPL'}, max_qty=100, max_notional=1000)
    ks = KillSwitch()
    snap = MarketSnapshot('AAPL',99,101,100)
    assert not risk.check(OrderRequest('MSFT','BUY',1), snap, ks).approved
    assert not risk.check(OrderRequest('AAPL','BUY',1000), snap, ks).approved
    ks.active = True
    assert not risk.check(OrderRequest('AAPL','BUY',1), snap, ks).approved
    ks.active = False
    live = GenericRestBroker({'TRADING_MODE':'paper','ENABLE_LIVE_TRADING':False,'DRY_RUN':True,'BROKER_API_KEY':'','BROKER_API_SECRET':'','BROKER_ENDPOINT':''})
    rep = live.execute(OrderRequest('AAPL','BUY',1), risk.check(OrderRequest('AAPL','BUY',1), snap, ks), ks)
    assert rep.status == 'rejected'


def test_execution_api_smoke():
    payload = {'symbol':'AAPL','side':'BUY','quantity':1,'order_type':'market','bid':99,'ask':101,'last':100}
    r = client.post('/api/execution/paper/order', json=payload)
    assert r.status_code == 200
    p = client.get('/api/execution/paper/portfolio')
    assert p.status_code == 200
    a = client.get('/api/execution/audit/recent')
    assert a.status_code == 200
