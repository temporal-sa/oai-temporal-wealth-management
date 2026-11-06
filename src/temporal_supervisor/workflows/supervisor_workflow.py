
from dataclasses import asdict, dataclass, is_dataclass
from datetime import timedelta
from enum import Enum

import asyncio
import json
from temporalio import workflow
from temporalio.contrib import openai_agents
from temporalio.common import RetryPolicy

from common.user_message import ProcessUserMessageInput, ChatInteraction
from common.status_update import StatusUpdate
from common.agent_constants import BENE_AGENT_NAME, BENE_HANDOFF, BENE_INSTRUCTIONS, INVEST_AGENT_NAME, \
    INVEST_HANDOFF, \
    INVEST_INSTRUCTIONS, SUPERVISOR_AGENT_NAME, SUPERVISOR_HANDOFF, SUPERVISOR_INSTRUCTIONS, \
    OPEN_ACCOUNT_AGENT_NAME, OPEN_ACCOUNT_HANDOFF, OPEN_ACCOUNT_INSTRUCTIONS

from temporal_supervisor.activities.event_stream_activities import EventStreamActivities

from temporal_supervisor.activities.open_account import OpenAccount, open_new_investment_account
from common.account_context import UpdateAccountOpeningStateInput
from temporal_supervisor.retry_policies import TOOL_RETRY_POLICY

with workflow.unsafe.imports_passed_through():
    from temporal_supervisor.activities.beneficiaries import Beneficiaries
    from temporal_supervisor.activities.investments import Investments
    from agents import (
        Agent,
        HandoffOutputItem,
        ItemHelpers,
        MessageOutputItem,
        RunConfig,
        Runner,
        ToolCallItem,
        ToolCallOutputItem,
        TResponseInputItem,
        RunContextWrapper,
        function_tool,
        ModelResponse,
        RunHooks,
    )
    from pydantic import BaseModel

### Context

class WealthManagementContext(BaseModel):
    # The customer's client ID, once a tool has been called with it. Shared by all
    # the agents so the customer is only asked for it once.
    client_id: str | None = None
    # Latest state reported by each open-account child workflow, keyed by its
    # workflow ID. Updated by the update_account_opening_state signal.
    account_opening_states: dict[str, str] = {}
    # Number of the customer message being processed, and the message in which each
    # account opening's client details were shown, keyed by its workflow ID. Used to
    # check that the customer confirmed their details before KYC is approved.
    turn: int = 0
    kyc_details_shown_turn: dict[str, int] = {}
    # Number of account openings (open-account child workflows) started in this
    # conversation. The next opening's workflow ID ends with this number plus one.
    account_openings_started: int = 0

class ClientIdHooks(RunHooks[WealthManagementContext]):
    """Saves the client ID from any tool call that has one, before the tool runs."""

    async def on_llm_end(self, context: RunContextWrapper[WealthManagementContext], agent: Agent,
                         response: ModelResponse) -> None:
        for item in response.output:
            if getattr(item, "type", None) != "function_call":
                continue
            try:
                client_id = json.loads(item.arguments or "{}").get("client_id")
            except (json.JSONDecodeError, AttributeError):
                continue
            if client_id:
                context.context.client_id = str(client_id)

def with_client_id(instructions: str):
    """Agent instructions that include the client ID once it is known.

    The ID is otherwise only in the conversation history, and an agent that is handed
    the conversation often asks for it again.
    """
    def dynamic_instructions(ctx: RunContextWrapper[WealthManagementContext], agent: Agent) -> str:
        if ctx.context.client_id is None:
            return instructions
        return (f"{instructions}\n"
                f"    The customer's client ID is {ctx.context.client_id}. Use it, and don't ask for it again.")
    return dynamic_instructions

