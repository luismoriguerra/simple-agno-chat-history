import os

from agno.db.sqlite import SqliteDb
from agno.models.aws import Claude

MODEL = Claude(id=os.environ.get("AGENT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"))
DB = SqliteDb(db_file="tmp/agentos.db")
