# Writing Agents with Scenario Testing in a TDD Style

This guide explains how to develop LLM-powered agents using Test-Driven Development (TDD) principles with scenario-based testing.

## The Core Idea

Traditional TDD follows: **write a failing test, write code to pass it, refactor**.

With LLM agents, the cycle becomes: **write a failing scenario, refine instructions to pass it, iterate**.

The "code" you're writing is mostly natural language instructions, not traditional logic. The tests verify observable behavior in conversation transcripts.

## The Three-Actor Model

Scenario tests use three agents working together:

```
UserSimulatorAgent  --->  YourAgent  --->  JudgeAgent
   (plays a role)      (under test)     (evaluates criteria)
```

- **UserSimulatorAgent**: Simulates a user based on a description you provide
- **YourAgent**: The agent under test, wrapped in an adapter
- **JudgeAgent**: Evaluates the conversation against your criteria

## Step 1: Define the Behavior Contract First

Before writing any agent code, define what the agent should do as testable criteria. Each criterion should be a clear, observable behavior that a judge LLM can verify from a conversation transcript.

```python
criteria=[
    "Agent should ask for the company name if not provided",
    "Summary should mention Slack, GitHub, Newsletter, and Grants",
    "Agent should be concise in follow-up questions",
]
```

### Rules for Good Criteria

- Each criterion is a single, specific behavior (not compound)
- It references something visible in the conversation output
- It avoids internal implementation details the judge can't see
- It uses words like "should mention", "should ask", "should not proceed"

### Bad vs Good Criteria Examples

| Bad | Good |
|-----|------|
| "Agent should handle the request well" | "Agent should return a summary with SUCCESS or FAIL per system" |
| "Agent should be helpful" | "Agent should ask for the company name if not provided" |
| "Agent should work correctly" | "Summary should mention all 4 systems: Slack, GitHub, Newsletter, and Grants" |

## Step 2: Write the Scenario Test (Red Phase)

Write the test before refining the agent. The test will fail initially -- that's the point.

```python
import pytest
import scenario

@pytest.mark.agent_test
async def test_onboarding_missing_info():
    result = await scenario.run(
        name="onboarding missing info",
        description="User says 'I need to onboard someone' without a company name.",
        agents=[
            OnboardingTeamAdapter(),          # your agent wrapped in an adapter
            scenario.UserSimulatorAgent(),     # simulates a user based on description
            scenario.JudgeAgent(criteria=[     # evaluates the conversation
                "Agent should ask for the company name",
                "Agent should not proceed without the company name",
                "Agent should be polite and concise",
            ]),
        ],
        max_turns=8,
    )
    assert result.success, f"Scenario failed: {result.reasoning}"
```

### Writing the Adapter

The adapter wraps your agent so the test framework can drive conversations:

```python
import asyncio
import scenario

class OnboardingTeamAdapter(scenario.AgentAdapter):
    def __init__(self):
        self.team = supervisor_team  # your agent/team

    async def call(self, input: scenario.AgentInput) -> scenario.AgentReturnTypes:
        response = await asyncio.to_thread(
            self.team.run,
            input.last_new_user_message_str(),
            session_id=input.thread_id,
        )
        return str(response.content or "")
```

Keep adapters thin -- they should only translate between the test framework and your agent's API.

## Step 3: Write Minimal Agent Instructions (Green Phase)

Start with the simplest instructions that could satisfy the criteria. Don't over-engineer.

```python
# First attempt -- too vague (will fail)
instructions=["Help the user onboard companies."]

# Second attempt -- targeted to pass criteria
instructions=[
    "You onboard companies into 4 systems: Slack, GitHub, Newsletter, and Grants.",
    "The company name is required. If missing, ask for it concisely.",
    "Return a summary listing each system with SUCCESS or FAIL.",
]
```

### The Key Insight

**Every test criterion should trace back to a specific instruction.**

If a criterion says "mention all 4 systems", an instruction must name those 4 systems. The LLM won't infer what you didn't state.

| Criterion | Required Instruction |
|-----------|---------------------|
| "Summary should mention Slack, GitHub, Newsletter, and Grants" | "You onboard companies into 4 systems: Slack, GitHub, Newsletter, and Grants" |
| "Agent should ask for the company name" | "The company name is required. If missing, ask for it concisely" |
| "Agent should be concise" | "Keep follow-up questions short -- one or two sentences, no bullet lists" |

## Step 4: Run and Read the Judge's Reasoning (Refactor Phase)

The judge output is your debugging tool. It tells you exactly which criteria passed and why each one failed:

