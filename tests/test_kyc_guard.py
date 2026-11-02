"""The approve_kyc tool only approves KYC after the customer has seen and confirmed
their details for that account opening.

The first test calls the tool directly for the blocked cases: they return before
calling any activity, so the tool can run outside a workflow. The second runs the
real ``WealthManagementWorkflow`` with a scripted model that calls approve_kyc too
early, and stub activities (registered under the real activity names) that record
which account openings KYC was actually approved for.

Requires the Temporal test server (downloaded automatically on first run). No
OPENAI_API_KEY or Redis needed.
"""

import asyncio
import json
import uuid
from datetime import timedelta
from typing import Any

import pytest
from agents import Model, ModelProvider, ModelResponse, Usage
from agents.tool_context import ToolContext
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
from temporalio import activity
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from common.agent_constants import INVEST_AGENT_NAME, OPEN_ACCOUNT_AGENT_NAME
from common.user_message import ProcessUserMessageInput
from temporal_supervisor.workflows.supervisor_workflow import (
    WealthManagementContext,
    WealthManagementWorkflow,
    approve_kyc,
)

WORKFLOW_ID = "OpenAccount-test-123-Education"


async def _approve(context: WealthManagementContext) -> str:
    arguments = json.dumps({"workflow_id": WORKFLOW_ID})
    return await approve_kyc.on_invoke_tool(
        ToolContext(context=context, tool_name="approve_kyc", tool_call_id="call-1", tool_arguments=arguments),
        arguments,
    )


@pytest.mark.parametrize(
    "shown_turns",
    [
        {},  # details never shown for this opening
        {"OpenAccount-test-123-Car": 2},  # only shown for an earlier opening
        {WORKFLOW_ID: 3},  # shown in the current turn; the customer hasn't replied yet
    ],
)
async def test_kyc_is_not_approved_until_the_customer_confirms(shown_turns):
    context = WealthManagementContext(turn=3, kyc_details_shown_turn=shown_turns)
    result = await _approve(context)
    assert result.startswith("KYC was not approved")


TASK_QUEUE = "test-kyc-guard"
CAR = "OpenAccount-test-123-Car"
VACATION = "OpenAccount-test-123-Vacation"

# Account openings that KYC was approved for, in order, recorded worker-side.
APPROVED: list = []
# The model's responses, in the order the workflow asks for them. Each step is a
# handoff to the named agent, a tool call, or a message to the customer.
SCRIPT: list = []


@activity.defn(name="get_current_client_info")
async def stub_get_current_client_info(workflow_id: str) -> dict:
    return {
        "client_id": "123", "first_name": "Sam", "last_name": "Doe", "address": "1 Main St",
        "phone": "555", "email": "s@example.com", "marital_status": "single",
    }


@activity.defn(name="approve_kyc")
async def stub_approve_kyc(workflow_id: str) -> None:
    APPROVED.append(workflow_id)


@activity.defn(name="delete_conversation")
async def stub_delete_conversation(workflow_id: str) -> bool:
    return True


@activity.defn(name="append_chat_interaction")
async def stub_append_chat_interaction(workflow_id: str, chat_interaction: Any) -> int:
    return 0


class ScriptedModel(Model):
    async def get_response(self, system_instructions, input, model_settings, tools, output_schema,
                           handoffs, tracing, **kwargs) -> ModelResponse:
        kind, value, *args = SCRIPT.pop(0)
        call_id = f"call-{uuid.uuid4()}"
        if kind == "handoff":
            name = next(h.tool_name for h in handoffs if h.agent_name == value)
            item = ResponseFunctionToolCall(type="function_call", call_id=call_id, name=name, arguments="{}")
        elif kind == "tool":
            item = ResponseFunctionToolCall(type="function_call", call_id=call_id, name=value,
                                            arguments=json.dumps({"workflow_id": args[0]}))
        else:
            item = ResponseOutputMessage(
                id=f"msg-{call_id}", type="message", role="assistant", status="completed",
                content=[ResponseOutputText(type="output_text", text=value, annotations=[])],
            )
        return ModelResponse(output=[item], usage=Usage(), response_id=None)

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError


class ScriptedModelProvider(ModelProvider):
    def get_model(self, model_name):
        return ScriptedModel()


@pytest.fixture(scope="module")
async def temporal_env():
    async with await WorkflowEnvironment.start_local() as env:
        yield env


async def _send(handle, prompt: str):
    """Send a customer message and return the agent's reply once it has been processed."""
    count = len(await handle.query(WealthManagementWorkflow.get_chat_history))
    await handle.signal(WealthManagementWorkflow.process_user_message, ProcessUserMessageInput(user_input=prompt))
    for _ in range(80):
        history = await handle.query(WealthManagementWorkflow.get_chat_history)
        if len(history) > count:
            return history[-1]
        await asyncio.sleep(0.25)
    raise AssertionError(f"no reply to {prompt!r}")


async def test_kyc_approved_only_after_the_customer_replies(temporal_env):
    plugin = OpenAIAgentsPlugin(
        model_provider=ScriptedModelProvider(),
        model_params=ModelActivityParameters(
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        ),
    )
    client = Client(**{**temporal_env.client.config(), "plugins": [plugin]})
    APPROVED.clear()
    SCRIPT[:] = [
        # Customer asks to open Car. The model shows their details, then approves
        # KYC in the same turn without waiting for the customer to answer.
        ("handoff", INVEST_AGENT_NAME),
        ("handoff", OPEN_ACCOUNT_AGENT_NAME),
        ("tool", "get_current_client_info", CAR),
        ("tool", "approve_kyc", CAR),
        ("message", "Are these details correct?"),
        # Customer confirms.
        ("tool", "approve_kyc", CAR),
        ("message", "KYC approved."),
        # Customer asks to open Vacation. The model treats the Car confirmation as
        # approval for this opening too.
        ("tool", "get_current_client_info", VACATION),
        ("tool", "approve_kyc", VACATION),
        ("message", "Are these details still correct?"),
        # Customer confirms.
        ("tool", "approve_kyc", VACATION),
        ("message", "KYC approved."),
    ]

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WealthManagementWorkflow],
        activities=[stub_get_current_client_info, stub_approve_kyc,
                    stub_delete_conversation, stub_append_chat_interaction],
    ):
        handle = await client.start_workflow(
            WealthManagementWorkflow.run, id=f"kyc-guard-test-{uuid.uuid4()}", task_queue=TASK_QUEUE
        )

        reply = await _send(handle, "Please open an account called Car.")
        assert "KYC was not approved" in reply.json_response
        assert APPROVED == []

        reply = await _send(handle, "Yes, that's correct.")
        assert "KYC approved" in reply.json_response
        assert APPROVED == [CAR]

        reply = await _send(handle, "Now open one called Vacation.")
        assert "KYC was not approved" in reply.json_response
        assert APPROVED == [CAR]

        reply = await _send(handle, "Yes, still correct.")
        assert "KYC approved" in reply.json_response
        assert APPROVED == [CAR, VACATION]

        assert SCRIPT == []
        await handle.signal(WealthManagementWorkflow.end_workflow)
