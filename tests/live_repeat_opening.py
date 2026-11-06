"""Live test: asking to open the same account again starts a new account opening, with its own KYC.

The customer asks for their beneficiaries, gives client ID 123, asks for their investments,
opens "Vacation" with $13,000, confirms their details for KYC, then asks to open "Vacation"
with $13,000 again while the first opening is waiting for compliance review. The agent must
start a second account opening (a second child workflow) and show the client's details for
KYC again, instead of answering from the conversation history.

The model decides whether to call the tool, so this can't be checked with the scripted model.
It runs the real ``WealthManagementWorkflow`` and ``OpenInvestmentAccountWorkflow`` with real
OpenAI calls (through the same model provider as the worker), and the real activities that
only read data/*.json (beneficiaries, investments, validation, client details). The
activities that would connect to the real Temporal service (get_current_client_info,
approve_kyc, update_client_details) are replaced with stand-ins that do the same through the
test server, update_client_details doesn't save, the Redis-backed event stream activities are
replaced with in-memory stand-ins, and the chaos flags are read as off (so no promo code).

Not part of the default ``uv run pytest`` run (the file name doesn't match ``test_*.py``),
because it calls the paid OpenAI API. Run it from the repository root with:

    source ./setoaikey.sh && uv run pytest tests/live_repeat_opening.py -s

LIVE_TEST_RUNS=<n> repeats the conversation n times (default 1), since model output varies.
Skipped when OPENAI_API_KEY is not set. Requires the Temporal test server (downloaded
automatically on first run). No Redis needed.
"""

import asyncio
import os
import uuid
from typing import Any

import pytest
from temporalio import activity
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Worker

from common.agent_constants import INVEST_AGENT_NAME, OPEN_ACCOUNT_AGENT_NAME
from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.clients import ClientActivities
from temporal_supervisor.activities.investments import Investments
from temporal_supervisor.activities.open_account import client_helper
from temporal_supervisor.workflows.open_account_workflow import OpenInvestmentAccountWorkflow
from temporal_supervisor.workflows.supervisor_workflow import WealthManagementWorkflow
from tests import live_agent_handoffs as live
from tests.live_agent_handoffs import (AGENT_BY_INSTRUCTIONS, AGENT_MESSAGES, chaos_off,  # noqa: F401
                                       live_client, memory_append_chat_interaction,
                                       memory_append_status_update, memory_delete_conversation,
                                       temporal_env)
from tests.scripted_model import send

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"),
                                reason="OPENAI_API_KEY not set: source ./setoaikey.sh first")

RUNS = max(1, int(os.getenv("LIVE_TEST_RUNS", "1")))
TASK_QUEUE = live.TASK_QUEUE
OPEN_VACATION = "Open Vacation with $13,000"
# Client 123's details in data/clients.json
KYC_DETAILS = ["Don", "123 Main Street"]

AGENT_BY_INSTRUCTIONS.setdefault("You are responsible for handling the opening a new investment account",
                                 OPEN_ACCOUNT_AGENT_NAME)

# Child workflow IDs passed to the activities, recorded worker-side.
APPROVED: list = []
TEST_CLIENT: list = []


def _child(workflow_id: str):
    return TEST_CLIENT[0].get_workflow_handle_for(OpenInvestmentAccountWorkflow.run, workflow_id)


@activity.defn(name="get_current_client_info")
async def via_test_server_get_current_client_info(workflow_id: str) -> Any:
    # By name, as the real activity does, so the result keeps the client ID.
    return await _child(workflow_id).execute_update("get_client_details")


@activity.defn(name="approve_kyc")
async def via_test_server_approve_kyc(workflow_id: str) -> None:
    APPROVED.append(workflow_id)
    await _child(workflow_id).signal(OpenInvestmentAccountWorkflow.verify_kyc)


@activity.defn(name="update_client_details")
async def via_test_server_update_client_details(workflow_id: str, client_details: Any) -> str:
    # Completes KYC without saving the changes to data/clients.json.
    APPROVED.append(workflow_id)
    await _child(workflow_id).signal(OpenInvestmentAccountWorkflow.verify_kyc)
    return "Client details updated."


async def _started(workflow_id: str) -> bool:
    """Whether a child workflow with this ID was started."""
    try:
        await TEST_CLIENT[0].get_workflow_handle(workflow_id).describe()
        return True
    except RPCError as e:
        if e.status == RPCStatusCode.NOT_FOUND:
            return False
        raise


async def test_opening_the_same_account_again_starts_a_new_opening(temporal_env, chaos_off):
    client = live_client(temporal_env.client)
    TEST_CLIENT[:] = [temporal_env.client]
    passed, failures = 0, []

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[WealthManagementWorkflow],
        activities=[
            Beneficiaries.list_beneficiaries,
            Investments.list_investments,
            Investments.validate_new_account,
            Investments.find_promotion,
            via_test_server_get_current_client_info,
            via_test_server_approve_kyc,
            via_test_server_update_client_details,
            memory_delete_conversation,
            memory_append_chat_interaction,
            memory_append_status_update,
        ],
    ), Worker(
        # The open-account tool starts the child on the Open Account task queue.
        client,
        task_queue=client_helper.taskQueueOpenAccount,
        workflows=[OpenInvestmentAccountWorkflow],
        activities=[ClientActivities.get_client],
    ), Worker(client, task_queue=live.LLM_TASK_QUEUE):
        for run in range(1, RUNS + 1):
            chat_id = f"repeat-opening-live-{run}-{uuid.uuid4()}"
            handle = await client.start_workflow(WealthManagementWorkflow.run, id=chat_id,
                                                 task_queue=TASK_QUEUE)
            APPROVED.clear()
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
                await say("123")
                await say("what investments do I have?")
                first = await say(OPEN_VACATION)
                for detail in KYC_DETAILS:
                    assert detail in first.text_response, f"KYC details ({detail}) not shown for the first opening{context()}"
                await say("Yes")
                second = await say(OPEN_VACATION)
                for detail in KYC_DETAILS:
                    assert detail in second.text_response, f"KYC details ({detail}) not shown for the second opening{context()}"
                prefix = f"OpenAccount-{chat_id}-123-Vacation"
                started = {n: await _started(f"{prefix}-{n}") for n in (1, 2, 3)}
                transcript.append(f"  child workflows started: "
                                  f"{[f'...-Vacation-{n}' for n, yes in started.items() if yes]}")
                assert started == {1: True, 2: True, 3: False}, \
                    f"expected child workflows ending -Vacation-1 and -Vacation-2{context()}"
                assert not any(c.endswith("-Vacation-2") for c in APPROVED), \
                    f"the second opening's KYC was approved without the customer confirming it{context()}"
                passed += 1
            except AssertionError as e:
                failures.append(str(e))
            finally:
                await handle.signal(WealthManagementWorkflow.end_workflow)
                try:
                    await asyncio.wait_for(handle.result(), timeout=30)
                except asyncio.TimeoutError:
                    await handle.terminate("the chat workflow did not end")
                print(context())

    print(f"\n{passed} of {RUNS} runs passed")
    assert not failures, f"{len(failures)} of {RUNS} runs failed:\n" + "\n\n".join(failures)
