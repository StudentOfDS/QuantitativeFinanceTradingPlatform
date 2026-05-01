# Enterprise Quantitative Intelligence Platform (EQIP)

EQIP is a **professional-grade but compact** quantitative finance platform designed for real workflows:
research, portfolio/risk analytics, backtesting, ML/RL-assisted diagnostics, paper trading, and exportable reports.

This repository is being developed in **phases** to keep quality high and avoid placeholder code.

---

## Product Scope (V1 Target)

V1 is complete when a user can:

1. Run a FastAPI backend and Next.js frontend locally.
2. Ingest data via manual input, CSV/Excel/parquet/trusted-pickle, or market-data fetch.
3. Validate and preview cleaned data before running models.
4. Run a complete research report with TVM, portfolio, risk, option, bond, credit, and operational outputs.
5. Run at least one realistic cost-aware backtest.
6. Inspect ML probability + feature importance and RL allocation advice (simulation mode).
7. Run paper-trading ledger actions (no real broker money).
8. Export JSON/CSV/Excel reports.
9. Pass the validation script.

Out of scope for early V1 (unless fully implemented/tested):
- Production live broker execution
- Multi-user auth & cloud tenancy
- TimescaleDB and advanced distributed infra
- Mandatory Zipline/QuantLib installs

---

## Architecture

### Frontend
- **Next.js + TypeScript + Tailwind CSS**
- UI/form stack: **React Hook Form + Zod**
- Server-state: **TanStack Query**
- Charts: **Recharts or Plotly.js**
- Finance-terminal style pages:
  - Data Input
  - Research Report
  - Backtesting
  - Portfolio & Risk
  - Options & Bonds
  - Corporate/Credit/Operational Risk
  - ML/RL Diagnostics
  - Paper Trading Desk
  - History/Exports

### Backend
- **FastAPI** owns computation, validation, reporting, backtesting, ML/RL, storage, and execution logic.
- Core module layout (compact, responsibility-driven):
  - `backend/main.py`
  - `backend/config.py`
  - `backend/data.py`
  - `backend/quant.py`
  - `backend/backtest.py`
  - `backend/intelligence.py`
  - `backend/execution.py`
  - `backend/storage.py`
  - `backend/reports.py`
  - `backend/tests/`
  - `backend/scripts/validate.py`

### Law of Demeter
- Frontend -> typed API client
- API routes -> service layer
- Services -> data/quant/storage interfaces
- No cross-layer attribute spelunking

---

## Optional Dependency Policy

Heavy quant/event dependencies are optional and must fail gracefully.

If unavailable:
- API should return an explicit availability message (e.g., `QuantLib unavailable`, `Zipline unavailable`).
- Frontend should disable relevant controls with clear tooltips (e.g., `Install QuantLib/Zipline to enable this feature`).
- Core app remains usable.

---

## Data Input & Validation Contract

All data ingestion paths (manual, file, provider) must flow through one canonical adapter/engine and emit:

- Raw rows count
- Cleaned rows count
- Detected columns
- Missing required columns
- Duplicate timestamps
- Invalid OHLC rules (e.g., `High < Low`)
- Non-positive prices
- Missing-value counts
- Date range
- Warnings
- Valid flag
- JSON-safe preview

Pickle inputs are allowed only with explicit trusted-local confirmation and warning text.

---

## Storage & Precision Strategy

- Local default: SQLite (`WAL` mode)
- DB abstraction: SQLAlchemy ORM + Alembic migrations
- Future-ready: PostgreSQL without rewriting quant/business logic
- Precision policy:
  - Floating metrics: `float` where acceptable
  - Ledger/cash/fees/notional/P&L: `Decimal` in business logic and `NUMERIC` in DB

Transactional integrity is mandatory: no partial writes for trades, ledger updates, reports, or audits.

---

## Quant Coverage (Syllabus Backbone)

EQIP must support practical implementations of:

- TVM, NPV/IRR, DDM (single/multi-stage), WACC helpers, DSCR/ICR
- Markowitz portfolio analytics + optimization (and optional skfolio enhancements)
- CAPM/factor diagnostics and risk-adjusted performance metrics
- Forwards/futures no-arbitrage logic and options parity
- CRR binomial pricing (European/American)
- BSM pricing + Greeks + implied vol edge cases
- Brownian/GBM/OU + Monte Carlo engines
- Bond pricing, YTM, duration, convexity, yield-curve utilities
- VaR/CVaR (historical/parametric/MC), drawdown, stress/scenario analysis
- Credit risk (PD/LGD/EAD/EL/UL/Z-score/transition simulation)
- Operational risk (Poisson/lognormal LDA/AMA, VaR/ES/capital)

---

## Backtesting, ML/RL, and Execution Guardrails

### Backtesting
- One-bar delayed execution
- Transaction cost + slippage + turnover accounting
- Benchmark comparison
- Seedable randomness
- Metrics: CAGR, Sharpe, Sortino, Calmar, max drawdown, volatility, turnover, win/loss stats, exposure, costs

### ML/RL
- ML first model: Random Forest with no-leakage controls and walk-forward style validation
- RL: transparent Q-learning sizing helper (bounded action space)
- ML/RL never directly place live trades

### Execution
- Separate research simulation, paper trading, and live trading
- Live trading disabled by default and explicitly gated via env + risk controls
- Broker adapters must implement explicit interface methods and remain optional

---

## Security & Observability Requirements

Security:
- Upload extension and size checks
- MIME/content sanity checks where possible
- Safe temp storage and path traversal prevention
- `.env`-only secrets handling
- Never log broker secrets
- Restrictive CORS

Observability:
- Persist/audit major events: ingestion, validation, reports, backtests, ML/RL decisions, orders, risk rejections, exports, exceptions
- Keep logs useful but non-sensitive

---

## Dependency Profiles

Planned install profiles:
- `base`: core API/UI/data/quant/report/backtest essentials
- `ml`: adds sklearn and ML dependencies
- `quant`: adds optional advanced quant libs (QuantLib/skfolio/arch where installable)
- `full`: all optional stacks including event-driven backtesting backend (if available)

Validation/CI should require base profile; heavy jobs may be manual or allowed-failure initially.

---

## Delivery Approach

To prevent low-quality bulk scaffolding, implementation proceeds in phases:

1. Skeleton + data input/validation
2. Quant formulas/services
3. Backtesting
4. ML
5. RL
6. Paper trading + ledger
7. Optional broker/PostgreSQL/advanced integrations
8. UI/export/deployment polish

No pseudo-code, placeholder methods, dead routes, or fake integrations are accepted.

---

## Environment Configuration

See `.env.example` for baseline settings.

