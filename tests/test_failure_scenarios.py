"""Tests for the failure scenarios demonstrated from the UI chaos panel.

The saga tests run the real ``OpenInvestmentAccountWorkflow`` against stub
activities (registered under the real activity names) that record the order they
were called in and fail on demand, so no Redis or data files are touched.

Requires the Temporal test server (downloaded automatically on first run). No
OPENAI_API_KEY or Redis needed.
"""

import asyncio
import json
import uuid
from typing import Any

import pytest
from openai import AsyncOpenAI
from temporalio import activity
from temporalio.api.enums.v1 import EventType
from temporalio.client import WorkflowExecutionStatus
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker

import temporal_supervisor.chaos as chaos
import temporal_supervisor.model_config as model_config
from common.chaos_manager import ChaosFlag
from common.funding_manager import FundingManager, InsufficientFundsError
from temporal_supervisor.activities.investments import Investments
from temporal_supervisor.workflows.open_account_workflow import (
    OpenInvestmentAccountInput,
    OpenInvestmentAccountWorkflow,
)

TASK_QUEUE = "test-failure-scenarios"
CLIENT_ID = "C-1"
INVESTMENT_ID = "i-test"

# Activity calls, in order, recorded worker-side (same process as the test).
CALLS: list = []
# Transfer IDs passed to debit_linked_account, across tests.
TRANSFER_IDS: list = []
# Per-test failure behavior, keyed by activity name: "reject" raises a
# non-retryable error; an int N fails the first N attempts with a transient error.
FAILURES: dict = {}


def _maybe_fail(name: str) -> None:
    behavior = FAILURES.get(name)
    if behavior == "reject":
        raise ApplicationError(f"{name} rejected", type="Rejected", non_retryable=True)
    if isinstance(behavior, int) and activity.info().attempt <= behavior:
        raise ConnectionError(f"{name} unavailable")


@activity.defn(name="get_client")
async def stub_get_client(client_id: str) -> dict:
    CALLS.append("get_client")
    return {
        "client_id": client_id, "first_name": "Sam", "last_name": "Doe", "address": "1 Main St",
        "phone": "555", "email": "s@example.com", "marital_status": "single",
    }


@activity.defn(name="open_investment")
async def stub_open_investment(new_account: Any) -> dict:
    CALLS.append(f"open_investment#{activity.info().attempt}")
    _maybe_fail("open_investment")
    return {"investment_id": INVESTMENT_ID, "name": "Test", "balance": 500.0}


@activity.defn(name="remove_investment")
async def stub_remove_investment(client_id: str, investment_id: str) -> bool:
    CALLS.append(f"remove_investment:{investment_id}")
    return True


@activity.defn(name="debit_linked_account")
async def stub_debit(client_id: str, amount: float, transfer_id: str) -> dict:
    CALLS.append(f"debit:{amount}")
    TRANSFER_IDS.append(transfer_id)
    _maybe_fail("debit_linked_account")
    return {}


@activity.defn(name="credit_linked_account")
async def stub_credit(client_id: str, amount: float, transfer_id: str) -> dict:
    CALLS.append(f"credit:{amount}")
    assert transfer_id.endswith("-refund")
    return {}


@activity.defn(name="register_account")
async def stub_register(client_id: str, investment_id: str, amount: float) -> str:
    CALLS.append("register")
    _maybe_fail("register_account")
    return "CUST-1"


STUB_ACTIVITIES = [
    stub_get_client, stub_open_investment, stub_remove_investment,
    stub_debit, stub_credit, stub_register,
]


@pytest.fixture(scope="module")
async def temporal_env():
    async with await WorkflowEnvironment.start_local() as env:
        yield env


@pytest.fixture
def chaos_flags(monkeypatch):
    """Turn chaos flags on without Redis: add flags to the returned set."""
    enabled = set()

    async def is_enabled(flag: ChaosFlag) -> bool:
        return flag in enabled

    async def record_event(flag: ChaosFlag) -> None:
        pass

    monkeypatch.setattr(chaos, "is_enabled", is_enabled)
    monkeypatch.setattr(chaos, "record_event", record_event)
    return enabled


