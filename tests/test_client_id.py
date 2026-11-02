"""Once a tool has been called with the customer's client ID, every agent is told
the ID, so an agent the conversation is handed to doesn't ask for it again.

Runs the real ``WealthManagementWorkflow`` with a scripted model, which records the
instructions each agent was given, and stub activities registered under the real
activity names.

Requires the Temporal test server (downloaded automatically on first run). No
OPENAI_API_KEY or Redis needed.
"""

import uuid
from typing import Any

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

import tests.scripted_model as scripted_model
from common.agent_constants import INVEST_AGENT_NAME, OPEN_ACCOUNT_AGENT_NAME, OPEN_ACCOUNT_INSTRUCTIONS
from temporal_supervisor.workflows.supervisor_workflow import WealthManagementWorkflow
from tests.scripted_model import handoff, message, scripted_client, send, tool

TASK_QUEUE = "test-client-id"
CLIENT_ID_NOTE = "The customer's client ID is 123"


@activity.defn(name="list_investments")
async def stub_list_investments(client_id: str) -> list:
    return [{"investment_id": "i-1", "name": "Checking", "balance": 1000.0}]


@activity.defn(name="delete_conversation")
async def stub_delete_conversation(workflow_id: str) -> bool:
    return True


@activity.defn(name="append_chat_interaction")
async def stub_append_chat_interaction(workflow_id: str, chat_interaction: Any) -> int:
    return 0


@pytest.fixture(scope="module")
async def temporal_env():
    async with await WorkflowEnvironment.start_local() as env:
        yield env


async def test_agents_are_told_the_client_id_once_a_tool_has_used_it(temporal_env):
    client = scripted_client(temporal_env.client)
    scripted_model.INSTRUCTIONS.clear()
    scripted_model.SCRIPT[:] = [
        # "What investments do I have?"
        message("What is your client ID?"),
        # "123"
        handoff(INVEST_AGENT_NAME),
        tool("list_investments", client_id="123"),
        message("You have a Checking account."),
        # "Open Car with 10,000"
        handoff(OPEN_ACCOUNT_AGENT_NAME),
        message("Opening it now."),
    ]

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WealthManagementWorkflow],
        activities=[stub_list_investments, stub_delete_conversation, stub_append_chat_interaction],
    ):
        handle = await client.start_workflow(
            WealthManagementWorkflow.run, id=f"client-id-test-{uuid.uuid4()}", task_queue=TASK_QUEUE
        )
        await send(handle, "What investments do I have?")
        await send(handle, "123")
        await send(handle, "Open Car with 10,000")
        assert scripted_model.SCRIPT == []
        await handle.signal(WealthManagementWorkflow.end_workflow)

    instructions = scripted_model.INSTRUCTIONS
    # Until list_investments is called, the ID is only in the conversation.
    assert not any(CLIENT_ID_NOTE in i for i in instructions[:3])
    # From the model call right after it, every agent is told the ID, including the
    # Open Account Agent the conversation is then handed to.
    assert all(CLIENT_ID_NOTE in i for i in instructions[3:])
    assert OPEN_ACCOUNT_INSTRUCTIONS in instructions[-1]
