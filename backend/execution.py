from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal


Side = Literal['BUY', 'SELL']
Type_ = Literal['market', 'limit']
Action = Literal['BUY','SELL','HOLD','LONG_SPREAD','SHORT_SPREAD','TARGET_ALLOCATION']


@dataclass
class OrderRequest:
    symbol: str
    side: Side
    quantity: float
    order_type: Type_ = 'market'
    limit_price: float | None = None


@dataclass
class MarketSnapshot:
    symbol: str
    bid: float
    ask: float
    last: float


@dataclass
class Position:
    symbol: str
    quantity: Decimal = Decimal('0')
    avg_entry_price: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')


@dataclass
class PortfolioState:
    cash: Decimal = Decimal('100000')
    positions: dict[str, Position] = field(default_factory=dict)


@dataclass
class RiskDecision:
    approved: bool
    reason: str = ''


@dataclass
class ExecutionReport:
    status: str
    filled_quantity: float
    fill_price: float | None
    fee: float
    symbol: str
    side: str
    reason: str = ''
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class KillSwitch:
    def __init__(self) -> None:
        self.active = False


class RiskManager:
    def __init__(self, allowed_symbols: set[str], max_qty: float = 1e6, max_notional: float = 1e7) -> None:
        self.allowed_symbols = allowed_symbols
        self.max_qty = max_qty
        self.max_notional = max_notional

    def check(self, order: OrderRequest, snapshot: MarketSnapshot, kill_switch: KillSwitch) -> RiskDecision:
        if kill_switch.active:
            return RiskDecision(False, 'kill-switch active')
        if order.symbol not in self.allowed_symbols:
            return RiskDecision(False, 'symbol not allowed')
        if order.quantity > self.max_qty:
            return RiskDecision(False, 'max quantity breach')
        px = snapshot.ask if order.side == 'BUY' else snapshot.bid
        if order.quantity * px > self.max_notional:
            return RiskDecision(False, 'max notional breach')
        return RiskDecision(True, '')


class PaperBroker:
    def __init__(self, commission_bps: float = 1.0, slippage_bps: float = 0.0) -> None:
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps
        self.portfolio = PortfolioState()

    def _calc_fee(self, notional: Decimal) -> Decimal:
        return notional * Decimal(str(self.commission_bps)) / Decimal('10000')

    def execute(self, order: OrderRequest, snap: MarketSnapshot) -> ExecutionReport:
        fill_price = None
        status = 'unfilled'
        if order.order_type == 'market':
            fill_price = snap.ask if order.side == 'BUY' else snap.bid
            status = 'filled'
        else:
            if order.side == 'BUY' and order.limit_price is not None and order.limit_price >= snap.ask:
                fill_price = snap.ask
                status = 'filled'
            if order.side == 'SELL' and order.limit_price is not None and order.limit_price <= snap.bid:
                fill_price = snap.bid
                status = 'filled'
        if status != 'filled':
            return ExecutionReport(status='unfilled', filled_quantity=0, fill_price=None, fee=0, symbol=order.symbol, side=order.side, reason='limit not marketable')

        fp = Decimal(str(fill_price))
        qty = Decimal(str(order.quantity))
        slip = fp * Decimal(str(self.slippage_bps)) / Decimal('10000')
        fp_eff = fp + slip if order.side == 'BUY' else fp - slip
        notional = fp_eff * qty
        fee = self._calc_fee(notional)
        pos = self.portfolio.positions.get(order.symbol, Position(symbol=order.symbol))

        if order.side == 'BUY':
            new_qty = pos.quantity + qty
            pos.avg_entry_price = (pos.avg_entry_price * pos.quantity + fp_eff * qty) / new_qty if new_qty > 0 else Decimal('0')
            pos.quantity = new_qty
            self.portfolio.cash -= (notional + fee)
        else:
            sell_qty = min(qty, pos.quantity)
            realized = (fp_eff - pos.avg_entry_price) * sell_qty
            pos.realized_pnl += realized
            pos.quantity -= sell_qty
            self.portfolio.cash += (fp_eff * sell_qty - fee)
            if pos.quantity == 0:
                pos.avg_entry_price = Decimal('0')

        self.portfolio.positions[order.symbol] = pos
        return ExecutionReport(status='filled', filled_quantity=float(order.quantity), fill_price=float(fp_eff), fee=float(fee), symbol=order.symbol, side=order.side)


class GenericRestBroker:
    def __init__(self, config: dict):
        self.config = config

    def execute(self, order: OrderRequest, risk: RiskDecision, kill_switch: KillSwitch) -> ExecutionReport:
        needed = [self.config.get('TRADING_MODE') == 'live_rest', self.config.get('ENABLE_LIVE_TRADING') is True, self.config.get('DRY_RUN') is False, bool(self.config.get('BROKER_API_KEY')), bool(self.config.get('BROKER_API_SECRET')), bool(self.config.get('BROKER_ENDPOINT'))]
        if not all(needed):
            return ExecutionReport(status='rejected', filled_quantity=0, fill_price=None, fee=0, symbol=order.symbol, side=order.side, reason='live trading gate blocked')
        if kill_switch.active:
            return ExecutionReport(status='rejected', filled_quantity=0, fill_price=None, fee=0, symbol=order.symbol, side=order.side, reason='kill-switch active')
        if not risk.approved:
            return ExecutionReport(status='rejected', filled_quantity=0, fill_price=None, fee=0, symbol=order.symbol, side=order.side, reason=risk.reason)
        return ExecutionReport(status='submitted', filled_quantity=0, fill_price=None, fee=0, symbol=order.symbol, side=order.side)


class ExecutionRouter:
    def __init__(self, paper: PaperBroker, live: GenericRestBroker, risk: RiskManager, kill_switch: KillSwitch):
        self.paper, self.live, self.risk, self.kill_switch = paper, live, risk, kill_switch

    def route_paper_order(self, order: OrderRequest, snap: MarketSnapshot) -> tuple[ExecutionReport, RiskDecision]:
        decision = self.risk.check(order, snap, self.kill_switch)
        if not decision.approved:
            return ExecutionReport(status='rejected', filled_quantity=0, fill_price=None, fee=0, symbol=order.symbol, side=order.side, reason=decision.reason), decision
        return self.paper.execute(order, snap), decision

    def route_live_order(self, order: OrderRequest, snap: MarketSnapshot) -> tuple[ExecutionReport, RiskDecision]:
        decision = self.risk.check(order, snap, self.kill_switch)
        return self.live.execute(order, decision, self.kill_switch), decision


def decision_to_orders(action: Action, symbol: str, quantity: float, second_symbol: str | None = None) -> list[OrderRequest]:
    if action == 'HOLD':
        return []
    if action == 'BUY':
        return [OrderRequest(symbol, 'BUY', quantity)]
    if action == 'SELL':
        return [OrderRequest(symbol, 'SELL', quantity)]
    if action == 'LONG_SPREAD' and second_symbol:
        return [OrderRequest(symbol, 'BUY', quantity), OrderRequest(second_symbol, 'SELL', quantity)]
    if action == 'SHORT_SPREAD' and second_symbol:
        return [OrderRequest(symbol, 'SELL', quantity), OrderRequest(second_symbol, 'BUY', quantity)]
    if action == 'TARGET_ALLOCATION':
        side = 'BUY' if quantity >= 0 else 'SELL'
        return [OrderRequest(symbol, side, abs(quantity))]
    raise ValueError('invalid decision action')