async def _start_and_approve(env: WorkflowEnvironment, failures: dict, promo_code=None, workflow_id=None):
    CALLS.clear()
    FAILURES.clear()
    FAILURES.update(failures)
    handle = await env.client.start_workflow(
        OpenInvestmentAccountWorkflow.run,
        OpenInvestmentAccountInput(
            client_id=CLIENT_ID, account_name="Test", initial_amount=500.0, promo_code=promo_code
        ),
        id=workflow_id or f"open-account-test-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    await handle.signal(OpenInvestmentAccountWorkflow.verify_kyc)
    await handle.signal(OpenInvestmentAccountWorkflow.compliance_approved)
    return handle


def _worker(env: WorkflowEnvironment) -> Worker:
    return Worker(
        env.client,
        task_queue=TASK_QUEUE,
        workflows=[OpenInvestmentAccountWorkflow],
        activities=STUB_ACTIVITIES,
    )


async def _open_account(env: WorkflowEnvironment, failures: dict):
    async with _worker(env):
        handle = await _start_and_approve(env, failures)
        result = await handle.result()
        state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
        return result, state


async def test_saga_happy_path(temporal_env):
    result, state = await _open_account(temporal_env, {})
    assert result.account_created
    assert state == "Complete"
    assert CALLS == ["get_client", "open_investment#1", "debit:500.0", "register"]


async def test_saga_rolls_back_in_reverse_when_custodian_rejects(temporal_env):
    result, state = await _open_account(temporal_env, {"register_account": "reject"})
    assert not result.account_created
    assert "register_account rejected" in result.message
    assert state.startswith("Rolled back")
    assert CALLS == [
        "get_client", "open_investment#1", "debit:500.0", "register",
        "credit:500.0", f"remove_investment:{INVESTMENT_ID}",
    ]


async def test_saga_undoes_only_completed_steps(temporal_env):
    result, _ = await _open_account(temporal_env, {"debit_linked_account": "reject"})
    assert not result.account_created
    # The debit never happened, so there is nothing to refund.
    assert CALLS == [
        "get_client", "open_investment#1", "debit:500.0", f"remove_investment:{INVESTMENT_ID}",
    ]


async def test_transient_failures_are_retried_not_rolled_back(temporal_env):
    result, _ = await _open_account(temporal_env, {"open_investment": 2})
    assert result.account_created
    assert CALLS == [
        "get_client", "open_investment#1", "open_investment#2", "open_investment#3",
        "debit:500.0", "register",
    ]


async def test_reopening_with_the_same_workflow_id_uses_a_new_transfer_id(temporal_env):
    # The open-account tool reuses the workflow ID for the same account name, so a
    # retry after a rollback must not look like a repeat of the earlier transfer.
    workflow_id = f"open-account-test-{uuid.uuid4()}"
    TRANSFER_IDS.clear()
    async with _worker(temporal_env):
        for failures in ({"register_account": "reject"}, {}):
            handle = await _start_and_approve(temporal_env, failures, workflow_id=workflow_id)
            await handle.result()
    assert len(TRANSFER_IDS) == 2
    assert TRANSFER_IDS[0] != TRANSFER_IDS[1]


@pytest.mark.parametrize(
    "amount, error_type",
    [(50.0, "DepositBelowMinimum"), (2_000_000.0, "DepositLimitExceeded")],
)
async def test_business_rule_violations_are_non_retryable(amount, error_type):
    with pytest.raises(ApplicationError) as exc_info:
        await ActivityEnvironment().run(Investments.validate_new_account, CLIENT_ID, "Test", amount)
    assert exc_info.value.type == error_type
    assert exc_info.value.non_retryable


async def test_valid_deposit_passes_validation():
    await ActivityEnvironment().run(Investments.validate_new_account, CLIENT_ID, "Test", 5_000.0)


def test_funding_transfers_are_idempotent(tmp_path):
    funding_file = tmp_path / "funding.json"
    funding_file.write_text(json.dumps({"accounts": {CLIENT_ID: {"name": "Bank", "balance": 1000.0}}}))

    FundingManager(funding_file).debit(CLIENT_ID, 400.0, "t-1")
    FundingManager(funding_file).debit(CLIENT_ID, 400.0, "t-1")  # a retry of the same transfer
    assert FundingManager(funding_file).get_account(CLIENT_ID)["balance"] == 600.0

    with pytest.raises(InsufficientFundsError):
        FundingManager(funding_file).debit(CLIENT_ID, 700.0, "t-2")

    FundingManager(funding_file).credit(CLIENT_ID, 400.0, "t-1-refund")
    FundingManager(funding_file).credit(CLIENT_ID, 400.0, "t-1-refund")
    assert FundingManager(funding_file).get_account(CLIENT_ID)["balance"] == 1000.0


async def test_tool_down_raises_a_retryable_error(chaos_flags):
    chaos_flags.add(ChaosFlag.TOOL_DOWN)
    with pytest.raises(ConnectionError):
        await ActivityEnvironment().run(Investments.list_investments, CLIENT_ID)


def _model() -> model_config.ChaosAwareOpenAIModel:
    return model_config.ChaosAwareOpenAIModel(model="gpt-4o", openai_client=AsyncOpenAI(api_key="test"))


async def test_llm_down_raises_a_retryable_error(chaos_flags):
    chaos_flags.add(ChaosFlag.LLM_DOWN)
    with pytest.raises(ConnectionError):
        await ActivityEnvironment().run(_model().get_response)


async def test_llm_rate_limit_waits_for_retry_after(chaos_flags):
    chaos_flags.add(ChaosFlag.LLM_RATE_LIMITED)
    with pytest.raises(ApplicationError) as exc_info:
        await ActivityEnvironment().run(_model().get_response)
    assert exc_info.value.type == "ModelRateLimited"
    assert exc_info.value.next_retry_delay == model_config.RATE_LIMIT_RETRY_AFTER
    assert not exc_info.value.non_retryable


async def test_promo_code_path_bug_pauses_workflow_instead_of_failing_it(temporal_env):
    async with _worker(temporal_env):
        handle = await _start_and_approve(temporal_env, {}, promo_code="WELCOME-BONUS")
        failure = None
        for _ in range(40):
            async for event in handle.fetch_history_events():
                if event.event_type == EventType.EVENT_TYPE_WORKFLOW_TASK_FAILED:
                    failure = event.workflow_task_failed_event_attributes.failure.message
            if failure:
                break
            await asyncio.sleep(0.25)

        assert failure and "initial_deposit" in failure, "the demo bug should fail the workflow task"
        # Paused, not failed: still running, and the saga never started.
        assert (await handle.describe()).status == WorkflowExecutionStatus.RUNNING
        assert "open_investment#1" not in CALLS
        await handle.terminate()
