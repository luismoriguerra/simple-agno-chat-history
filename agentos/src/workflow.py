"""
workflow.py

Onboarding workflow definition with parallel provisioning steps
and a structured reporting step.

Factors addressed:
  4 - Tools are structured outputs (reporter parses JSON results)
  8 - Own your control flow (explicit step graph)
 10 - Small, focused agents (reporter has narrow scope)
"""

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
        "Write a short onboarding execution report based on the provisioning results.",
        "Each provisioning step returns a JSON object with fields: "
        "system, status, details, error_code, retryable, attempt.",
        "Parse these JSON results and create a checklist with SUCCESS or FAIL per system.",
        "If any system has status 'error' or 'fail', mark it as FAIL and include the error details.",
        "If any step was retried (attempt > 1), note the number of attempts.",
        "If anything failed, list recommended next actions.",
        "Always list all 4 systems: Slack, GitHub, Newsletter, and Grants.",
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
