"""
Unit tests for models and state management.

These tests validate:
- StepResult serialization/deserialization
- WorkflowEvent creation and context rendering
- RunState lifecycle (append, retry tracking)
- ProvisioningError contract
- StateStore CRUD operations (save, load, idempotency, filtering)
"""

import pytest

from src.models import (
    EventType,
    ProvisioningError,
    RunState,
    RunStatus,
    StepResult,
    StepStatus,
    WorkflowEvent,
    sanitize_slug,
)
from src.state import StateStore


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------


class TestStepResult:
    """Tests for the StepResult data contract."""

    def test_success_result_round_trip(self):
        result = StepResult(
            system="slack",
            status=StepStatus.SUCCESS,
            details="Slack provisioned for Acme: channel=#welcome-acme",
        )
        content = result.to_content()
        restored = StepResult.from_content(content)
        assert restored.system == "slack"
        assert restored.status == StepStatus.SUCCESS
        assert "Acme" in restored.details
        assert restored.retryable is False
        assert restored.attempt == 1

    def test_error_result_with_retry_info(self):
        result = StepResult(
            system="github",
            status=StepStatus.ERROR,
            details="Connection timeout",
            error_code="TIMEOUT",
            retryable=True,
            attempt=2,
        )
        assert result.retryable is True
        assert result.attempt == 2
        assert result.error_code == "TIMEOUT"

    def test_fail_result_non_retryable(self):
        result = StepResult(
            system="grants",
            status=StepStatus.FAIL,
            details="Invalid configuration",
            error_code="INVALID_CONFIG",
            retryable=False,
        )
        assert result.retryable is False
        assert result.status == StepStatus.FAIL


# ---------------------------------------------------------------------------
# WorkflowEvent
# ---------------------------------------------------------------------------


class TestWorkflowEvent:
    """Tests for WorkflowEvent creation and rendering."""

    def test_event_has_auto_id_and_timestamp(self):
        event = WorkflowEvent(
            event_type=EventType.USER_INPUT,
            data={"company_name": "Acme Corp"},
        )
        assert event.id is not None
        assert event.timestamp is not None

    def test_context_line_includes_step_name(self):
        event = WorkflowEvent(
            event_type=EventType.STEP_RESULT,
            step_name="Provision Slack",
            data={"status": "success"},
        )
        line = event.to_context_line()
        assert "step_result" in line
        assert "Provision Slack" in line
        assert "status: success" in line

    def test_context_line_without_step_name(self):
        event = WorkflowEvent(
            event_type=EventType.PAUSED,
            data={"reason": "manual"},
        )
        line = event.to_context_line()
        assert "<paused>" in line
        assert "reason: manual" in line


# ---------------------------------------------------------------------------
# RunState
# ---------------------------------------------------------------------------


class TestRunState:
    """Tests for the RunState model."""

    def test_new_run_defaults(self):
        run = RunState()
        assert run.status == RunStatus.RUNNING
        assert len(run.events) == 0
        assert run.run_id is not None

    def test_append_event_updates_timestamp(self):
        run = RunState()
        old_ts = run.updated_at
        event = WorkflowEvent(
            event_type=EventType.USER_INPUT,
            data={"company_name": "Test Co"},
        )
        run.append_event(event)
        assert len(run.events) == 1
        assert run.updated_at >= old_ts

    def test_retry_tracking(self):
        run = RunState()
        assert run.get_retry_count("Provision Slack") == 0
        assert run.increment_retry("Provision Slack") == 1
        assert run.increment_retry("Provision Slack") == 2
        assert run.get_retry_count("Provision Slack") == 2

    def test_to_context_renders_all_events(self):
        run = RunState()
        run.append_event(
            WorkflowEvent(
                event_type=EventType.USER_INPUT,
                data={"company_name": "Ctx Co"},
            ),
        )
        run.append_event(
            WorkflowEvent(
                event_type=EventType.STEP_RESULT,
                step_name="Provision Slack",
                data={"status": "success"},
            ),
        )
        ctx = run.to_context()
        assert "user_input" in ctx
        assert "step_result" in ctx


# ---------------------------------------------------------------------------
# ProvisioningError
# ---------------------------------------------------------------------------


class TestProvisioningError:
    """Tests for the ProvisioningError exception."""

    def test_error_attributes(self):
        err = ProvisioningError(
            message="Company name missing",
            system="slack",
            error_code="MISSING_COMPANY_NAME",
        )
        assert err.system == "slack"
        assert err.error_code == "MISSING_COMPANY_NAME"
        assert str(err) == "Company name missing"


# ---------------------------------------------------------------------------
# sanitize_slug
# ---------------------------------------------------------------------------


class TestSanitizeSlug:
    """Tests for the slug helper."""

    def test_simple_name(self):
        assert sanitize_slug("Acme") == "acme"

    def test_name_with_spaces(self):
        assert sanitize_slug("Acme Corp") == "acme-corp"

    def test_name_with_special_chars(self):
        assert sanitize_slug("Acme & Co. (US)") == "acme-co-us"

    def test_empty_string_fallback(self):
        assert sanitize_slug("") == "unknown"

    def test_whitespace_only_fallback(self):
        assert sanitize_slug("   ") == "unknown"


# ---------------------------------------------------------------------------
# StateStore
# ---------------------------------------------------------------------------


class TestStateStore:
    """Integration tests for the SQLAlchemy-backed StateStore."""

    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test_state.db"
        return StateStore(db_url=f"sqlite:///{db_path}")

    def test_save_and_load(self, store):
        run = RunState(company_name="Test Corp")
        run.append_event(
            WorkflowEvent(
                event_type=EventType.USER_INPUT,
                data={"company_name": "Test Corp"},
            ),
        )
        store.save(run)

        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.company_name == "Test Corp"
        assert len(loaded.events) == 1

    def test_idempotency_key_lookup(self, store):
        run = RunState(
            company_name="Idempotent Co",
            idempotency_key="unique-key-123",
        )
        store.save(run)

        found = store.find_by_idempotency_key("unique-key-123")
        assert found is not None
        assert found.run_id == run.run_id

    def test_idempotency_key_not_found(self, store):
        assert store.find_by_idempotency_key("nonexistent") is None

    def test_update_existing_record(self, store):
        run = RunState(company_name="Update Co")
        store.save(run)

        run.status = RunStatus.PAUSED
        run.append_event(
            WorkflowEvent(
                event_type=EventType.PAUSED,
                data={"reason": "test"},
            ),
        )
        store.save(run)

        loaded = store.load(run.run_id)
        assert loaded is not None
        assert loaded.status == RunStatus.PAUSED
        assert len(loaded.events) == 1

    def test_list_active_excludes_completed(self, store):
        run_active = RunState(company_name="Active1")
        run_paused = RunState(company_name="Active2", status=RunStatus.PAUSED)
        run_done = RunState(company_name="Done", status=RunStatus.COMPLETED)
        store.save(run_active)
        store.save(run_paused)
        store.save(run_done)

        active = store.list_active()
        active_ids = {r.run_id for r in active}
        assert run_active.run_id in active_ids
        assert run_paused.run_id in active_ids
        assert run_done.run_id not in active_ids

    def test_load_nonexistent_returns_none(self, store):
        assert store.load("does-not-exist") is None

    def test_find_by_session(self, store):
        run1 = RunState(company_name="S1", session_id="sess-a")
        run2 = RunState(company_name="S2", session_id="sess-a")
        run3 = RunState(company_name="S3", session_id="sess-b")
        store.save(run1)
        store.save(run2)
        store.save(run3)

        results = store.find_by_session("sess-a")
        assert len(results) == 2
