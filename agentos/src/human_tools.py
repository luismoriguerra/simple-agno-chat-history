"""
human_tools.py

Human-in-the-loop tools that the agent team can invoke to request
approval or escalate issues to a human operator.

These are standard Agno tool functions (plain Python callables with
docstrings) that return JSON strings.

Factors addressed:
  7 - Contact humans with tool calls
  8 - Own your control flow (escalation as explicit decision)
  9 - Compact errors into context (structured escalation info)
"""

import json


def request_approval(
    action: str,
    reason: str,
    details: str = "",
    urgency: str = "medium",
) -> str:
    """Request human approval before proceeding with a high-stakes action.

    Use this tool when you encounter repeated failures or need to perform
    an action that requires human verification.

    Args:
        action: The action requiring approval (e.g., "retry provisioning", "skip system").
        reason: Why approval is needed.
        details: Additional context about the situation.
        urgency: Priority level - "low", "medium", or "high".

    Returns:
        A JSON status message indicating the approval request has been created.
    """
    return json.dumps({
        "status": "approval_requested",
        "action": action,
        "reason": reason,
        "details": details,
        "urgency": urgency,
        "message": (
            f"Approval requested for: {action}. Reason: {reason}. "
            "The workflow is paused until approval is received."
        ),
    })


def escalate_to_human(
    issue: str,
    context: str,
    failed_systems: str = "",
    attempts_made: int = 0,
) -> str:
    """Escalate an issue to a human operator when automated resolution fails.

    Use this when the agent has exhausted retry attempts or encountered
    an unrecoverable error that cannot be resolved automatically.

    Args:
        issue: Brief description of the problem.
        context: Full context of what was attempted.
        failed_systems: Comma-separated list of systems that failed.
        attempts_made: How many retry attempts were made.

    Returns:
        A JSON status message confirming the escalation.
    """
    return json.dumps({
        "status": "escalated",
        "issue": issue,
        "context": context,
        "failed_systems": failed_systems,
        "attempts_made": attempts_made,
        "message": (
            f"Issue escalated to human operator: {issue}. "
            f"Failed systems: {failed_systems or 'none specified'}. "
            f"Attempts made: {attempts_made}."
        ),
    })