@function_tool
async def get_current_client_info(ctx: RunContextWrapper[WealthManagementContext], workflow_id: str) -> dict:
    """Retrieve the customer's current details for an account opening, to show them for KYC.

    Args:
        workflow_id: The workflow ID returned by open_new_investment_account.
    """
    client = await workflow.execute_activity(
        OpenAccount.get_current_client_info,
        workflow_id,
        start_to_close_timeout=timedelta(seconds=5),
        retry_policy=TOOL_RETRY_POLICY)
    ctx.context.kyc_details_shown_turn[workflow_id] = ctx.context.turn
    return asdict(client) if is_dataclass(client) else client

@function_tool
async def approve_kyc(ctx: RunContextWrapper[WealthManagementContext], workflow_id: str) -> str:
    """Approve KYC for an account opening, after the customer confirmed their details are correct.

    Args:
        workflow_id: The workflow ID returned by open_new_investment_account.
    """
    # The model sometimes treats a confirmation for an earlier account opening as
    # approval for a new one. Only approve once this opening's details have been
    # shown and the customer has replied since.
    shown_turn = ctx.context.kyc_details_shown_turn.get(workflow_id)
    if shown_turn is None or shown_turn >= ctx.context.turn:
        return ("KYC was not approved. First show the customer their current details for this account "
                "opening (get_current_client_info) and ask whether they are correct. Approve KYC only "
                "after the customer confirms in their next message.")
    await workflow.execute_activity(
        OpenAccount.approve_kyc,
        workflow_id,
        start_to_close_timeout=timedelta(seconds=5),
        retry_policy=TOOL_RETRY_POLICY)
    return "KYC approved. The account is now waiting for compliance review."

@function_tool
async def get_account_opening_status(ctx: RunContextWrapper[WealthManagementContext], workflow_id: str) -> str:
    """Get the current status of an account opening.

    Args:
        workflow_id: The workflow ID returned by open_new_investment_account.

    Returns:
        The latest status the account opening reported. "Complete" means the account
        was opened; a status starting with "Rolled back" means it was not opened.
        Either way, that account opening is finished.
    """
    state = ctx.context.account_opening_states.get(workflow_id)
    if state is None:
        return f"No account opening with workflow ID {workflow_id} was found in this conversation."
    return state

### Agents
def init_agents() -> Agent[WealthManagementContext]:
    """
    Initialize the agents for the Wealth Management Workflow

    Returns a supervisor agent
    """
    beneficiary_agent = Agent[WealthManagementContext](
        name=BENE_AGENT_NAME,
        handoff_description=BENE_HANDOFF,
        instructions=with_client_id(BENE_INSTRUCTIONS),
        tools=[openai_agents.workflow.activity_as_tool(Beneficiaries.list_beneficiaries,
                                start_to_close_timeout=timedelta(seconds=5),
                                retry_policy=TOOL_RETRY_POLICY),
               openai_agents.workflow.activity_as_tool(Beneficiaries.add_beneficiary,
                                start_to_close_timeout=timedelta(seconds=5),
                                retry_policy=TOOL_RETRY_POLICY),
               openai_agents.workflow.activity_as_tool(Beneficiaries.delete_beneficiary,
                                start_to_close_timeout=timedelta(seconds=5),
                                retry_policy=TOOL_RETRY_POLICY)
               ],
    )

    open_account_agent = Agent[WealthManagementContext](
        name=OPEN_ACCOUNT_AGENT_NAME,
        handoff_description=OPEN_ACCOUNT_HANDOFF,
        instructions=with_client_id(OPEN_ACCOUNT_INSTRUCTIONS),
        tools=[
            open_new_investment_account,
            get_account_opening_status,
            get_current_client_info,
            approve_kyc,
            openai_agents.workflow.activity_as_tool(OpenAccount.update_client_details, start_to_close_timeout=timedelta(seconds=5),
                                retry_policy=TOOL_RETRY_POLICY),
        ],
    )

    investment_agent = Agent[WealthManagementContext](
        name=INVEST_AGENT_NAME,
        handoff_description=INVEST_HANDOFF,
        instructions=with_client_id(INVEST_INSTRUCTIONS),
        tools=[openai_agents.workflow.activity_as_tool(Investments.list_investments,
                                start_to_close_timeout=timedelta(seconds=5),
                                retry_policy=TOOL_RETRY_POLICY),
               openai_agents.workflow.activity_as_tool(Investments.close_investment,
                                start_to_close_timeout=timedelta(seconds=5),
                                retry_policy=TOOL_RETRY_POLICY)],
        handoffs=[
            open_account_agent
        ],
    )

    supervisor_agent = Agent[WealthManagementContext](
        name=SUPERVISOR_AGENT_NAME,
        handoff_description=SUPERVISOR_HANDOFF,
        instructions=with_client_id(SUPERVISOR_INSTRUCTIONS),
        handoffs=[
            beneficiary_agent,
            investment_agent,
        ],
    )

    beneficiary_agent.handoffs.append(supervisor_agent)
    investment_agent.handoffs.append(supervisor_agent)
    open_account_agent.handoffs.append(investment_agent)
    return supervisor_agent


