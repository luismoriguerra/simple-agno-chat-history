"""
api.py

FastAPI router with explicit lifecycle endpoints for workflow runs:
launch, pause, resume, query, and webhook-based approval.

Factors addressed:
  6 - Launch/Pause/Resume with simple APIs
  7 - Contact humans with tool calls (approval webhook receiver)
 11 - Trigger from anywhere (REST surface for external systems)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models import EventType, RunState, RunStatus, WorkflowEvent
from src.state import StateStore

router = APIRouter(prefix="/api/v1", tags=["workflow"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class LaunchRequest(BaseModel):
    company_name: str
    session_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class LaunchResponse(BaseModel):
    run_id: str
    status: str
    message: str


class ResumeRequest(BaseModel):
    event_type: str = "approval_received"
    data: dict = {}


class RunStateResponse(BaseModel):
    run_id: str
    status: str
    company_name: Optional[str]
    event_count: int
    created_at: str
    updated_at: str


class WebhookPayload(BaseModel):
    run_id: str
    approved: bool
    responder: Optional[str] = None
    comment: Optional[str] = None


# ---------------------------------------------------------------------------
# State store singleton (injected from main.py)
# ---------------------------------------------------------------------------

_store: Optional[StateStore] = None


def set_state_store(store: StateStore) -> None:
    """Inject the state store singleton used by all endpoints."""
    global _store
    _store = store


def _get_store() -> StateStore:
    if _store is None:
        raise RuntimeError("StateStore not initialized. Call set_state_store() first.")
    return _store


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/runs", response_model=LaunchResponse)
def launch_run(req: LaunchRequest) -> LaunchResponse:
    """Launch a new workflow run.

    Supports idempotency: if a run with the same idempotency_key already
    exists, return the existing run instead of creating a new one.
    """
    store = _get_store()

    # Idempotency check
    if req.idempotency_key:
        existing = store.find_by_idempotency_key(req.idempotency_key)
        if existing:
            return LaunchResponse(
                run_id=existing.run_id,
                status=existing.status.value,
                message="Run already exists (idempotent).",
            )

    run = RunState(
        session_id=req.session_id or str(uuid.uuid4()),
        company_name=req.company_name,
        idempotency_key=req.idempotency_key,
    )
    run.append_event(
        WorkflowEvent(
            event_type=EventType.USER_INPUT,
            data={"company_name": req.company_name},
        )
    )
    store.save(run)

    return LaunchResponse(
        run_id=run.run_id,
        status=run.status.value,
        message=f"Run launched for company '{req.company_name}'.",
    )


@router.get("/runs/{run_id}", response_model=RunStateResponse)
def get_run(run_id: str) -> RunStateResponse:
    """Get current state of a workflow run."""
    store = _get_store()
    run = store.load(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return RunStateResponse(
        run_id=run.run_id,
        status=run.status.value,
        company_name=run.company_name,
        event_count=len(run.events),
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
    )


@router.post("/runs/{run_id}/pause")
def pause_run(run_id: str) -> dict:
    """Pause an active workflow run."""
    store = _get_store()
    run = store.load(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause run in status '{run.status.value}'.",
        )

    run.status = RunStatus.PAUSED
    run.append_event(
        WorkflowEvent(
            event_type=EventType.PAUSED,
            data={"reason": "Manual pause via API"},
        )
    )
    store.save(run)
    return {"run_id": run_id, "status": "paused", "message": "Run paused."}


@router.post("/runs/{run_id}/resume")
def resume_run(run_id: str, req: ResumeRequest) -> dict:
    """Resume a paused or approval-waiting run."""
    store = _get_store()
    run = store.load(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status not in (RunStatus.PAUSED, RunStatus.AWAITING_APPROVAL):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot resume run in status '{run.status.value}'.",
        )

    run.status = RunStatus.RUNNING
    run.append_event(
        WorkflowEvent(
            event_type=EventType.RESUMED,
            data=req.data,
        )
    )
    store.save(run)
    return {"run_id": run_id, "status": "running", "message": "Run resumed."}


@router.post("/webhooks/approval")
def receive_approval_webhook(payload: WebhookPayload) -> dict:
    """Receive external approval webhook and resume or fail the run.

    This endpoint is designed to be called by external systems (Slack bots,
    email links, admin dashboards) to approve or deny a pending action.
    """
    store = _get_store()
    run = store.load(payload.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status != RunStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Run is not awaiting approval (status: {run.status.value}).",
        )

    run.append_event(
        WorkflowEvent(
            event_type=EventType.APPROVAL_RECEIVED,
            data={
                "approved": payload.approved,
                "responder": payload.responder,
                "comment": payload.comment,
            },
        )
    )
    run.status = RunStatus.RUNNING if payload.approved else RunStatus.FAILED
    store.save(run)

    return {
        "run_id": payload.run_id,
        "approved": payload.approved,
        "status": run.status.value,
        "message": (
            "Approval received."
            if payload.approved
            else "Approval denied, run marked as failed."
        ),
    }


@router.get("/runs")
def list_runs(status: Optional[str] = None) -> list[RunStateResponse]:
    """List workflow runs, optionally filtered by status."""
    store = _get_store()
    if status:
        runs = store.list_all()
        runs = [r for r in runs if r.status.value == status]
    else:
        runs = store.list_active()

    return [
        RunStateResponse(
            run_id=r.run_id,
            status=r.status.value,
            company_name=r.company_name,
            event_count=len(r.events),
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in runs
    ]
