"""
state.py

Persistence layer for workflow run state using SQLAlchemy.
Works with both SQLite (local dev) and PostgreSQL (production).

Factors addressed:
  5 - Unify execution state and business state
  6 - Launch/Pause/Resume with simple APIs (state persistence)
 12 - Stateless reducer (event-sourced RunState is trivially serializable)
"""

import logging
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.models import RunState, RunStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


class RunStateRecord(Base):
    """SQLAlchemy model for persisting workflow run states."""

    __tablename__ = "workflow_runs"

    run_id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True, index=True)
    company_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="running")
    state_json = Column(Text, nullable=False)
    idempotency_key = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


# ---------------------------------------------------------------------------
# State store
# ---------------------------------------------------------------------------


class StateStore:
    """Persistence layer for workflow run state.

    Backed by SQLAlchemy so the same code works for SQLite and Postgres.
    """

    def __init__(self, db_url: str = "sqlite:///tmp/agentos_state.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine)
        logger.info("StateStore initialized with %s", db_url)

    # -- write -----------------------------------------------------------------

    def save(self, run_state: RunState) -> None:
        """Upsert a RunState into the store."""
        with self._session_factory() as session:
            record = session.get(RunStateRecord, run_state.run_id)
            state_json = run_state.model_dump_json()
            if record:
                record.status = run_state.status.value
                record.state_json = state_json
                record.company_name = run_state.company_name
                record.updated_at = run_state.updated_at
            else:
                record = RunStateRecord(
                    run_id=run_state.run_id,
                    session_id=run_state.session_id,
                    company_name=run_state.company_name,
                    status=run_state.status.value,
                    state_json=state_json,
                    idempotency_key=run_state.idempotency_key,
                    created_at=run_state.created_at,
                    updated_at=run_state.updated_at,
                )
                session.add(record)
            session.commit()

    # -- read ------------------------------------------------------------------

    def load(self, run_id: str) -> Optional[RunState]:
        """Load a RunState by its run_id."""
        with self._session_factory() as session:
            record = session.get(RunStateRecord, run_id)
            if record is None:
                return None
            return RunState.model_validate_json(record.state_json)

    def find_by_idempotency_key(self, key: str) -> Optional[RunState]:
        """Find a RunState by its idempotency key."""
        with self._session_factory() as session:
            record = (
                session.query(RunStateRecord)
                .filter_by(idempotency_key=key)
                .first()
            )
            if record is None:
                return None
            return RunState.model_validate_json(record.state_json)

    def find_by_session(self, session_id: str) -> list[RunState]:
        """Find all RunStates associated with a session."""
        with self._session_factory() as db_session:
            records = (
                db_session.query(RunStateRecord)
                .filter_by(session_id=session_id)
                .all()
            )
            return [RunState.model_validate_json(r.state_json) for r in records]

    def list_active(self) -> list[RunState]:
        """List all runs that are not completed or failed."""
        active_statuses = [
            RunStatus.RUNNING.value,
            RunStatus.PAUSED.value,
            RunStatus.AWAITING_APPROVAL.value,
        ]
        with self._session_factory() as session:
            records = (
                session.query(RunStateRecord)
                .filter(RunStateRecord.status.in_(active_statuses))
                .all()
            )
            return [RunState.model_validate_json(r.state_json) for r in records]

    def list_all(self) -> list[RunState]:
        """List all runs regardless of status."""
        with self._session_factory() as session:
            records = session.query(RunStateRecord).all()
            return [RunState.model_validate_json(r.state_json) for r in records]
