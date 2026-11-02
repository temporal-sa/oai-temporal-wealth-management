"""A model for workflow tests that replays a script instead of calling OpenAI.

Set ``SCRIPT`` to the model's responses, in the order the workflow asks for them.
Each step is a handoff to the named agent, a tool call, or a message to the
customer. ``INSTRUCTIONS`` records the system instructions of every model call.
Run a worker with ``scripted_client`` and talk to the workflow with ``send``.
"""

import asyncio
import json
import uuid
from datetime import timedelta

from agents import Model, ModelProvider, ModelResponse, Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

from common.user_message import ProcessUserMessageInput
from temporal_supervisor.workflows.supervisor_workflow import WealthManagementWorkflow

SCRIPT: list = []
INSTRUCTIONS: list = []


def handoff(agent_name: str) -> tuple:
    return ("handoff", agent_name)


def tool(name: str, **arguments) -> tuple:
    return ("tool", name, arguments)


def message(text: str) -> tuple:
    return ("message", text)


class ScriptedModel(Model):
    async def get_response(self, system_instructions, input, model_settings, tools, output_schema,
                           handoffs, tracing, **kwargs) -> ModelResponse:
        INSTRUCTIONS.append(system_instructions)
        kind, value, *args = SCRIPT.pop(0)
        call_id = f"call-{uuid.uuid4()}"
        if kind == "handoff":
            name = next(h.tool_name for h in handoffs if h.agent_name == value)
            item = ResponseFunctionToolCall(type="function_call", call_id=call_id, name=name, arguments="{}")
        elif kind == "tool":
            item = ResponseFunctionToolCall(type="function_call", call_id=call_id, name=value,
                                            arguments=json.dumps(args[0]))
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


async def send(handle, prompt: str):
    """Send a customer message and return the agent's reply once it has been processed."""
    count = len(await handle.query(WealthManagementWorkflow.get_chat_history))
    await handle.signal(WealthManagementWorkflow.process_user_message, ProcessUserMessageInput(user_input=prompt))
    for _ in range(80):
        history = await handle.query(WealthManagementWorkflow.get_chat_history)
        if len(history) > count:
            return history[-1]
        await asyncio.sleep(0.25)
    raise AssertionError(f"no reply to {prompt!r}")


def scripted_client(client: Client) -> Client:
    """A copy of the client whose workers run model calls against the script."""
    plugin = OpenAIAgentsPlugin(
        model_provider=ScriptedModelProvider(),
        model_params=ModelActivityParameters(
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        ),
    )
    return Client(**{**client.config(), "plugins": [plugin]})
