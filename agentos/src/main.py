"""
main.py

Run:
  python3 -m venv .venv && source .venv/bin/activate
  pip install -U agno boto3 "fastapi[standard]"

Env:
  export AWS_ACCESS_KEY_ID=...
  export AWS_SECRET_ACCESS_KEY=...
  export AWS_DEFAULT_REGION=us-east-2

Start AgentOS:
  python -m src.main

Then open AgentUI and connect to:
  http://localhost:7777
"""

from dotenv import load_dotenv

load_dotenv()

from src import instrumentation
from agno.os import AgentOS
from src.config import DB
from src.team import supervisor_team
from src.workflow import onboarding_workflow

instrumentation.setup()

agent_os = AgentOS(
    id="onboarding-demo",
    teams=[supervisor_team],
    workflows=[onboarding_workflow],
    db=DB,
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve("src.main:app", reload=True)
