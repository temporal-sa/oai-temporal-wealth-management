"""Off-topic questions are declined by the supervisor's prompt, not by a guardrail."""

import common.agent_constants as agent_constants
import oai_supervisor.main as standalone
import temporal_supervisor.workflows.supervisor_workflow as supervisor_workflow

DECLINE_BLOCK = [
    "You only help with wealth management: the customer's beneficiaries and investment accounts.",
    "If the customer asks about anything else (for example general knowledge, weather, news, or",
    "other financial products), politely decline, say that you can only help with beneficiaries",
    "and investment accounts, and do not answer the question. Then ask how you can help with",
    "their beneficiaries or investment accounts.",
]


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines()]


def test_supervisor_instructions_contain_the_decline_block():
    lines = _lines(agent_constants.SUPERVISOR_INSTRUCTIONS)
    start = lines.index(DECLINE_BLOCK[0])
    assert lines[start:start + len(DECLINE_BLOCK)] == DECLINE_BLOCK
    assert start < lines.index("# Routine")


def test_specialists_transfer_off_topic_questions_back():
    for instructions in (agent_constants.BENE_INSTRUCTIONS, agent_constants.INVEST_INSTRUCTIONS):
        assert "not related to the routine, transfer back to the supervisor agent" in instructions
    assert f"hand off to the {agent_constants.INVEST_AGENT_NAME}" in agent_constants.OPEN_ACCOUNT_INSTRUCTIONS


def test_no_guardrails_remain():
    for module in (agent_constants, supervisor_workflow, standalone):
        names = [name for name in vars(module) if "guardrail" in name.lower() or name.startswith("ROUTING_")]
        assert names == [], f"{module.__name__}: {names}"

    supervisor = supervisor_workflow.init_agents()
    seen, agents = set(), [supervisor]
    while agents:
        agent = agents.pop()
        if agent.name in seen:
            continue
        seen.add(agent.name)
        assert agent.input_guardrails == [] and agent.output_guardrails == []
        agents.extend(agent.handoffs)
    assert len(seen) == 4

    assert standalone.supervisor_agent.instructions == agent_constants.SUPERVISOR_INSTRUCTIONS
