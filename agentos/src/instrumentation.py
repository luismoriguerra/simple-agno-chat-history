"""
instrumentation.py

Observability and instrumentation setup.  Initializes LangWatch tracing
and provides a structured event logger for workflow audit trails.
"""

import json
import logging
from typing import Any

import langwatch
from openinference.instrumentation.agno import AgnoInstrumentor

logger = logging.getLogger("agentos.events")


def setup() -> None:
    """Initialize LangWatch and instrument Agno."""
    langwatch.setup(instrumentors=[AgnoInstrumentor()])
    logger.info("Instrumentation initialized: LangWatch + AgnoInstrumentor")


def log_workflow_event(
    event_type: str,
    data: dict[str, Any],
    run_id: str = "",
) -> None:
    """Emit a structured log entry for a workflow event.

    Provides an audit trail alongside LangWatch traces so operators
    can correlate run-level events with LLM-level spans.
    """
    logger.info(
        json.dumps(
            {
                "event_type": event_type,
                "run_id": run_id,
                **data,
            },
        ),
    )
