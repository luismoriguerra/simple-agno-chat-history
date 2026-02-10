from agno.workflow import StepOutput


def _extract_company(step_input) -> str:
    """Extract company name from step input, handling both str and dict inputs."""
    if isinstance(step_input.input, dict):
        return step_input.input.get("company_name", "UnknownCo")
    elif isinstance(step_input.input, str):
        return step_input.input
    return "UnknownCo"


def _make_provisioner(system: str, template: str):
    """Factory that creates a provisioning step executor."""
    def executor(step_input) -> StepOutput:
        company = _extract_company(step_input)
        return StepOutput(content=template.format(company=company, slug=company.lower()))
    executor.__name__ = f"provision_{system}"
    return executor


provision_slack = _make_provisioner(
    "slack", "Slack provisioned for {company}: channel=#welcome-{slug}"
)
provision_github = _make_provisioner(
    "github", "GitHub provisioned for {company}: repo={slug}-onboarding"
)
provision_newsletter = _make_provisioner(
    "newsletter", "Newsletter audience created for {company}: list_id=list_{slug}"
)
provision_grants = _make_provisioner(
    "grants", "Grants tracker initialized for {company}: grant_board=grants-{slug}"
)
