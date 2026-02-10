# Tools and Knowledge Reference

Complete reference for Agno toolkits, custom tools, MCP integration, knowledge bases, vector databases, and embedders.

## Built-in Toolkits

All toolkits are imported from `agno.tools.<name>` and passed to the `tools` parameter as instances.

### Web and Search

```python
from agno.tools.hackernews import HackerNewsTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.websearch import WebSearchTools

agent = Agent(tools=[DuckDuckGoTools()])
```

| Toolkit | Import | Purpose |
|---------|--------|---------|
| `HackerNewsTools` | `agno.tools.hackernews` | Fetch HN stories, users, comments |
| `DuckDuckGoTools` | `agno.tools.duckduckgo` | Web search via DuckDuckGo |
| `WebSearchTools` | `agno.tools.websearch` | General web search |

### Database

```python
from agno.tools.sql import SQLTools
from agno.tools.postgres import PostgresTools
from agno.tools.duckdb import DuckDbTools
from agno.tools.csv_tools import CSVTools
from agno.tools.pandas import PandasTools
from agno.tools.neo4j import Neo4jTools
from agno.tools.google_bigquery import GoogleBigQueryTools
```

| Toolkit | Import | Purpose |
|---------|--------|---------|
| `SQLTools` | `agno.tools.sql` | Generic SQL database queries |
| `PostgresTools` | `agno.tools.postgres` | PostgreSQL-specific operations |
| `DuckDbTools` | `agno.tools.duckdb` | DuckDB analytics queries |
| `CSVTools` | `agno.tools.csv_tools` | CSV file analysis |
| `PandasTools` | `agno.tools.pandas` | Pandas DataFrame operations |
| `Neo4jTools` | `agno.tools.neo4j` | Neo4j graph database |
| `GoogleBigQueryTools` | `agno.tools.google_bigquery` | BigQuery queries |

### Local / System

```python
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.tools.file import FileTools
from agno.tools.local_file_system import LocalFileSystemTools
from agno.tools.calculator import CalculatorTools
from agno.tools.docker import DockerTools
from agno.tools.sleep import SleepTools
```

| Toolkit | Import | Purpose |
|---------|--------|---------|
| `PythonTools` | `agno.tools.python` | Execute Python code |
| `ShellTools` | `agno.tools.shell` | Execute shell commands |
| `FileTools` | `agno.tools.file` | Read/write files |
| `LocalFileSystemTools` | `agno.tools.local_file_system` | File system management |
| `CalculatorTools` | `agno.tools.calculator` | Mathematical calculations |
| `DockerTools` | `agno.tools.docker` | Docker container management |
| `SleepTools` | `agno.tools.sleep` | Wait/sleep operations |

### AI Models / Generation

```python
from agno.tools.openai import OpenAITools
from agno.tools.dalle import DalleTools
from agno.tools.gemini_tools import GeminiTools
```

| Toolkit | Import | Purpose |
|---------|--------|---------|
| `OpenAITools` | `agno.tools.openai` | OpenAI API operations |
| `DalleTools` | `agno.tools.dalle` | DALL-E image generation |
| `GeminiTools` | `agno.tools.gemini_tools` | Gemini model operations |

### External Services

```python
from agno.tools.apify import ApifyTools
from agno.tools.confluence import ConfluenceTools
from agno.tools.clickup import ClickUpTools
from agno.tools.composio import ComposioTools
from agno.tools.airflow import AirflowTools
from agno.tools.aws_lambda import AWSLambdaTools
from agno.tools.aws_ses import AWSSESTools
from agno.tools.calcom import CalComTools
from agno.tools.cartesia import CartesiaTools
from agno.tools.bitbucket import BitbucketTools
from agno.tools.custom_api import CustomAPITools
```

### Including / Excluding Tools from a Toolkit

```python
# Only include specific tools
tools = DuckDuckGoTools(include=["search"])

# Exclude specific tools
tools = DuckDuckGoTools(exclude=["news"])
```

## Custom Tool Creation

### Function Tools (simplest)

Any function with type hints and a docstring:

```python
def get_weather(city: str, unit: str = "celsius") -> str:
    """Get the current weather for a city.

    Args:
        city: The city name to get weather for.
        unit: Temperature unit, either 'celsius' or 'fahrenheit'.
    """
    # Your implementation
    return f"25 degrees {unit} in {city}"

agent = Agent(tools=[get_weather])
```

Rules for function tools:
- Must have type hints on all parameters
- Must have a docstring (used as tool description)
- Args section in docstring describes each parameter to the LLM
- Return type should be `str` (or JSON-serializable)

### Async Function Tools

```python
import httpx

async def fetch_url(url: str) -> str:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

agent = Agent(tools=[fetch_url])
```

### Tool Call Limit

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[my_tool],
    tool_call_limit=5,  # Max 5 tool calls per run
)
```

### Tool Result Caching

```python
from agno.tools.caching import CachedTool

