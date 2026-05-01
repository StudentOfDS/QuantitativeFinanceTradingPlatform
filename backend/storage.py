from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, create_engine, select
from sqlalchemy.orm import Session, declarative_base

from backend.config import settings

Base = declarative_base()
engine = create_engine(settings.database_url, future=True)


class ReportRun(Base):
    __tablename__ = 'report_runs'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)


class BacktestRun(Base):
    __tablename__ = 'backtest_runs'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)




class ModelValidation(Base):
    __tablename__ = 'model_validations'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False)




class OrderRow(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)

class ExecutionReportRow(Base):
    __tablename__ = 'execution_reports'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)

class PositionRow(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)

class PortfolioSnapshotRow(Base):
    __tablename__ = 'portfolio_snapshots'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)

class LedgerEntryRow(Base):
    __tablename__ = 'ledger_entries'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)

class ExecutionAuditEventRow(Base):
    __tablename__ = 'execution_audit_events'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_json = Column(Text, nullable=False)


def initialize_storage() -> None:
    Base.metadata.create_all(engine)


def record_report_run(payload: dict) -> int:
    with Session(engine) as session, session.begin():
        row = ReportRun(payload_json=json.dumps(payload, default=str))
        session.add(row)
        session.flush()
        return int(row.id)


def record_backtest_run(payload: dict) -> int:
    with Session(engine) as session, session.begin():
        row = BacktestRun(payload_json=json.dumps(payload, default=str))
        session.add(row)
        session.flush()
        return int(row.id)


def record_audit_event(event_type: str, payload: dict) -> int:
    with Session(engine) as session, session.begin():
        row = AuditEvent(event_type=event_type, payload_json=json.dumps(payload, default=str))
        session.add(row)
        session.flush()
        return int(row.id)



def record_model_validation(payload: dict) -> int:
    with Session(engine) as session, session.begin():
        row = ModelValidation(payload_json=json.dumps(payload, default=str))
        session.add(row)
        session.flush()
        return int(row.id)


def list_recent_reports(limit: int = 20) -> list[dict]:
    with Session(engine) as session:
        rows = session.execute(select(ReportRun).order_by(ReportRun.id.desc()).limit(limit)).scalars().all()
        out = []
        for r in rows:
            payload = json.loads(r.payload_json)
            out.append({'id': r.id, 'created_at': r.created_at.isoformat(), 'metadata': payload.get('metadata', {})})
        return out


def record_execution_bundle(order_payload: dict, report_payload: dict, position_payload: dict, snapshot_payload: dict, ledger_payload: dict, audit_payload: dict) -> int:
    with Session(engine) as session, session.begin():
        o=OrderRow(payload_json=json.dumps(order_payload, default=str)); session.add(o)
        r=ExecutionReportRow(payload_json=json.dumps(report_payload, default=str)); session.add(r)
        p=PositionRow(payload_json=json.dumps(position_payload, default=str)); session.add(p)
        s=PortfolioSnapshotRow(payload_json=json.dumps(snapshot_payload, default=str)); session.add(s)
        l=LedgerEntryRow(payload_json=json.dumps(ledger_payload, default=str)); session.add(l)
        a=ExecutionAuditEventRow(payload_json=json.dumps(audit_payload, default=str)); session.add(a)
        session.flush(); return int(r.id)


def list_recent_execution_audits(limit: int = 20) -> list[dict]:
    with Session(engine) as session:
        rows = session.execute(select(ExecutionAuditEventRow).order_by(ExecutionAuditEventRow.id.desc()).limit(limit)).scalars().all()
        return [{'id': r.id, 'created_at': r.created_at.isoformat(), 'payload': json.loads(r.payload_json)} for r in rows]
