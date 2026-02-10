from agno.agent import Agent
from agno.workflow import Step, Workflow
from agno.workflow.parallel import Parallel

from src.config import MODEL
from src.provisioners import (
    provision_github,
    provision_grants,
    provision_newsletter,
    provision_slack,
)

# Agent scoped to the workflow's final reporting step
report_agent = Agent(
    name="Onboarding Reporter",
    model=MODEL,
    instructions=[
        "Write a short onboarding execution report.",
        "Include a checklist with SUCCESS/FAIL per system.",
        "If anything is missing, list next actions.",
    ],
    markdown=True,
)

# Individual provisioning steps
slack_step = Step(name="Provision Slack", executor=provision_slack)
github_step = Step(name="Provision GitHub", executor=provision_github)
newsletter_step = Step(name="Provision Newsletter", executor=provision_newsletter)
grants_step = Step(name="Provision Grants", executor=provision_grants)

report_step = Step(name="Summarize & Report", agent=report_agent)

# Full onboarding workflow
onboarding_workflow = Workflow(
    name="Company Onboarding Workflow",
    steps=[
        Parallel(
            slack_step,
            github_step,
            newsletter_step,
            grants_step,
            name="Provision Systems (Parallel)",
        ),
        report_step,
    ],
)
