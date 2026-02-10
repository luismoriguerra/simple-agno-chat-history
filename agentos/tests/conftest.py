import scenario
from dotenv import load_dotenv

load_dotenv()


def pytest_configure(config):
    """Register custom markers and configure scenario defaults."""
    scenario.configure(
        default_model="bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        cache_key="v1",
    )
