"""Live test of the agent handoffs, against the real OpenAI model.

A customer starts with the Beneficiary Agent, then asks about their investments. The
Beneficiary Agent should hand the conversation back to the supervisor, which hands it to
the Investment Agent, all in the same turn, so the reply lists the investment accounts. It
must not ask the customer whether they want to be transferred, or announce the transfer.

The model decides whether to hand off, so this can't be checked with the scripted model.
It runs the real ``WealthManagementWorkflow`` with real OpenAI calls (through the same
model provider as the worker) and the real beneficiary and investment activities, which
only read data/*.json. Only the Redis-backed event stream activities are replaced, with
in-memory stand-ins, and the chaos flags are read as off.

Not part of the default ``uv run pytest`` run (the file name doesn't match ``test_*.py``),
because it calls the paid OpenAI API. Run it from the repository root with:

    source ./setoaikey.sh && uv run pytest tests/live_agent_handoffs.py -s

LIVE_TEST_RUNS=<n> repeats the conversation n times (default 1), since model output varies.
Skipped when OPENAI_API_KEY is not set. Requires the Temporal test server (downloaded
automatically on first run). No Redis needed.
"""

import os
import re
import uuid
from datetime import timedelta
from typing import Any

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

import temporal_supervisor.chaos as chaos
from common.agent_constants import BENE_AGENT_NAME, INVEST_AGENT_NAME, SUPERVISOR_AGENT_NAME
from common.chaos_manager import ChaosFlag
from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.investments import Investments
from temporal_supervisor.model_config import ChaosAwareOpenAIModel
from temporal_supervisor.retry_policies import LLM_RETRY_POLICY
from temporal_supervisor.workflows.supervisor_workflow import WealthManagementWorkflow
from tests.scripted_model import send

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"),
                                reason="OPENAI_API_KEY not set: source ./setoaikey.sh first")

RUNS = max(1, int(os.getenv("LIVE_TEST_RUNS", "1")))
TASK_QUEUE = "agent-handoffs-live-test"
LLM_TASK_QUEUE = f"{TASK_QUEUE}-llm"
# Client 123's accounts in data/investments.json and beneficiaries in data/beneficiaries.json
CLIENT_123_ACCOUNTS = ["Checking", "Savings", "401K"]
CLIENT_123_BENEFICIARIES = ["John", "Jane", "Joan"]
TRANSFER = re.compile(r"transfer", re.IGNORECASE)

# The conversation, kept in memory instead of the Redis event stream
INTERACTIONS: list = []


@activity.defn(name="delete_conversation")
async def memory_delete_conversation(workflow_id: str) -> bool:
    return True


@activity.defn(name="append_chat_interaction")
async def memory_append_chat_interaction(workflow_id: str, chat_interaction: Any) -> int:
    INTERACTIONS.append(chat_interaction)
    return len(INTERACTIONS)


@activity.defn(name="append_status_update")
async def memory_append_status_update(workflow_id: str, status_update: Any) -> int:
    return 0


@pytest.fixture(scope="module")
async def temporal_env():
    async with await WorkflowEnvironment.start_local() as env:
        yield env


@pytest.fixture
def chaos_off(monkeypatch):
    """Chaos flags read as off. They fail open without Redis anyway, but a local Redis
    left with a flag on would otherwise break the run."""
    async def is_enabled(flag: ChaosFlag) -> bool:
        return False

    monkeypatch.setattr(chaos, "is_enabled", is_enabled)


# What each agent said, as (agent name, text), from every model call's output. The trace
# only records handoffs and tool calls, and the reply concatenates every agent's messages.
AGENT_MESSAGES: list = []
AGENT_BY_INSTRUCTIONS = {
    "You are a beneficiary agent": BENE_AGENT_NAME,
    "You are an investment agent": INVEST_AGENT_NAME,
    "You only help with wealth management": SUPERVISOR_AGENT_NAME,
}


def _agent_name(system_instructions: str | None) -> str:
    return next((name for marker, name in AGENT_BY_INSTRUCTIONS.items()
                 if marker in (system_instructions or "")), "Other Agent")


