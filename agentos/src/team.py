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
        "Turn the user's onboarding request into a short plan.",
        "Identify missing info and ask only for what you need.",
        "When ready, execute the onboarding workflow using the available workflow tool.",
    ],
    markdown=True,
)

supervisor_team = Team(
    name="Supervisor Team",
    model=MODEL,
    members=[planner_agent],
    tools=[workflow_tools],
    instructions=[
        "You are a supervisor team for onboarding companies into enterprise systems.",
        "First: produce a short plan.",
        "Then: execute the onboarding workflow.",
        "Finally: return the workflow results + a clean summary.",
    ],
    markdown=True,
    db=DB,
)