@workflow.defn
class WealthManagementWorkflow:

    def __init__(self):
        self.wf_id = workflow.info().workflow_id
        self.pending_chat_messages: asyncio.Queue = asyncio.Queue()
        self.pending_status_updates: asyncio.Queue = asyncio.Queue()
        self.processed_response: list[ChatInteraction] | None = None
        self.run_config = RunConfig()
        self.chat_history: list[ChatInteraction] = []
        self.current_agent: Agent[WealthManagementContext] = init_agents()
        self.context = WealthManagementContext()
        self.input_items: list[TResponseInputItem] = []
        self.end_workflow = False
        self.sched_to_close_timeout = timedelta(seconds=5)
        self.retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1),
                               backoff_coefficient=2,
                               maximum_interval=timedelta(seconds=30))

    @workflow.run
    async def run(self):
        # delete any previous conversations
        # FIXME: We shouldn't be deleting conversations here,
        # we should be deleting them when the workflow is ended coupled with
        # expirations on redis in case of workflow termination.
        # This is polluting the workflow code because we re-use the workflow ID in the demo app.
        wf_id = workflow.info().workflow_id
        workflow.logger.info(f"Deleting any previous conversation {wf_id}")
        await workflow.execute_local_activity(
            EventStreamActivities.delete_conversation,
            args=[wf_id],
            schedule_to_close_timeout=self.sched_to_close_timeout,
            retry_policy=self.retry_policy)

        while True:
            workflow.logger.info("At top of loop - waiting for messages or status updates")
            # Wait for queue items or end workflow
            await workflow.wait_condition(
                lambda: not self.pending_chat_messages.empty() or not self.pending_status_updates.empty() or self.end_workflow
            )

            if self.end_workflow:
                workflow.logger.info("Ending workflow.")
                return

            # Process chat messages
            if not self.pending_chat_messages.empty():
                message = self.pending_chat_messages.get_nowait()
                self.processed_response = await self._process_chat_message(message)
                workflow.logger.info("chat message processed.")

            # Process status updates
            if not self.pending_status_updates.empty():
                status_message = self.pending_status_updates.get_nowait()
                await self._process_status_update(status_message)
                workflow.logger.info("status update processed.")

            # TODO: Continue-As-New.
            # This demo keeps the whole conversation in one workflow run. A production system
            # would call continue-as-new when workflow.info().is_continue_as_new_suggested()
            # returns true, because Temporal limits a run's event history (warnings at 10K
            # events / 10 MB, terminated at 50K events / 50 MB) and every LLM call and tool
            # call adds events, so a long-running chat would eventually hit those limits.
            # To do it safely:
            #   - Wait for workflow.all_handlers_finished() and drain the pending message and
            #     status queues first, so no customer message or status update is lost.
            #   - Carry the conversation state into the new run: the message history, the
            #     active agent, the client ID, the account-opening states, the number of
            #     account openings started (part of each child workflow ID), and the KYC
            #     guard's turn tracking.
            #   - Open-account child workflows are started with ParentClosePolicy.TERMINATE,
            #     which also applies when the parent continues-as-new, so an opening waiting
            #     for KYC or compliance would be terminated. Use ParentClosePolicy.ABANDON and
            #     have the end_workflow handler cancel/terminate any openings still running,
            #     or defer continue-as-new until no opening is in progress.

    async def _process_chat_message(self, message: str) -> list[ChatInteraction]:
        workflow.logger.info(f"processing chat message: {message}")
        length = len(self.chat_history)

        chat_interaction = ChatInteraction(
            user_prompt=message,
            text_response=""
        )
        await self._process_user_message(chat_interaction, message)

        self.chat_history.append(chat_interaction)

        current_details = "\n\n"
        for item in self.chat_history:
            current_details.join(str(item))

        workflow.set_current_details(current_details)

        await workflow.execute_local_activity(
            EventStreamActivities.append_chat_interaction,
            args=[self.wf_id, chat_interaction],
            schedule_to_close_timeout=self.sched_to_close_timeout,
            retry_policy=self.retry_policy)

        return self.chat_history[length:]

    async def _process_status_update(self, status_message: str):
        workflow.logger.info(f"processing status update: {status_message}")

        # TODO: Consider filtering which messages we want to update the client
        status_update = StatusUpdate(status=status_message)
        result = await workflow.execute_local_activity(
            EventStreamActivities.append_status_update,
            args=[self.wf_id, status_update],
            schedule_to_close_timeout=self.sched_to_close_timeout,
            retry_policy=self.retry_policy)

    async def _process_user_message(self, chat_interaction: ChatInteraction, message: str):
        self.input_items.append({"content": message, "role": "user"})
        self.context.turn += 1
        result = await Runner.run(
            self.current_agent,
            self.input_items,
            context=self.context,
            run_config=self.run_config,
            hooks=ClientIdHooks(),
        )

        workflow.logger.info("Runner.run has exited.")
        self.input_items = result.to_input_list()
        self.current_agent = result.last_agent

        agent_trace, json_response, text_response = await self._process_llm_response(result)

        chat_interaction.text_response = text_response
        chat_interaction.json_response = json_response
        chat_interaction.agent_trace = agent_trace

    async def _process_llm_response(self, result):
        text_response = ""
        json_response = ""
        agent_trace = ""
        for new_item in result.new_items:
            agent_name = new_item.agent.name
            if isinstance(new_item, MessageOutputItem):
                workflow.logger.info(f"{agent_name} {ItemHelpers.text_message_output(new_item)}")
                text_response += f"{ItemHelpers.text_message_output(new_item)}"
            elif isinstance(new_item, HandoffOutputItem):
                workflow.logger.info(f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
                agent_trace += f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}\n"
            elif isinstance(new_item, ToolCallItem):
                workflow.logger.info(f"{agent_name}: Calling a tool")
                agent_trace += f"{agent_name}: Calling a tool\n"
            elif isinstance(new_item, ToolCallOutputItem):
                workflow.logger.info(f"{agent_name}: Tool call output: {new_item.output}")
                json_response += str(new_item.output) + "\n"
            else:
                agent_trace += f"{agent_name}: Skipping item: {new_item.__class__.__name__}\n"
        return agent_trace, json_response, text_response

    @workflow.query
    def get_chat_history(self) -> list[ChatInteraction]:
        return self.chat_history

    @workflow.signal
    async def end_workflow(self):
        self.end_workflow = True
        
    @workflow.signal
    async def update_account_opening_state(self, state_input: UpdateAccountOpeningStateInput):
        workflow.logger.info(f"Account Opening State changed {state_input.account_name} {state_input.state}")
        if state_input.workflow_id is not None:
            self.context.account_opening_states[state_input.workflow_id] = state_input.state
        status_message = f"New {state_input.account_name} account status changed: {state_input.state}"
        await self.pending_status_updates.put(status_message)

    @workflow.signal
    async def process_user_message(self, message_input: ProcessUserMessageInput):
        workflow.logger.info(f"processing user message {message_input}")
        await self.pending_chat_messages.put(message_input.user_input)

