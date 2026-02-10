# AgentOS Production Reference

AgentOS turns Agno agents into production APIs with 50+ endpoints, SSE streaming, and a control plane UI.

Docs: https://docs.agno.com/agent-os/introduction

## Basic AgentOS Setup

```python
from agno.os import AgentOS
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses

agent = Agent(
    name="My Agent",
    model=OpenAIResponses(id="gpt-5.2"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
)

agent_os = AgentOS(agents=[agent])
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="main:app", reload=True)
```

The `app` string in `serve()` must match `<filename>:<variable>` where the variable is the result of `get_app()`.

## AgentOS with Registry (Builder Components)

Pre-register components to use them in the AgentOS visual builder:

```python
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.os import AgentOS
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools
from agno.tools.duckduckgo import DuckDuckGoTools

db = PostgresDb(
    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    id="postgres_db",
)

def sample_tool():
    return "Hello, world!"

registry = Registry(
    name="My Registry",
    tools=[DuckDuckGoTools(), sample_tool, CalculatorTools()],
    models=[
        OpenAIChat(id="gpt-4o"),
        Claude(id="claude-sonnet-4-5"),
    ],
    dbs=[db],
)

agent = Agent(
    id="registry-agent",
    model=Claude(id="claude-sonnet-4-5"),
    db=db,
)

agent_os = AgentOS(
    agents=[agent],
    id="my-agent-os",
    registry=registry,
    db=db,
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="main:app", reload=True)
```

## Multiple Agents

```python
from agno.os import AgentOS

research_agent = Agent(
    name="Researcher",
    model=OpenAIChat(id="gpt-4o"),
    tools=[WebSearchTools()],
    db=db,
)

writer_agent = Agent(
    name="Writer",
    model=OpenAIChat(id="gpt-4o"),
    db=db,
)

agent_os = AgentOS(
    agents=[research_agent, writer_agent],
    db=db,
)
app = agent_os.get_app()
```

## Production Configuration

### PostgreSQL (required for production)

```python
from agno.db.postgres import PostgresDb
import os

db = PostgresDb(db_url=os.getenv("DATABASE_URL"))

agent = Agent(
    name="Production Agent",
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    show_tool_calls=False,
    debug_mode=False,
    markdown=True,
)

agent_os = AgentOS(agents=[agent], db=db)
```

### Security Key

Secure your AgentOS instance:

```python
agent_os = AgentOS(
    agents=[agent],
    security_key=os.getenv("AGNO_SECURITY_KEY"),
)
```

## BYO FastAPI App

Integrate AgentOS into an existing FastAPI application:

```python
from fastapi import FastAPI
from agno.os import AgentOS

# Your existing FastAPI app
my_app = FastAPI(title="My Application")

@my_app.get("/health")
async def health():
    return {"status": "ok"}

# Create AgentOS with your app
agent_os = AgentOS(
    agents=[agent],
    app=my_app,  # Pass your existing app
)

# AgentOS adds its routes to your app
app = agent_os.get_app()
```

## Middleware

### JWT Authentication

```python
from agno.os.middleware.jwt import JWTMiddleware

agent_os = AgentOS(
    agents=[agent],
    middleware=[
        JWTMiddleware(
            secret_key=os.getenv("JWT_SECRET"),
            algorithm="HS256",
        ),
    ],
)
```

### Custom Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        print(f"Response: {response.status_code}")
        return response

agent_os = AgentOS(
    agents=[agent],
    middleware=[LoggingMiddleware],
)
```

## MCP Integration

Enable MCP (Model Context Protocol) functionality in AgentOS:

```python
from agno.os import AgentOS
from agno.tools.mcp import MCPTools

agent_os = AgentOS(
    agents=[agent],
    mcp=True,  # Enable MCP endpoints
)
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  agent_os:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+psycopg://ai:ai@db:5432/ai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db

  db:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=ai
      - POSTGRES_PASSWORD=ai
      - POSTGRES_DB=ai
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## Railway Deployment

```bash
# Install Railway CLI
brew install railway

# Login and deploy
railway login
./scripts/railway_up.sh
```

The Railway deployment script provisions PostgreSQL, configures environment variables, and deploys.

## Connecting to AgentOS Control Plane

1. Open https://os.agno.com
2. Click **Add OS**
3. For local: enter `http://localhost:8000`
4. For production: enter your deployed domain

The control plane connects directly to your AgentOS instance from the browser. No data is proxied through Agno servers.

## AgentOS API

Once running, the API provides:

- `POST /v1/runs` - Run an agent
- `GET /v1/agents` - List available agents
- `GET /v1/sessions` - List sessions
- `GET /v1/sessions/{session_id}` - Get session details
- API docs at `http://localhost:8000/docs`

## Interfaces

### Slack Integration

```python
from agno.os.interfaces.slack import SlackInterface

agent_os = AgentOS(
    agents=[agent],
    interfaces=[
        SlackInterface(
            bot_token=os.getenv("SLACK_BOT_TOKEN"),
            signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
        ),
    ],
)
```

### WhatsApp Integration

```python
from agno.os.interfaces.whatsapp import WhatsAppInterface

agent_os = AgentOS(
    agents=[agent],
    interfaces=[
        WhatsAppInterface(
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            access_token=os.getenv("WHATSAPP_ACCESS_TOKEN"),
            verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN"),
        ),
    ],
)
```

## Custom Lifespan

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Startup logic
    print("Starting up...")
    yield
    # Shutdown logic
    print("Shutting down...")

agent_os = AgentOS(
    agents=[agent],
    lifespan=lifespan,
)
```

## Makefile for Development

```makefile
dev:
	fastapi dev main.py

serve:
	python main.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
```

## Architecture Summary

```
AgentOS = Runtime + Control Plane

Runtime:
  - Runs your Agno agents
  - FastAPI-based (add routes, middleware, workers)
  - 50+ pre-built API endpoints with SSE streaming
  - Runs as a container in your cloud

Control Plane (os.agno.com):
  - Connects from browser directly to your runtime
  - No data proxied through Agno
  - Monitor sessions, traces, memory
  - Visual agent builder (with Registry)
```

## Key Principles

- **Private by Design**: Database, sessions, memory, traces stay in your infrastructure
- **Zero Transmission**: No conversations or logs sent to Agno
- **Client-Side UI**: Control plane reads directly from your database, displays in browser, stores nothing
- **FastAPI Compatible**: Add your own routes, middleware, background tasks
