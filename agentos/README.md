# AgentOS -- 12-Factor Onboarding Agent

An onboarding agent system built with [Agno](https://docs.agno.com) and aligned with the [12-Factor Agents](https://github.com/humanlayer/12-factor-agents) principles for production-grade LLM applications.

## What it does

Onboards companies into four enterprise systems -- **Slack**, **GitHub**, **Newsletter**, and **Grants** -- using a supervisor team that orchestrates a parallel provisioning workflow, validates results with structured contracts, and supports human-in-the-loop approval and escalation.

## Architecture

```
                        +-------------------+
   User / Webhook  ---> |  FastAPI (main.py) |
                        +-------------------+
                           |            |
              AgentOS Chat |            | Lifecycle API (/api/v1)
                           v            v
                  +---------------+  +-----------+
                  | Supervisor    |  | StateStore |
                  | Team          |  | (state.py) |
                  +---------------+  +-----------+
                        |
            +-----------+-----------+
            |                       |
    +----------------+     +------------------+
    | Planner Agent  |     | Workflow (Agno)  |
    +----------------+     +------------------+
                                |
                    +-----------+-----------+-----------+
                    |           |           |           |
                  Slack     GitHub    Newsletter    Grants
               (provisioner) (provisioner) (provisioner) (provisioner)
                    |           |           |           |
                    +-----------+-----------+-----------+
                                |
                        +----------------+
                        | Reporter Agent |
                        +----------------+
```

### Key modules

| Module | Purpose |
|--------|---------|
| `src/models.py` | Canonical data models -- StepResult, WorkflowEvent, RunState |
| `src/provisioners.py` | Deterministic step executors with input validation |
| `src/workflow.py` | Agno Workflow with parallel steps and reporter |
| `src/team.py` | Supervisor Team with human-in-the-loop tools |
| `src/human_tools.py` | `request_approval` and `escalate_to_human` tool functions |
| `src/state.py` | SQLAlchemy-backed event state store (SQLite / Postgres) |
| `src/api.py` | Lifecycle REST API (launch, pause, resume, webhook) |
| `src/config.py` | Environment-driven DB and model configuration |
| `src/instrumentation.py` | LangWatch + structured event logging |
| `src/main.py` | Application entry-point, wires everything together |

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- AWS credentials for Bedrock (Claude)

### Local development (SQLite)

```bash
# Clone and enter the project
cd agentos

# Install dependencies
uv sync

# Set environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-2

# Start the server
make dev
# or: uv run fastapi dev src/main.py
```

Then open AgentUI and connect to `http://localhost:7777`.

### Production (PostgreSQL)

```bash
# Install with Postgres support
uv sync --extra postgres

# Set production database
export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname

# Start
uv run fastapi run src/main.py
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | _(empty -- SQLite)_ | PostgreSQL connection string for production |
| `SQLITE_DB_PATH` | `tmp/agentos.db` | SQLite file path for local dev |
| `AGENT_MODEL` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Bedrock model ID |
| `MAX_STEP_RETRIES` | `3` | Max retries before escalation |
| `AWS_ACCESS_KEY_ID` | _(required)_ | AWS credential |
| `AWS_SECRET_ACCESS_KEY` | _(required)_ | AWS credential |
| `AWS_DEFAULT_REGION` | _(required)_ | AWS region (e.g., `us-east-2`) |

## API Contracts

### Lifecycle API (`/api/v1`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/runs` | Launch a new workflow run |
| `GET` | `/api/v1/runs` | List active runs (optional `?status=` filter) |
| `GET` | `/api/v1/runs/{run_id}` | Get run state |
| `POST` | `/api/v1/runs/{run_id}/pause` | Pause a running run |
| `POST` | `/api/v1/runs/{run_id}/resume` | Resume a paused/awaiting run |
| `POST` | `/api/v1/webhooks/approval` | Receive external approval |

#### Launch a run

```bash
curl -X POST http://localhost:7777/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Acme Corp", "idempotency_key": "acme-001"}'
```

#### Approve via webhook

```bash
curl -X POST http://localhost:7777/api/v1/webhooks/approval \
  -H "Content-Type: application/json" \
  -d '{"run_id": "...", "approved": true, "responder": "admin@example.com"}'
```

### Step result schema

Every provisioning step returns a JSON object with this shape:

```json
{
  "system": "slack",
  "status": "success",
  "details": "Slack provisioned for Acme Corp: channel=#welcome-acme-corp",
  "error_code": null,
  "retryable": false,
  "attempt": 1
}
```

Possible `status` values: `success`, `fail`, `error`, `pending`, `skipped`.

## Testing

```bash
# Unit + integration tests (no LLM calls)
make test-unit
# or: uv run python -m pytest tests/test_state_model.py tests/test_control_flow.py -v

# Scenario tests (requires AWS/Bedrock credentials)
make test
# or: uv run python -m pytest tests/ -v -m agent_test
```

## 12-Factor Agents Coverage Matrix

| # | Factor | Status | Implementation |
|---|--------|--------|----------------|
| 1 | Natural language to tool calls | Implemented | Team invokes workflow tools; provisioners return structured JSON |
| 2 | Own your prompts | Implemented | All prompts are explicit in `team.py` and `workflow.py` |
| 3 | Own your context window | Partial | Session history via Agno; `RunState.to_context()` for event threads |
| 4 | Tools are structured outputs | Implemented | `StepResult` schema with typed fields |
| 5 | Unify execution + business state | Implemented | `RunState` event-sourced thread model |
| 6 | Launch/Pause/Resume APIs | Implemented | REST endpoints with idempotency |
| 7 | Contact humans with tool calls | Implemented | `request_approval` and `escalate_to_human` tools |
| 8 | Own your control flow | Implemented | Retry policy, escalation thresholds, deterministic guards |
| 9 | Compact errors into context | Implemented | Structured error results with `retryable` and `attempt` fields |
| 10 | Small, focused agents | Implemented | Separate planner, reporter roles with narrow scope |
| 11 | Trigger from anywhere | Implemented | REST API + webhook endpoint for external systems |
| 12 | Stateless reducer | Implemented | `RunState` is fully serializable, event-sourced, replay-safe |

## Operational Runbook

### Run is stuck in `awaiting_approval`

1. Check the run state: `GET /api/v1/runs/{run_id}`
2. Review the events to understand what approval was requested
3. Send approval or denial: `POST /api/v1/webhooks/approval`

### Provisioning fails repeatedly

1. The agent will retry up to `MAX_STEP_RETRIES` times (default: 3)
2. After exhausting retries, it calls `escalate_to_human`
3. Check the structured error in the step result for `error_code` and `retryable` fields

### Switching to production database

1. Set `DATABASE_URL` to your PostgreSQL connection string
2. Install Postgres dependencies: `uv sync --extra postgres`
3. The state store and Agno sessions will both use Postgres automatically
4. Tables are created automatically on first startup

### Viewing audit trail

- LangWatch traces are captured automatically via `instrumentation.py`
- Structured workflow events are logged to `agentos.events` logger
- Run events are persisted in the `workflow_runs` table

## License

Private -- internal use only.