cached_search = CachedTool(
    tool=search_function,
    ttl=300,  # Cache for 5 minutes
)

agent = Agent(tools=[cached_search])
```

### Tool Hooks

```python
from agno.tools.hooks import ToolHook

def before_tool_call(tool_name, args):
    print(f"Calling {tool_name} with {args}")

def after_tool_call(tool_name, result):
    print(f"{tool_name} returned: {result[:100]}")

agent = Agent(
    tools=[my_tool],
    tool_hooks=[
        ToolHook(before=before_tool_call, after=after_tool_call),
    ],
)
```

## MCP (Model Context Protocol)

### Stdio Transport

```python
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

async with MCPTools(
    server_params=StdioServerParameters(
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "test.db"],
    )
) as mcp_tools:
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[mcp_tools],
    )
    agent.print_response("List all tables")
```

### SSE Transport

```python
from agno.tools.mcp import MCPTools
from mcp import SSEServerParameters

async with MCPTools(
    server_params=SSEServerParameters(url="http://localhost:3000/sse")
) as mcp_tools:
    agent = Agent(tools=[mcp_tools])
```

### Streamable HTTP Transport

```python
from agno.tools.mcp import MCPTools
from mcp import StreamableHTTPServerParameters

async with MCPTools(
    server_params=StreamableHTTPServerParameters(
        url="http://localhost:3000/mcp"
    )
) as mcp_tools:
    agent = Agent(tools=[mcp_tools])
```

### Multiple MCP Servers

```python
from agno.tools.mcp import MultiMCPTools

async with MultiMCPTools(
    servers={
        "sqlite": StdioServerParameters(
            command="uvx",
            args=["mcp-server-sqlite", "--db-path", "test.db"],
        ),
        "filesystem": StdioServerParameters(
            command="uvx",
            args=["mcp-server-filesystem", "/tmp"],
        ),
    }
) as mcp_tools:
    agent = Agent(tools=[mcp_tools])
```

## Knowledge Base Setup

### Knowledge Class

The `Knowledge` class is the core abstraction for RAG:

```python
from agno.knowledge import Knowledge

knowledge = Knowledge(
    name="My Knowledge Base",
    vector_db=<vector_db_instance>,
)

# Load documents
knowledge.load(recreate=False)

# Use with agent
agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,  # CRITICAL: must be True
)
```

### Content Types / Readers

```python
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.website import WebsiteKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.json_kb import JSONKnowledgeBase
from agno.knowledge.csv_kb import CSVKnowledgeBase
```

| Reader | Import | Source |
|--------|--------|--------|
| `PDFKnowledgeBase` | `agno.knowledge.pdf` | PDF files or directories |
| `WebsiteKnowledgeBase` | `agno.knowledge.website` | Web pages by URL |
| `TextKnowledgeBase` | `agno.knowledge.text` | Plain text files |
| `JSONKnowledgeBase` | `agno.knowledge.json_kb` | JSON files |
| `CSVKnowledgeBase` | `agno.knowledge.csv_kb` | CSV files |

Usage:

```python
# PDF files from a directory
knowledge = PDFKnowledgeBase(
    path="data/documents/",
    vector_db=vector_db,
)

# Website content
knowledge = WebsiteKnowledgeBase(
    urls=["https://docs.agno.com/introduction"],
    vector_db=vector_db,
)

# Load into vector DB (run once or when data changes)
knowledge.load(recreate=False)
# Set recreate=True to rebuild the entire knowledge base
```

## Vector Databases

### LanceDB (recommended for local development)

```python
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder

vector_db = LanceDb(
    uri="tmp/lancedb",
    table_name="knowledge",
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### ChromaDB

```python
from agno.vectordb.chroma import ChromaDb, SearchType

vector_db = ChromaDb(
    name="my_collection",
    path="tmp/chromadb",
    persistent_client=True,
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### PgVector (recommended for production)

```python
from agno.vectordb.pgvector import PgVector, SearchType

vector_db = PgVector(
    db_url="postgresql+psycopg://user:pass@localhost:5432/ai",
    table_name="embeddings",
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### Qdrant

```python
from agno.vectordb.qdrant import Qdrant

vector_db = Qdrant(
    collection="my_collection",
    url="http://localhost:6333",
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### Pinecone

```python
from agno.vectordb.pinecone import Pinecone

vector_db = Pinecone(
    index_name="my-index",
    api_key=os.getenv("PINECONE_API_KEY"),
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### Milvus

```python
from agno.vectordb.milvus import Milvus

vector_db = Milvus(
    collection="my_collection",
    uri="http://localhost:19530",
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### Weaviate

```python
from agno.vectordb.weaviate import Weaviate

vector_db = Weaviate(
    collection="MyCollection",
    url="http://localhost:8080",
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### MongoDB Atlas

```python
from agno.vectordb.mongodb import MongoDB

vector_db = MongoDB(
    collection="embeddings",
    db_url=os.getenv("MONGODB_URL"),
    db_name="agno",
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

### Search Types

All vector databases support these search types:

```python
from agno.vectordb.lancedb import SearchType  # Same enum across all DBs

SearchType.vector     # Pure vector similarity search
SearchType.keyword    # Keyword/full-text search
SearchType.hybrid     # Combined vector + keyword (recommended)
```

## Embedders

### OpenAI (recommended)

```python
from agno.knowledge.embedder.openai import OpenAIEmbedder

embedder = OpenAIEmbedder(id="text-embedding-3-small")
# or
embedder = OpenAIEmbedder(id="text-embedding-3-large")
```

### Other Embedders

```python
# Cohere
from agno.knowledge.embedder.cohere import CohereEmbedder
embedder = CohereEmbedder(id="embed-english-v3.0")

# HuggingFace
from agno.knowledge.embedder.huggingface import HuggingFaceEmbedder
embedder = HuggingFaceEmbedder(id="sentence-transformers/all-MiniLM-L6-v2")

# Ollama (local)
from agno.knowledge.embedder.ollama import OllamaEmbedder
embedder = OllamaEmbedder(id="nomic-embed-text")

# Google/Gemini
from agno.knowledge.embedder.gemini import GeminiEmbedder
embedder = GeminiEmbedder(id="text-embedding-004")

# Mistral
from agno.knowledge.embedder.mistral import MistralEmbedder
embedder = MistralEmbedder(id="mistral-embed")

# AWS Bedrock
from agno.knowledge.embedder.aws_bedrock import AWSBedrockEmbedder
embedder = AWSBedrockEmbedder(id="amazon.titan-embed-text-v1")

# Azure OpenAI
from agno.knowledge.embedder.azure_openai import AzureOpenAIEmbedder
embedder = AzureOpenAIEmbedder(id="text-embedding-3-small")

# SentenceTransformers
from agno.knowledge.embedder.sentencetransformers import SentenceTransformersEmbedder
embedder = SentenceTransformersEmbedder(id="all-MiniLM-L6-v2")

# Together
from agno.knowledge.embedder.together import TogetherEmbedder
embedder = TogetherEmbedder(id="togethercomputer/m2-bert-80M-8k-retrieval")

# Fireworks
from agno.knowledge.embedder.fireworks import FireworksEmbedder
embedder = FireworksEmbedder(id="nomic-ai/nomic-embed-text-v1.5")

# Voyage AI
from agno.knowledge.embedder.voyageai import VoyageAIEmbedder
embedder = VoyageAIEmbedder(id="voyage-2")

# Qdrant FastEmbed
from agno.knowledge.embedder.qdrant_fastembed import QdrantFastEmbedEmbedder
embedder = QdrantFastEmbedEmbedder(id="BAAI/bge-small-en-v1.5")
```

## Chunking Strategies

```python
from agno.knowledge.chunking.fixed_size import FixedSizeChunking
from agno.knowledge.chunking.recursive import RecursiveChunking
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.chunking.markdown import MarkdownChunking
from agno.knowledge.chunking.document import DocumentChunking
from agno.knowledge.chunking.agentic import AgenticChunking
from agno.knowledge.chunking.csv_row import CSVRowChunking

# Use with knowledge base
knowledge = PDFKnowledgeBase(
    path="data/docs/",
    vector_db=vector_db,
    chunking=RecursiveChunking(chunk_size=1000, overlap=200),
)
```

| Strategy | Best For |
|----------|----------|
| `FixedSizeChunking` | Simple, predictable chunks |
| `RecursiveChunking` | General purpose (recommended default) |
| `SemanticChunking` | Meaning-aware boundaries |
| `MarkdownChunking` | Markdown documents |
| `DocumentChunking` | One chunk per document |
| `AgenticChunking` | LLM-determined boundaries |
| `CSVRowChunking` | One chunk per CSV row |

## Complete RAG Example

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.chunking.recursive import RecursiveChunking

# Set up vector DB
vector_db = LanceDb(
    uri="tmp/lancedb",
    table_name="documents",
    search_type=SearchType.hybrid,
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)

# Create knowledge base
knowledge = PDFKnowledgeBase(
    path="data/documents/",
    vector_db=vector_db,
    chunking=RecursiveChunking(chunk_size=1000, overlap=200),
)

# Load documents (run once)
knowledge.load(recreate=False)

# Create agent with knowledge
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    search_knowledge=True,
    instructions="Answer questions using the knowledge base. Always cite your sources.",
    markdown=True,
)

agent.print_response("What does the document say about X?", stream=True)
```

## Hybrid Search Configuration

Hybrid search combines vector similarity with keyword matching for better results:

```python
vector_db = LanceDb(
    uri="tmp/lancedb",
    table_name="docs",
    search_type=SearchType.hybrid,  # Combines vector + keyword
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
)
```

This is the recommended search type for most use cases as it combines semantic understanding with exact keyword matching.
