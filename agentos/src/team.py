"""
team.py

Supervisor team and planner agent definitions with human-in-the-loop
tool access and structured result awareness.

Factors addressed:
  2 - Own your prompts (explicit, tunable instructions)
  7 - Contact humans with tool calls (approval + escalation tools)
  8 - Own your control flow (retry / escalation policy in instructions)
 10 - Small, focused agents (planner has one clear job)
"""

from agno.agent import Agent
from agno.team import Team
from agno.tools.workflow import WorkflowTools

from src.config import DB, MAX_STEP_RETRIES, MODEL
from src.human_tools import escalate_to_human, request_approval
from src.workflow import onboarding_workflow

workflow_tools = WorkflowTools(workflow=onboarding_workflow)

planner_agent = Agent(
    name="Onboarding Planner",
    model=MODEL,
    instructions=[
        "You onboard companies into 4 enterprise systems: Slack, GitHub, Newsletter, and Grants.",
        "The company name is required. If the user does not provide it, ask for it concisely before doing anything else.",
        "Keep follow-up questions short -- one or two sentences, no bullet lists.",
        "Once you have the company name, produce a brief plan and execute the onboarding workflow.",
        "Each provisioning step returns structured JSON with a 'status' field (success/fail/error).",
        "If a step fails, note the error_code and whether it is retryable.",
        f"If a step fails more than {MAX_STEP_RETRIES} times, use the escalate_to_human tool.",
        "If you need human approval for a high-stakes action, use the request_approval tool.",
    ],
    markdown=True,
)

supervisor_team = Team(
    name="Supervisor Team",
    model=MODEL,
    members=[planner_agent],
    tools=[workflow_tools, request_approval, escalate_to_human],
    instructions=[
        "You are a supervisor team for onboarding companies into 4 enterprise systems: "
        "Slack, GitHub, Newsletter, and Grants.",
        "First: confirm the company name (required). If missing, ask concisely.",
        "Then: execute the onboarding workflow.",
        "Each provisioning step returns structured JSON. Parse the 'status' field to determine SUCCESS or FAIL.",
        f"If a system fails and the error is retryable, you may retry up to {MAX_STEP_RETRIES} times.",
        "If retries are exhausted, use the escalate_to_human tool to flag the issue.",
        "If a high-stakes decision is needed, use the request_approval tool and wait for approval.",
        "Finally: return a summary listing each of the 4 systems (Slack, GitHub, Newsletter, Grants) "
        "with a SUCCESS or FAIL status.",
        "Include error details for any failed systems and recommended next actions.",
    ],
    markdown=True,
    db=DB,
    add_history_to_context=True,
    num_history_runs=5,
)
