"""
main.py

Application entry-point.  Wires up AgentOS, the workflow lifecycle API,
and the state store.

Run (local dev):
  uv run fastapi dev src/main.py

Env:
  export AWS_ACCESS_KEY_ID=...
  export AWS_SECRET_ACCESS_KEY=...
  export AWS_DEFAULT_REGION=us-east-2

  # Optional -- production database:
  export DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db

Start AgentOS:
  python -m src.main

Then open AgentUI and connect to:
  http://localhost:7777
"""

from dotenv import load_dotenv

load_dotenv()

from src import instrumentation  # noqa: E402
from agno.os import AgentOS  # noqa: E402
from src.api import router as api_router, set_state_store  # noqa: E402
from src.config import DB, get_state_db_url  # noqa: E402
from src.state import StateStore  # noqa: E402
from src.team import supervisor_team  # noqa: E402
from src.workflow import onboarding_workflow  # noqa: E402

instrumentation.setup()

# Initialize the workflow state store
state_store = StateStore(db_url=get_state_db_url())
set_state_store(state_store)

agent_os = AgentOS(
    id="onboarding-demo",
    teams=[supervisor_team],
    workflows=[onboarding_workflow],
    db=DB,
)

app = agent_os.get_app()

# Mount the workflow lifecycle API routes
app.include_router(api_router)

if __name__ == "__main__":
    agent_os.serve("src.main:app", reload=True)