```
Criterion 3 FAIL: Agent was polite but NOT concise -- it provided
a detailed plan, formatting, and multiple bullet points.
```

This tells you exactly what instruction to add:

```python
"Keep follow-up questions short -- one or two sentences, no bullet lists."
```

## Step 5: Build Scenarios Incrementally

Start with the simplest happy-path scenario and layer complexity:

```
Test 1: Happy path       -- user gives all info, agent executes
Test 2: Missing info     -- user omits required fields, agent asks
Test 3: Edge case        -- user gives two companies at once
Test 4: Adversarial      -- user gives contradictory info
```

Each new scenario may cause you to refine instructions. The earlier tests act as regression guards -- if a new instruction breaks them, you know immediately.

## The TDD Loop

```
1. Write scenario + criteria for a new behavior
2. Run test --> FAIL (red)
3. Add/refine agent instructions
4. Run test --> PASS (green)
5. Run ALL tests --> verify no regressions
6. Refine instructions for clarity (refactor)
7. Repeat for next behavior
```

## The Mapping Pattern

| Traditional TDD | Agent TDD |
|-----------------|-----------|
| Unit test | Scenario with criteria |
| Source code | Agent instructions |
| Assertion failure | Judge criterion failure |
| Stack trace | Judge reasoning |
| Refactor code | Refine instructions |
| Code coverage | Criteria coverage |

## Practical Guidelines

### 1. One Scenario Per Behavior

Don't test "the whole onboarding flow" in one scenario. Test "happy path", "missing info", "multiple companies" separately.

### 2. Criteria Should Be Strict and Unambiguous

The judge evaluates strictly. Vague criteria lead to inconsistent results.

### 3. Instructions Must Be Explicit

The LLM doesn't know your system has 4 subsystems unless you tell it. Don't assume it will infer structure from the workflow code -- it sees the output, not the source.

### 4. Use `max_turns` to Enforce Efficiency

Setting `max_turns=8` means the agent must complete the task in a reasonable number of exchanges. If it can't, the instructions need to be more directive.

### 5. Treat Instruction Changes Like Code Changes

When you modify instructions to fix a failing scenario, re-run all scenarios. Instructions interact -- making the agent more concise might cause it to skip information another test requires.

### 6. Match Test Infrastructure to Production

If your agent uses Claude via AWS Bedrock, your test's simulated user and judge must also use compatible credentials. Configure this in `conftest.py`:

```python
import scenario
from dotenv import load_dotenv

load_dotenv()

def pytest_configure(config):
    scenario.configure(
        default_model="bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        cache_key="v1",
    )
```

## Example: Complete Test File

```python
import asyncio
import pytest
import scenario
from src.team import supervisor_team


class OnboardingTeamAdapter(scenario.AgentAdapter):
    def __init__(self):
        self.team = supervisor_team

    async def call(self, input: scenario.AgentInput) -> scenario.AgentReturnTypes:
        response = await asyncio.to_thread(
            self.team.run,
            input.last_new_user_message_str(),
            session_id=input.thread_id,
        )
        return str(response.content or "")


async def _run_scenario(name: str, description: str, criteria: list[str]) -> None:
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
@pytest.mark.asyncio
async def test_happy_path():
    await _run_scenario(
        name="onboarding happy path",
        description="User wants to onboard Acme Corp into all enterprise systems.",
        criteria=[
            "Agent should ask clarifying questions only if needed",
            "Agent should produce an onboarding plan",
            "Agent should execute the onboarding workflow",
            "Agent should return a summary with SUCCESS or FAIL per system",
            "Summary should mention all 4 systems: Slack, GitHub, Newsletter, and Grants",
        ],
    )


@pytest.mark.agent_test
@pytest.mark.asyncio
async def test_missing_info():
    await _run_scenario(
        name="onboarding missing info",
        description="User says 'I need to onboard someone' without a company name.",
        criteria=[
            "Agent should ask for the company name",
            "Agent should not proceed without the company name",
            "Agent should be polite and concise",
        ],
    )
```

## The Mindset Shift

You're not debugging algorithms, you're debugging **communication**.

- The agent fails because you didn't tell it clearly enough what to do
- The judge fails criteria because the agent's output didn't match the specific words the criteria expect
- The fix is almost always better instructions, not more code

## Summary

1. Define behavior as testable criteria before writing agent code
2. Write failing scenario tests that specify user behavior and success criteria
3. Write minimal instructions targeted at passing each criterion
4. Use judge reasoning to debug failures and refine instructions
5. Build scenarios incrementally from happy path to edge cases
6. Treat instruction changes like code changes -- run all tests after each change
