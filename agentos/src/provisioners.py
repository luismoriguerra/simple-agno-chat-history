"""
provisioners.py

Deterministic provisioning step executors with strict input validation
and structured result contracts.

Factors addressed:
  1 - Natural language to tool calls (structured step output)
  4 - Tools are structured outputs (StepResult JSON)
  9 - Compact errors into context (structured error info)
"""

from agno.workflow import StepOutput

from src.models import (
    ProvisioningError,
    StepResult,
    StepStatus,
    sanitize_slug,
)


def _extract_company(step_input) -> str:
    """Extract and validate company name from step input.

    Raises ProvisioningError if the company name is missing or blank.
    """
    company: str | None = None
    if isinstance(step_input.input, dict):
        company = step_input.input.get("company_name", "")
    elif isinstance(step_input.input, str):
        company = step_input.input

    if not company or not company.strip():
        raise ProvisioningError(
            message="Company name is required but was not provided or is empty.",
            system="unknown",
            error_code="MISSING_COMPANY_NAME",
        )
    return company.strip()


def _make_provisioner(system: str, template: str):
    """Factory that creates a provisioning step executor with structured output.

    Every executor returns a StepResult JSON inside StepOutput.content so
    downstream consumers (reporter agent, control-flow logic) can parse it
    deterministically.
    """

    def executor(step_input) -> StepOutput:
        try:
            company = _extract_company(step_input)
            slug = sanitize_slug(company)
            details = template.format(company=company, slug=slug)
            result = StepResult(
                system=system,
                status=StepStatus.SUCCESS,
                details=details,
            )
        except ProvisioningError as exc:
            result = StepResult(
                system=system,
                status=StepStatus.ERROR,
                details=str(exc),
                error_code=exc.error_code,
                retryable=False,
            )
        except Exception as exc:
            result = StepResult(
                system=system,
                status=StepStatus.ERROR,
                details=f"Unexpected error: {exc}",
                error_code="INTERNAL_ERROR",
                retryable=True,
            )
        return StepOutput(content=result.to_content())

    executor.__name__ = f"provision_{system}"
    return executor


# ---------------------------------------------------------------------------
# Provisioner instances
# ---------------------------------------------------------------------------

provision_slack = _make_provisioner(
    "slack",
    "Slack provisioned for {company}: channel=#welcome-{slug}",
)
provision_github = _make_provisioner(
    "github",
    "GitHub provisioned for {company}: repo={slug}-onboarding",
)
provision_newsletter = _make_provisioner(
    "newsletter",
    "Newsletter audience created for {company}: list_id=list_{slug}",
)
provision_grants = _make_provisioner(
    "grants",
    "Grants tracker initialized for {company}: grant_board=grants-{slug}",
)
