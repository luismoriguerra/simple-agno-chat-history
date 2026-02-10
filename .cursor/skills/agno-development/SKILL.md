---
name: agno-development
description: Build AI agents, multi-agent teams, and workflows using the Agno framework. Use when creating or modifying Agno agents, teams, workflows, AgentOS deployments, adding tools, knowledge/RAG, learning, memory, or storage to agents. Covers correct import patterns, parameter names, and production best practices.
---

# Agno Development

Build multi-agent systems that learn and improve with every interaction using the Agno framework.

Docs: https://docs.agno.com

## When to Use Each Abstraction

| Abstraction | When to Use | Import |
|-------------|-------------|--------|
| **Agent** | Single task, one domain, 90% of use cases | `from agno.agent import Agent` |
| **Team** | Multiple specialized agents collaborating | `from agno.team import Team` |
| **Workflow** | Sequential steps with conditional logic | `from agno.workflow import Workflow` |
| **AgentOS** | Production API server for agents | `from agno.os import AgentOS` |

## Agent Basics

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions="You are a helpful assistant",
    markdown=True,
)
agent.print_response("Your query", stream=True)
```

### Key Agent Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `model` | Model | LLM to use (required) |
| `tools` | list | Functions or Toolkits |
| `instructions` | str/list | System prompt guidance |
| `db` | Db | Storage backend for sessions |
| `markdown` | bool | Format responses as markdown |
| `add_history_to_context` | bool | Include chat history |
| `num_history_runs` | int | How many previous runs to include |
| `learning` | bool/LearningMachine | Enable learning system |
| `user_id` | str | Identify the user |
| `session_id` | str | Identify the session |
| `output_schema` | BaseModel | Structured output via Pydantic |
| `knowledge` | Knowledge | RAG knowledge base |
| `search_knowledge` | bool | Enable agentic RAG (MUST be True when using knowledge) |
| `show_tool_calls` | bool | Display tool calls in output |
| `debug_mode` | bool | Enable debug logging |

## Model Providers

```python
# OpenAI
from agno.models.openai import OpenAIChat        # Chat completions
from agno.models.openai import OpenAIResponses    # Responses API

# Anthropic
from agno.models.anthropic import Claude

# Google
from agno.models.google import Gemini

# Groq
from agno.models.groq import Groq

# Ollama (local)
from agno.models.ollama import Ollama

# AWS Bedrock
from agno.models.aws import BedrockChat

# Azure OpenAI
from agno.models.azure import AzureOpenAIChat

# DeepSeek
from agno.models.deepseek import DeepSeek

# Mistral
from agno.models.mistral import Mistral
```

Usage:

```python
Agent(model=OpenAIChat(id="gpt-4o"))
Agent(model=OpenAIResponses(id="gpt-5.2"))
Agent(model=Claude(id="claude-sonnet-4-5"))
Agent(model=Gemini(id="gemini-2.0-flash"))
Agent(model=Groq(id="llama-3.3-70b-versatile"))
Agent(model=Ollama(id="llama3.2"))
```

## Tools

Add tools as functions or pre-built toolkits:

```python
from agno.agent import Agent
from agno.tools.hackernews import HackerNewsTools

# Using a toolkit
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[HackerNewsTools()],
)

# Using a custom function
def get_weather(city: str) -> str:
    """Get weather for a city.

    Args:
        city: The city name.
    """
    return f"Sunny in {city}"

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[get_weather],
)
```

Common toolkits: `HackerNewsTools`, `DuckDuckGoTools`, `WebSearchTools`, `SQLTools`, `PythonTools`, `ShellTools`, `FileTools`, `CalculatorTools`, `DalleTools`.

For full toolkit list and custom tools, see [references/TOOLS-AND-KNOWLEDGE.md](references/TOOLS-AND-KNOWLEDGE.md).

## Learning System

### Automatic Learning (simplest)

```python
agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    db=SqliteDb(db_file="tmp/agents.db"),
    add_history_to_context=True,
    learning=True,
)
```

### Agentic Learning (more control)

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

### Cross-User Knowledge

```python
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.chroma import ChromaDb, SearchType
from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode

