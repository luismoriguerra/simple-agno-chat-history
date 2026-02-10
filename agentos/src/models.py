"""
models.py

Canonical data models for the onboarding agent system.
Provides structured contracts for step results, workflow events,
and run state management.

Factors addressed:
  4 - Tools are structured outputs
  5 - Unify execution state and business state
 12 - Stateless reducer (RunState as event-sourced thread)
"""

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Step result contracts  (Factor 4)
# ---------------------------------------------------------------------------


class StepStatus(str, Enum):
    """Canonical status for a provisioning step."""

    SUCCESS = "success"
    FAIL = "fail"
    ERROR = "error"
    PENDING = "pending"
    SKIPPED = "skipped"


class StepResult(BaseModel):
    """Structured output for a single provisioning step."""

    system: str
    status: StepStatus
    details: str
    error_code: Optional[str] = None
    retryable: bool = False
    attempt: int = 1

    def to_content(self) -> str:
        """Serialize to JSON string for StepOutput content."""
        return self.model_dump_json()

    @classmethod
    def from_content(cls, content: str) -> "StepResult":
        """Deserialize from JSON string."""
        return cls.model_validate_json(content)


class ProvisioningError(Exception):
    """Raised when provisioning input is invalid or a step fails."""

    def __init__(
        self,
        message: str,
        system: str = "unknown",
        error_code: str = "INVALID_INPUT",
    ):
        self.system = system
        self.error_code = error_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Workflow event model  (Factor 5 + Factor 12)
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Types of events in a workflow run thread."""

    USER_INPUT = "user_input"
    STEP_SELECTED = "step_selected"
    STEP_RESULT = "step_result"
    STEP_ERROR = "step_error"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECEIVED = "approval_received"
    HUMAN_ESCALATION = "human_escalation"
    PAUSED = "paused"
    RESUMED = "resumed"
    FINALIZED = "finalized"
    ERROR_COMPACTED = "error_compacted"


class WorkflowEvent(BaseModel):
    """A single event in a workflow run thread."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    data: dict[str, Any] = Field(default_factory=dict)
    step_name: Optional[str] = None

    def to_context_line(self) -> str:
        """Render this event as a compact context line for the LLM."""
        parts = [f"<{self.event_type.value}>"]
        if self.step_name:
            parts.append(f"step: {self.step_name}")
        for key, value in self.data.items():
            parts.append(f"{key}: {value}")
        parts.append(f"</{self.event_type.value}>")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Run state  (Factor 5 + Factor 6 + Factor 12)
# ---------------------------------------------------------------------------


class RunStatus(str, Enum):
    """Status of a workflow run."""

    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class RunState(BaseModel):
    """Complete state of a single workflow run -- the 'thread'.

    This is the single source of truth for both execution state and
    business state.  All transitions are captured as WorkflowEvents
    so the run can be inspected, resumed, or replayed.
    """

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    company_name: Optional[str] = None
    status: RunStatus = RunStatus.RUNNING
    events: list[WorkflowEvent] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    retry_counts: dict[str, int] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None

    def append_event(self, event: WorkflowEvent) -> None:
        """Append an event and update the timestamp."""
        self.events.append(event)
        self.updated_at = datetime.now(timezone.utc)

    def to_context(self) -> str:
        """Build a compact context string from all events."""
        return "\n\n".join(e.to_context_line() for e in self.events)

    def get_step_results(self) -> list[StepResult]:
        """Extract all step results from events."""
        results: list[StepResult] = []
        for event in self.events:
            if event.event_type == EventType.STEP_RESULT and "result" in event.data:
                try:
                    results.append(StepResult.model_validate(event.data["result"]))
                except Exception:
                    pass
        return results

    def get_retry_count(self, step_name: str) -> int:
        """Get the current retry count for a step."""
        return self.retry_counts.get(step_name, 0)

    def increment_retry(self, step_name: str) -> int:
        """Increment and return the retry count for a step."""
        count = self.retry_counts.get(step_name, 0) + 1
        self.retry_counts[step_name] = count
        return count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sanitize_slug(company: str) -> str:
    """Create a URL-safe slug from a company name."""
    slug = company.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unknown"
