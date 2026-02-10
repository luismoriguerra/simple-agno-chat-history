import asyncio

import pytest
import scenario

from src.team import supervisor_team


class OnboardingTeamAdapter(scenario.AgentAdapter):
    """Wraps the supervisor_team so Scenario can drive multi-turn conversations."""

    def __init__(self) -> None:
        self.team = supervisor_team

    async def call(self, input: scenario.AgentInput) -> scenario.AgentReturnTypes:
        response = await asyncio.to_thread(
            self.team.run,
            input.last_new_user_message_str(),
            session_id=input.thread_id,
        )
        if response.content is None:
            return ""
        return str(response.content)


async def _run_onboarding_scenario(
    name: str,
    description: str,
    criteria: list[str],
) -> None:
    """Shared helper -- runs a scenario with the standard agent trio and asserts success."""
    result = await scenario.run(
        name=name,
        description=description,
        agents=[
            OnboardingTeamAdapter(),
            scenario.UserSimulatorAgent(),
            scenario.JudgeAgent(criteria=criteria),
        ],
        max_turns=8,
    )
    assert result.success, f"Scenario '{name}' failed"


@pytest.mark.agent_test
@pytest.mark.asyncio_concurrent(group="onboarding")
async def test_onboarding_happy_path() -> None:
    """User requests onboarding for a specific company and expects a full execution."""
    await _run_onboarding_scenario(
        name="onboarding happy path",
        description="User wants to onboard a company called Acme Corp into all enterprise systems.",
        criteria=[
            "Agent should ask clarifying questions only if needed",
            "Agent should produce an onboarding plan",
            "Agent should execute the onboarding workflow",
            "Agent should return a summary with SUCCESS or FAIL per system",
            "Summary should mention all 4 systems: Slack, GitHub, Newsletter, and Grants",
        ],
    )


@pytest.mark.agent_test
@pytest.mark.asyncio_concurrent(group="onboarding")
async def test_onboarding_missing_info() -> None:
    """User provides a vague request without specifying a company name."""
    await _run_onboarding_scenario(
        name="onboarding missing info",
        description="User says 'I need to onboard someone' without specifying a company name.",
        criteria=[
            "Agent should ask for the company name or other missing information",
            "Agent should not proceed with the workflow without knowing the company name",
            "Agent should be polite and concise in its follow-up questions",
        ],
    )


@pytest.mark.agent_test
@pytest.mark.asyncio_concurrent(group="onboarding")
async def test_onboarding_multiple_companies() -> None:
    """User asks to onboard two companies at once."""
    await _run_onboarding_scenario(
        name="onboarding multiple companies",
        description="User asks to onboard two companies: Acme Corp and Globex Inc.",
        criteria=[
            "Agent should handle the request or clearly explain limitations",
            "Agent should not produce incorrect or mixed-up provisioning results",
            "If the agent handles both, each company should have its own provisioning summary",
        ],
    )
