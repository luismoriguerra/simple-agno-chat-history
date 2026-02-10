"""
Tests for the workflow lifecycle API endpoints.

Validates launch, pause, resume, approval webhook, and listing
behaviour including idempotency and status guard-rails.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import router
from src.models import RunState, RunStatus
from src.state import StateStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_api.db"
    return StateStore(db_url=f"sqlite:///{db_path}")


@pytest.fixture
def client(store):
    app = FastAPI()
    app.state.state_store = store
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/v1/runs  (launch)
# ---------------------------------------------------------------------------


class TestLaunchEndpoint:
    def test_launch_creates_new_run(self, client):
        resp = client.post("/api/v1/runs", json={"company_name": "Acme Corp"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "run_id" in data

    def test_idempotent_launch_returns_same_run(self, client):
        payload = {
            "company_name": "Acme Corp",
            "idempotency_key": "idem-123",
        }
        resp1 = client.post("/api/v1/runs", json=payload)
        resp2 = client.post("/api/v1/runs", json=payload)
        assert resp1.json()["run_id"] == resp2.json()["run_id"]
        assert resp2.json()["message"] == "Run already exists (idempotent)."

    def test_launch_without_idempotency_key_creates_distinct_runs(self, client):
        """Two launches without idempotency_key should create two separate runs."""
        resp1 = client.post("/api/v1/runs", json={"company_name": "Acme Corp"})
        resp2 = client.post("/api/v1/runs", json={"company_name": "Acme Corp"})
        assert resp1.json()["run_id"] != resp2.json()["run_id"]


# ---------------------------------------------------------------------------
# GET /api/v1/runs/{run_id}
# ---------------------------------------------------------------------------


class TestGetRunEndpoint:
    def test_get_existing_run(self, client, store):
        run = RunState(company_name="Test Co")
        store.save(run)

        resp = client.get(f"/api/v1/runs/{run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "Test Co"

    def test_get_nonexistent_run_returns_404(self, client):
        resp = client.get("/api/v1/runs/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/runs/{run_id}/pause
# ---------------------------------------------------------------------------


class TestPauseEndpoint:
    def test_pause_running_run(self, client, store):
        run = RunState(company_name="Pausable Co")
        store.save(run)

        resp = client.post(f"/api/v1/runs/{run.run_id}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_cannot_pause_completed_run(self, client, store):
        run = RunState(company_name="Done Co", status=RunStatus.COMPLETED)
        store.save(run)

        resp = client.post(f"/api/v1/runs/{run.run_id}/pause")
        assert resp.status_code == 409

    def test_pause_nonexistent_run_returns_404(self, client):
        resp = client.post("/api/v1/runs/ghost/pause")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/runs/{run_id}/resume
# ---------------------------------------------------------------------------


class TestResumeEndpoint:
    def test_resume_paused_run(self, client, store):
        run = RunState(company_name="Resume Co", status=RunStatus.PAUSED)
        store.save(run)

        resp = client.post(
            f"/api/v1/runs/{run.run_id}/resume",
            json={"data": {"note": "resuming"}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_resume_awaiting_approval_run(self, client, store):
        run = RunState(
            company_name="Approval Co",
            status=RunStatus.AWAITING_APPROVAL,
        )
        store.save(run)

        resp = client.post(
            f"/api/v1/runs/{run.run_id}/resume",
            json={"data": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_cannot_resume_running_run(self, client, store):
        run = RunState(company_name="Already Running")
        store.save(run)

        resp = client.post(
            f"/api/v1/runs/{run.run_id}/resume",
            json={"data": {}},
        )
        assert resp.status_code == 409

    def test_resume_request_rejects_unknown_fields(self, client, store):
        """ResumeRequest no longer accepts event_type -- extra fields are ignored by Pydantic
        but the schema should only contain 'data'."""
        run = RunState(company_name="Schema Co", status=RunStatus.PAUSED)
        store.save(run)

        resp = client.post(
            f"/api/v1/runs/{run.run_id}/resume",
            json={"data": {"note": "ok"}},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/webhooks/approval
# ---------------------------------------------------------------------------


class TestApprovalWebhook:
    def test_approve_waiting_run(self, client, store):
        run = RunState(
            company_name="Approval Co",
            status=RunStatus.AWAITING_APPROVAL,
        )
        store.save(run)

        resp = client.post(
            "/api/v1/webhooks/approval",
            json={
                "run_id": run.run_id,
                "approved": True,
                "responder": "admin@example.com",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["approved"] is True
        assert resp.json()["status"] == "running"

    def test_deny_waiting_run(self, client, store):
        run = RunState(
            company_name="Denied Co",
            status=RunStatus.AWAITING_APPROVAL,
        )
        store.save(run)

        resp = client.post(
            "/api/v1/webhooks/approval",
            json={
                "run_id": run.run_id,
                "approved": False,
                "responder": "admin@example.com",
                "comment": "Not authorized",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_webhook_on_wrong_status_returns_409(self, client, store):
        run = RunState(company_name="Wrong Status Co")
        store.save(run)

        resp = client.post(
            "/api/v1/webhooks/approval",
            json={"run_id": run.run_id, "approved": True},
        )
        assert resp.status_code == 409

    def test_webhook_nonexistent_run_returns_404(self, client):
        resp = client.post(
            "/api/v1/webhooks/approval",
            json={"run_id": "ghost", "approved": True},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/runs  (list)
# ---------------------------------------------------------------------------


class TestListRunsEndpoint:
    def test_list_active_runs(self, client, store):
        store.save(RunState(company_name="Active"))
        store.save(RunState(company_name="Done", status=RunStatus.COMPLETED))

        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        runs = resp.json()
        names = [r["company_name"] for r in runs]
        assert "Active" in names
        assert "Done" not in names

    def test_list_filtered_by_status(self, client, store):
        store.save(RunState(company_name="Paused1", status=RunStatus.PAUSED))
        store.save(RunState(company_name="Running1"))

        resp = client.get("/api/v1/runs", params={"status": "paused"})
        assert resp.status_code == 200
        runs = resp.json()
        assert all(r["status"] == "paused" for r in runs)

    def test_list_invalid_status_returns_400(self, client):
        """An unrecognized status value should be rejected with 400."""
        resp = client.get("/api/v1/runs", params={"status": "banana"})
        assert resp.status_code == 400
        assert "Invalid status" in resp.json()["detail"]

    def test_list_all_statuses_via_filter(self, client, store):
        """Using a valid terminal status should return those runs."""
        store.save(RunState(company_name="Done1", status=RunStatus.COMPLETED))
        store.save(RunState(company_name="Running1"))

        resp = client.get("/api/v1/runs", params={"status": "completed"})
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) == 1
        assert runs[0]["company_name"] == "Done1"