knowledge = Knowledge(
    name="Agent Learnings",
    vector_db=ChromaDb(
        name="learnings",
        path="tmp/chromadb",
        persistent_client=True,
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)

agent = Agent(
    model=OpenAIResponses(id="gpt-5.2"),
    db=SqliteDb(db_file="tmp/agents.db"),
    learning=LearningMachine(
        knowledge=knowledge,
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
)
```

## Teams

```python
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.tools.hackernews import HackerNewsTools

researcher = Agent(
    name="Researcher",
    model=OpenAIChat(id="gpt-4o"),
    tools=[HackerNewsTools()],
    role="Research topics on the web",
)

writer = Agent(
    name="Writer",
    model=OpenAIChat(id="gpt-4o"),
    role="Write articles based on research",
)

team = Team(
    members=[researcher, writer],
    model=OpenAIChat(id="gpt-4o"),
    instructions="Research and write articles",
)
team.print_response("Write about trending AI startups", stream=True)
```

### Team Delegation Patterns

| Pattern | Configuration | Use Case |
|---------|--------------|----------|
| **Supervisor** | Default | Task decomposition, quality control, synthesis |
| **Router** | `respond_directly=True`, `determine_input_for_members=False` | Route to specialists without synthesis |
| **Broadcast** | `delegate_to_all_members=True` | Parallel research, multiple perspectives |

CRITICAL: Use `members=` (not `agents=`) for Team members.

## Running Agents

```python
# Development: prints formatted output
agent.print_response("query", stream=True)

# Production: returns RunResponse
response = agent.run("query")
print(response.content)

# Production streaming
from agno.agent import RunOutputEvent, RunEvent
from typing import Iterator

stream: Iterator[RunOutputEvent] = agent.run("query", stream=True)
for chunk in stream:
    if chunk.event == RunEvent.run_content:
        print(chunk.content)

# Async
response = await agent.arun("query")
```

## Chat History and Sessions

```python
from agno.db.sqlite import SqliteDb

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    db=SqliteDb(db_file="tmp/agents.db"),
    user_id="user-123",
    session_id="session-456",
    add_history_to_context=True,
    num_history_runs=3,
)
```

## Structured Output

```python
from pydantic import BaseModel

class Report(BaseModel):
    summary: str
    findings: list[str]
    confidence: float

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=Report,
)
result: Report = agent.run("Analyze market trends").content
```

## Knowledge / RAG

```python
from agno.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

knowledge = Knowledge(
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="knowledge_base",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    search_knowledge=True,  # CRITICAL: must be True for agentic RAG
    instructions="Use knowledge base, cite sources",
)
```

For vector DB options and embedders, see [references/TOOLS-AND-KNOWLEDGE.md](references/TOOLS-AND-KNOWLEDGE.md).

## AgentOS (Production)

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

For AgentOS deployment, middleware, and production patterns, see [references/AGENTOS.md](references/AGENTOS.md).

## Storage Backends

```python
# Development
from agno.db.sqlite import SqliteDb
db = SqliteDb(db_file="tmp/agents.db")

# Production
from agno.db.postgres import PostgresDb
db = PostgresDb(db_url="postgresql+psycopg://user:pass@host:5432/db")

# Other options
from agno.db.mongodb import MongoDb
from agno.db.redis import RedisDb
from agno.db.json import JsonDb
```

## Critical Anti-Patterns

### NEVER create agents in loops

```python
# WRONG - massive performance hit
for query in queries:
    agent = Agent(...)  # DO NOT DO THIS
    agent.run(query)

# CORRECT - create once, reuse
agent = Agent(...)
for query in queries:
    agent.run(query)
```

### NEVER forget search_knowledge with Knowledge

```python
# WRONG - knowledge exists but won't be searched
agent = Agent(knowledge=knowledge)

# CORRECT
agent = Agent(knowledge=knowledge, search_knowledge=True)
```

### NEVER use SQLite in production

```python
# Dev only
db = SqliteDb(db_file="tmp/agents.db")

# Production
db = PostgresDb(db_url=os.getenv("DATABASE_URL"))
```

### Common Parameter Mistakes

- Team uses `members=`, NOT `agents=`
- Don't use f-strings in print lines where there are no variables to format
- Don't use emojis in agent instructions or print lines

## Production Checklist

- [ ] Use `PostgresDb` not `SqliteDb`
- [ ] Set `show_tool_calls=False`
- [ ] Set `debug_mode=False`
- [ ] Wrap `agent.run()` in try-except
- [ ] Use `agent.run()` not `agent.print_response()`
- [ ] Set proper `user_id` and `session_id`
- [ ] Use environment variables for API keys and DB URLs

## Additional Resources

- For detailed code patterns: [references/PATTERNS.md](references/PATTERNS.md)
- For AgentOS and production deployment: [references/AGENTOS.md](references/AGENTOS.md)
- For tools, knowledge, and embedders: [references/TOOLS-AND-KNOWLEDGE.md](references/TOOLS-AND-KNOWLEDGE.md)
- Official docs: https://docs.agno.com
- Cookbook: https://docs.agno.com/cookbook/overview
- API Reference: https://docs.agno.com/reference/agents/agent
