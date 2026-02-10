# Agno Code Patterns Reference

Detailed code patterns for agents, teams, workflows, learning, and advanced features.

## Structured Output with Pydantic

```python
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat

class MovieScript(BaseModel):
    title: str = Field(..., description="Movie title")
    genre: str = Field(..., description="Genre of the movie")
    setting: str = Field(..., description="Setting of the movie")
    characters: list[str] = Field(..., description="Main characters")
    plot: str = Field(..., description="Brief plot summary")

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=MovieScript,
    instructions="Write movie scripts based on the topic",
)

# Result is automatically parsed into the Pydantic model
result: MovieScript = agent.run("A heist in space").content
print(result.title)
print(result.characters)
```

### Nested Structured Output

```python
class Finding(BaseModel):
    category: str
    description: str
    severity: str  # "high", "medium", "low"

class AuditReport(BaseModel):
    summary: str
    findings: list[Finding]
    overall_risk: str
    recommendations: list[str]

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=AuditReport,
)
```

## Chat History and Session Management

### Basic Chat History

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=SqliteDb(db_file="tmp/agents.db"),
    add_history_to_context=True,
    num_history_runs=3,  # Include last 3 exchanges
)

# Same session - agent remembers context
agent.print_response("My name is Alice", user_id="alice", session_id="s1")
agent.print_response("What is my name?", user_id="alice", session_id="s1")

# New session - no memory of previous session (unless learning is enabled)
agent.print_response("What is my name?", user_id="alice", session_id="s2")
```

### Session with User and Session IDs

```python
# Pass user_id and session_id per request
response = agent.run(
    "Hello",
    user_id="user@example.com",
    session_id="session_abc123",
)
```

## Knowledge / RAG Patterns

### LanceDB (recommended for local dev)

```python
from agno.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="docs",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    search_knowledge=True,
)
```

### ChromaDB

```python
from agno.vectordb.chroma import ChromaDb, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