def live_client(client: Client) -> Client:
    """A copy of the client whose workers run model calls against OpenAI, on their own task
    queue, as the real worker does, recording what each agent said."""
    from temporal_supervisor.run_worker import CustomModelProvider

    class RecordingModel(ChaosAwareOpenAIModel):
        async def get_response(self, system_instructions, *args, **kwargs):
            response = await super().get_response(system_instructions, *args, **kwargs)
            for item in response.output:
                if getattr(item, "type", None) == "message":
                    text = "".join(getattr(c, "text", "") for c in item.content)
                    AGENT_MESSAGES.append((_agent_name(system_instructions), text))
                elif getattr(item, "type", None) == "function_call":
                    AGENT_MESSAGES.append((_agent_name(system_instructions), f"<calls {item.name}>"))
            return response

    class RecordingProvider(CustomModelProvider):
        def get_model(self, model_name):
            model = super().get_model(model_name)
            return RecordingModel(model=model.model, openai_client=model._client)

    plugin = OpenAIAgentsPlugin(
        model_provider=RecordingProvider(),
        model_params=ModelActivityParameters(
            task_queue=LLM_TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=LLM_RETRY_POLICY,
        ),
    )
    return Client(**{**client.config(), "plugins": [plugin]})


async def test_investment_question_asked_while_talking_to_the_beneficiary_agent(temporal_env, chaos_off):
    client = live_client(temporal_env.client)
    passed, chatter, failures = 0, 0, []

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WealthManagementWorkflow],
        activities=[
            Beneficiaries.list_beneficiaries,
            Investments.list_investments,
            memory_delete_conversation,
            memory_append_chat_interaction,
            memory_append_status_update,
        ],
    ), Worker(client, task_queue=LLM_TASK_QUEUE):
        for run in range(1, RUNS + 1):
            handle = await client.start_workflow(
                WealthManagementWorkflow.run, id=f"agent-handoffs-live-{run}-{uuid.uuid4()}",
                task_queue=TASK_QUEUE,
            )
            transcript: list[str] = []

            async def say(text: str):
                AGENT_MESSAGES.clear()
                reply = await send(handle, text)
                transcript.extend([f"Customer: {text}", f"Agent: {reply.text_response}",
                                   *[f"  trace: {line}" for line in (reply.agent_trace or "").splitlines()],
                                   *[f"  [{name}]: {said}" for name, said in AGENT_MESSAGES]])
                return reply

            def context() -> str:
                return f"\nRun {run} of {RUNS}:\n" + "\n".join(transcript)

            try:
                await say("Who are my beneficiaries?")
                beneficiaries = await say("123")
                for name in CLIENT_123_BENEFICIARIES:
                    assert name in beneficiaries.text_response, f"beneficiary {name} not listed{context()}"

                investments = await say("What investments do I have?")
                trace = investments.agent_trace or ""
                # Count transfer chatter from the Beneficiary Agent even when the run passes:
                # a later agent's reply can hide it in the UI, but the workflow concatenates
                # every agent's messages into the reply, so it shows up there.
                bene_said = [said for name, said in AGENT_MESSAGES
                             if name == BENE_AGENT_NAME and not said.startswith("<calls")]
                if TRANSFER.search(investments.text_response) or any(TRANSFER.search(s) for s in bene_said):
                    chatter += 1
                for account in CLIENT_123_ACCOUNTS:
                    assert account in investments.text_response, f"account {account} not listed{context()}"
                assert not TRANSFER.search(investments.text_response), f"the agent talked about a transfer{context()}"
                assert not any(TRANSFER.search(s) for s in bene_said), \
                    f"the Beneficiary Agent talked about a transfer instead of just handing off{context()}"
                assert not re.search(r"client id", investments.text_response, re.IGNORECASE), \
                    f"asked for the client ID again{context()}"
                assert f"Handed off from {BENE_AGENT_NAME}" in trace, \
                    f"the Beneficiary Agent did not hand off{context()}"
                assert re.search(rf"Handed off from .* to {INVEST_AGENT_NAME}", trace), \
                    f"no handoff to the Investment Agent{context()}"
                assert f"{INVEST_AGENT_NAME}: Calling a tool" in trace, \
                    f"the Investment Agent did not call list_investments{context()}"
                passed += 1
            except AssertionError as e:
                failures.append(str(e))
            finally:
                await handle.signal(WealthManagementWorkflow.end_workflow)
                await handle.result()
                print(context())

    print(f"\n{passed} of {RUNS} runs passed; {chatter} had transfer chatter")
    assert not failures, f"{len(failures)} of {RUNS} runs failed:\n" + "\n\n".join(failures)
