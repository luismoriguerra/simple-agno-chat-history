import langwatch
from openinference.instrumentation.agno import AgnoInstrumentor


def setup():
    """Initialize LangWatch and instrument Agno."""
    langwatch.setup(instrumentors=[AgnoInstrumentor()])
