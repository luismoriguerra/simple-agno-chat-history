from agno.agent import Agent
from agno.team import Team
from agno.tools.workflow import WorkflowTools

from src.config import DB, MODEL
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
    ],
    markdown=True,
)

supervisor_team = Team(
    name="Supervisor Team",
    model=MODEL,
    members=[planner_agent],
    tools=[workflow_tools],
    instructions=[
        "You are a supervisor team for onboarding companies into 4 enterprise systems: Slack, GitHub, Newsletter, and Grants.",
        "First: confirm the company name (required). If missing, ask concisely.",
        "Then: execute the onboarding workflow.",
        "Finally: return a summary that lists each of the 4 systems (Slack, GitHub, Newsletter, Grants) with a SUCCESS or FAIL status.",
    ],
    markdown=True,
    db=DB,
)