knowledge = Knowledge(
    vector_db=ChromaDb(
        name="my_collection",
        path="tmp/chromadb",
        persistent_client=True,
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
```

### PgVector (production)

```python
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

knowledge = Knowledge(
    vector_db=PgVector(
        db_url="postgresql+psycopg://user:pass@localhost:5432/ai",
        table_name="knowledge_embeddings",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)
```

### Loading Documents into Knowledge

```python
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.website import WebsiteKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.json_kb import JSONKnowledgeBase
from agno.knowledge.csv_kb import CSVKnowledgeBase

# PDF files
knowledge = PDFKnowledgeBase(
    path="data/pdfs",
    vector_db=vector_db,
)

# Websites
knowledge = WebsiteKnowledgeBase(
    urls=["https://docs.agno.com"],
    vector_db=vector_db,
)

# Load knowledge (run once or when data changes)
knowledge.load(recreate=False)  # Set recreate=True to rebuild
```

## Workflow Patterns

### Basic Workflow

```python
from agno.workflow import Workflow
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

researcher = Agent(
    name="Researcher",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Research the given topic thoroughly",
)

writer = Agent(
    name="Writer",
    model=OpenAIChat(id="gpt-4o"),
    instructions="Write a blog post based on the research",
)

async def blog_pipeline(session_state, topic: str):
    # Step 1: Research
    research = await researcher.arun(f"Research: {topic}")

    # Step 2: Write based on research
    article = await writer.arun(
        f"Write a blog post based on this research:\n{research.content}"
    )

    return article

workflow = Workflow(
    name="Blog Generator",
    steps=blog_pipeline,
    db=SqliteDb(db_file="tmp/workflow.db"),
)
```

### Workflow with Shared State

```python
async def pipeline(session_state, query: str):
    # Store intermediate results in session_state
    session_state["research"] = await researcher.arun(query)

    # Access previous step's results
    research_content = session_state["research"].content
    session_state["article"] = await writer.arun(research_content)

    return session_state["article"]
```

## Team Patterns

### Supervisor Pattern (default)

The leader decomposes tasks, delegates, and synthesizes results.

```python
from agno.team import Team

team = Team(
    members=[researcher, writer, editor],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Coordinate research, writing, and editing",
)
```

### Router Pattern

Route directly to the right specialist without synthesis.

```python
team = Team(
    members=[english_agent, spanish_agent, french_agent],
    model=OpenAIChat(id="gpt-4o"),
    respond_directly=True,
    determine_input_for_members=False,
)
```

### Broadcast Pattern

All members work on the task in parallel.

```python
team = Team(
    members=[analyst_1, analyst_2, analyst_3],
    model=OpenAIChat(id="gpt-4o"),
    delegate_to_all_members=True,
)
```

### Nested Teams

```python
research_team = Team(
    name="Research Team",
    members=[web_researcher, paper_researcher],
    model=OpenAIChat(id="gpt-4o"),
    role="Research topics thoroughly",
)

writing_team = Team(
    name="Writing Team",
    members=[writer, editor],
    model=OpenAIChat(id="gpt-4o"),
    role="Write and edit content",
)

main_team = Team(
    members=[research_team, writing_team],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Coordinate research and writing teams",
)
```

## Custom Tool Creation

### Function Tools

Any Python function with type hints and a docstring becomes a tool:

```python
import json
import httpx

def get_top_hackernews_stories(num_stories: int = 10) -> str:
    """Get top stories from Hacker News.

    Args:
        num_stories: Number of stories to return. Defaults to 10.
    """
    response = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()

    stories = []
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        )
        story = story_response.json()
        stories.append(story)

    return json.dumps(stories)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[get_top_hackernews_stories],
)
```

### Async Tools

```python
async def fetch_data(url: str) -> str:
    """Fetch data from a URL.

    Args:
        url: The URL to fetch data from.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[fetch_data],
)
```

## Learning Modes

### Always Learn (background extraction)

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses

agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    db=SqliteDb(db_file="tmp/agents.db"),
    add_history_to_context=True,
    learning=True,  # Extracts profile and memories in background
    markdown=True,
)

# Session 1: agent learns about the user
agent.print_response(
    "Hi! I'm Alice. I work at Anthropic as a research scientist.",
    user_id="alice@example.com",
    session_id="session_1",
)

# Session 2: agent remembers across sessions
agent.print_response(
    "What do you know about me?",
    user_id="alice@example.com",
    session_id="session_2",
)
```

### Agentic Learning (tool-based, visible decisions)

```python
from agno.learn import LearningMachine, LearningMode, UserMemoryConfig, UserProfileConfig

agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    db=SqliteDb(db_file="tmp/agents.db"),
    learning=LearningMachine(
        user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
        user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
    ),
)
```

### Accessing Learning Data

```python
lm = agent.get_learning_machine()
lm.user_profile_store.print(user_id="alice@example.com")
lm.user_memory_store.print(user_id="alice@example.com")
```

## Storage Backend Patterns

### SQLite (development)

```python
from agno.db.sqlite import SqliteDb
db = SqliteDb(db_file="tmp/agents.db")
```

### PostgreSQL (production)

```python
from agno.db.postgres import PostgresDb
db = PostgresDb(db_url="postgresql+psycopg://user:pass@localhost:5432/ai")
```

### MongoDB

```python
from agno.db.mongodb import MongoDb
db = MongoDb(
    db_url="mongodb://localhost:27017",
    db_name="agno",
    collection_name="agent_sessions",
)
```

### Redis

```python
from agno.db.redis import RedisDb
db = RedisDb(url="redis://localhost:6379")
```

### JSON files

```python
from agno.db.json import JsonDb
db = JsonDb(dir_path="tmp/sessions")
```

## Guardrails

```python
from agno.guardrails import OpenAIModerationGuardrail

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    guardrails=[
        OpenAIModerationGuardrail(),
    ],
)
```

## Hooks (Pre and Post)

```python
def pre_hook(agent, message):
    """Called before the agent processes a message."""
    print(f"Processing: {message}")
    return message

def post_hook(agent, response):
    """Called after the agent generates a response."""
    print(f"Response generated with {response.metrics.total_tokens} tokens")
    return response

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    pre_hook=pre_hook,
    post_hook=post_hook,
)
```

## MCP Tools

```python
from agno.tools.mcp import MCPTools

# Stdio transport
async with MCPTools(
    server_params=StdioServerParameters(
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "test.db"],
    )
) as mcp_tools:
    agent = Agent(tools=[mcp_tools])
    agent.print_response("List all tables")

# Multiple MCP servers
from agno.tools.mcp import MultiMCPTools

async with MultiMCPTools(
    servers={
        "sqlite": StdioServerParameters(command="uvx", args=["mcp-server-sqlite"]),
        "filesystem": StdioServerParameters(command="uvx", args=["mcp-server-fs"]),
    }
) as mcp_tools:
    agent = Agent(tools=[mcp_tools])
```

## Multimodal Agents

### Image Input

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.media import Image

agent = Agent(model=OpenAIChat(id="gpt-4o"))
agent.print_response(
    "Describe this image",
    images=[Image(url="https://example.com/image.jpg")],
)
```

### Audio Input

```python
from agno.media import Audio

agent.print_response(
    "Transcribe this audio",
    audio=[Audio(filepath="audio.mp3")],
)
```

## Error Handling Pattern

```python
from agno.agent import Agent, RunResponse

agent = Agent(model=OpenAIChat(id="gpt-4o"))

try:
    response: RunResponse = agent.run("query")
    if response and response.content:
        print(response.content)
    else:
        print("No response generated")
except Exception as e:
    print(f"Agent error: {e}")
```

## Dependencies (Dependency Injection)

```python
from agno.agent import Agent

def get_user_context(user_id: str) -> dict:
    return {"role": "admin", "department": "engineering"}

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    deps=[get_user_context],
)
```
