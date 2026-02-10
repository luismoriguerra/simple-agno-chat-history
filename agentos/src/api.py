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
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.instrumentation import log_workflow_event
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
# Dependency injection
# ---------------------------------------------------------------------------


def get_state_store(request: Request) -> StateStore:
    """FastAPI dependency that retrieves the StateStore from app state."""
    store: Optional[StateStore] = getattr(request.app.state, "state_store", None)
    if store is None:
        raise RuntimeError(
            "StateStore not initialized. "
            "Assign it to app.state.state_store during startup."
        )
    return store


StoreDep = Annotated[StateStore, Depends(get_state_store)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/runs", response_model=LaunchResponse)
def launch_run(req: LaunchRequest, store: StoreDep) -> LaunchResponse:
    """Launch a new workflow run.

    Supports idempotency: if a run with the same idempotency_key already
    exists, return the existing run instead of creating a new one.
    Uses an atomic create-or-get to handle concurrent requests safely.
    """
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

    result = store.create_or_get_by_idempotency(run)

    if result.created:
        log_workflow_event(
            "launch",
            {"company_name": req.company_name},
            run_id=result.run_state.run_id,
        )
        return LaunchResponse(
            run_id=result.run_state.run_id,
            status=result.run_state.status.value,
            message=f"Run launched for company '{req.company_name}'.",
        )

    return LaunchResponse(
        run_id=result.run_state.run_id,
        status=result.run_state.status.value,
        message="Run already exists (idempotent).",
    )


@router.get("/runs/{run_id}", response_model=RunStateResponse)
def get_run(run_id: str, store: StoreDep) -> RunStateResponse:
    """Get current state of a workflow run."""
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
def pause_run(run_id: str, store: StoreDep) -> dict:
    """Pause an active workflow run."""
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
    log_workflow_event("pause", {"reason": "Manual pause via API"}, run_id=run_id)
    return {"run_id": run_id, "status": "paused", "message": "Run paused."}


@router.post("/runs/{run_id}/resume")
def resume_run(run_id: str, req: ResumeRequest, store: StoreDep) -> dict:
    """Resume a paused or approval-waiting run."""
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
    log_workflow_event("resume", req.data, run_id=run_id)
    return {"run_id": run_id, "status": "running", "message": "Run resumed."}


@router.post("/webhooks/approval")
def receive_approval_webhook(payload: WebhookPayload, store: StoreDep) -> dict:
    """Receive external approval webhook and resume or fail the run.

    This endpoint is designed to be called by external systems (Slack bots,
    email links, admin dashboards) to approve or deny a pending action.
    """
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

    log_workflow_event(
        "approval_webhook",
        {"approved": payload.approved, "responder": payload.responder},
        run_id=payload.run_id,
    )

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


# ---------------------------------------------------------------------------
# Status enum helper
# ---------------------------------------------------------------------------

_VALID_STATUSES = {s.value for s in RunStatus}


@router.get("/runs")
def list_runs(
    store: StoreDep, status: Optional[str] = None
) -> list[RunStateResponse]:
    """List workflow runs, optionally filtered by status.

    When ``status`` is provided it is validated against ``RunStatus`` values
    and filtering is done at the database level.  Without a filter the
    endpoint returns only active (non-terminal) runs.
    """
    if status:
        if status not in _VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid status '{status}'. "
                    f"Valid values: {sorted(_VALID_STATUSES)}."
                ),
            )
        runs = store.list_by_status(RunStatus(status))
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
