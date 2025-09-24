
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

import asyncio
from temporalio import workflow
from temporalio.contrib import openai_agents
from temporalio.common import RetryPolicy

from common.user_message import ProcessUserMessageInput, ChatInteraction
from common.status_update import StatusUpdate
from common.agent_constants import BENE_AGENT_NAME, BENE_HANDOFF, BENE_INSTRUCTIONS, INVEST_AGENT_NAME, \
    INVEST_HANDOFF, \
    INVEST_INSTRUCTIONS, SUPERVISOR_AGENT_NAME, SUPERVISOR_HANDOFF, SUPERVISOR_INSTRUCTIONS, \
    OPEN_ACCOUNT_AGENT_NAME, OPEN_ACCOUNT_HANDOFF, OPEN_ACCOUNT_INSTRUCTIONS, ROUTING_GUARDRAIL_NAME, \
    ROUTING_INSTRUCTIONS

from temporal_supervisor.activities.event_stream_activities import EventStreamActivities

from temporal_supervisor.activities.open_account import OpenAccount, open_new_investment_account
from common.account_context import UpdateAccountOpeningStateInput

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
        input_guardrail,
        RunContextWrapper,
        GuardrailFunctionOutput,
        InputGuardrailTripwireTriggered,
    )
    from pydantic import BaseModel

### Context

class WealthManagementContext(BaseModel):
    client_id: str | None = None

class RoutingGuardrailOutput(BaseModel):
    is_wealth_management_question: bool
    reasoning: str

routing_guardrail_agent = Agent(
    name=ROUTING_GUARDRAIL_NAME,
    instructions=ROUTING_INSTRUCTIONS,
    output_type=RoutingGuardrailOutput,
)

@input_guardrail
async def routing_guardrail(
        ctx: RunContextWrapper[WealthManagementContext], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    workflow.logger.info(f"Guardrail triggered with input: {input}")
    
    if isinstance(input, list) and len(input) > 0:
        last_message = input[-1].get("content", "") if isinstance(input[-1], dict) else str(input[-1])
        workflow.logger.info(f"Analyzing message: {last_message}")
    else:
        last_message = str(input)
        workflow.logger.info(f"Analyzing message: {last_message}")
    
    result = await Runner.run(routing_guardrail_agent, input, context=ctx.context)
    
    workflow.logger.info(f"Guardrail result: {result.final_output}")
    should_block = not result.final_output.is_wealth_management_question
    workflow.logger.info(f"Should block: {should_block}")
    workflow.logger.info(f"Question is wealth management: {result.final_output.is_wealth_management_question}")
    workflow.logger.info(f"Reasoning: {result.final_output.reasoning}")
    
    if should_block:
        workflow.logger.info(f"Guardrail tripwire triggered! Blocking non-wealth-management question.")
    else:
        workflow.logger.info(f"Guardrail allowing wealth management question to pass through.")
    
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=should_block,
    )

### Agents
def init_agents(disable_guardrails: bool) -> Agent[WealthManagementContext]:
    """
    Initialize the agents for the Wealth Management Workflow

    Returns a supervisor agent
    """
    guardrails = []
    if disable_guardrails == False:
        guardrails = [routing_guardrail]
    beneficiary_agent = Agent[WealthManagementContext](
        name=BENE_AGENT_NAME,
        handoff_description=BENE_HANDOFF,
        instructions=BENE_INSTRUCTIONS,
        tools=[openai_agents.workflow.activity_as_tool(Beneficiaries.list_beneficiaries,
                                start_to_close_timeout=timedelta(seconds=5)),
               openai_agents.workflow.activity_as_tool(Beneficiaries.add_beneficiary,
                                start_to_close_timeout=timedelta(seconds=5)),
               openai_agents.workflow.activity_as_tool(Beneficiaries.delete_beneficiary,
                                start_to_close_timeout=timedelta(seconds=5))
               ],
        input_guardrails=guardrails,
    )

    open_account_agent = Agent[WealthManagementContext](
        name=OPEN_ACCOUNT_AGENT_NAME,
        handoff_description=OPEN_ACCOUNT_HANDOFF,
        instructions=OPEN_ACCOUNT_INSTRUCTIONS,
        tools=[
            open_new_investment_account,
            openai_agents.workflow.activity_as_tool(OpenAccount.get_current_client_info, start_to_close_timeout=timedelta(seconds=5)),
            openai_agents.workflow.activity_as_tool(OpenAccount.approve_kyc, start_to_close_timeout=timedelta(seconds=5)),
            openai_agents.workflow.activity_as_tool(OpenAccount.update_client_details, start_to_close_timeout=timedelta(seconds=5)),
        ],
        input_guardrails=guardrails,
    )

    investment_agent = Agent[WealthManagementContext](
        name=INVEST_AGENT_NAME,
        handoff_description=INVEST_HANDOFF,
        instructions=INVEST_INSTRUCTIONS,
        tools=[openai_agents.workflow.activity_as_tool(Investments.list_investments,
                                start_to_close_timeout=timedelta(seconds=5)),
               openai_agents.workflow.activity_as_tool(Investments.close_investment,
                                start_to_close_timeout=timedelta(seconds=5))],
        handoffs=[
            open_account_agent
        ],
        input_guardrails=guardrails,
    )

    supervisor_agent = Agent[WealthManagementContext](
        name=SUPERVISOR_AGENT_NAME,
        handoff_description=SUPERVISOR_HANDOFF,
        instructions=SUPERVISOR_INSTRUCTIONS,
        handoffs=[
            beneficiary_agent,
            investment_agent,
        ],
        input_guardrails=guardrails,
    )

    beneficiary_agent.handoffs.append(supervisor_agent)
    investment_agent.handoffs.append(supervisor_agent)
    open_account_agent.handoffs.append(investment_agent)
    return supervisor_agent


@workflow.defn
class WealthManagementWorkflow:

    def __init__(self, input_items: list[TResponseInputItem] | None = None ):
        self.wf_id = workflow.info().workflow_id
        self.pending_chat_messages: asyncio.Queue = asyncio.Queue()
        self.pending_status_updates: asyncio.Queue = asyncio.Queue()
        self.processed_response: list[ChatInteraction] | None = None
        self.run_config = RunConfig()
        self.chat_history: list[ChatInteraction] = []
        self.current_agent: Agent[WealthManagementContext] = init_agents(True)
        self.context = WealthManagementContext()
        self.input_items = [] if input_items is None else input_items
        self.end_workflow = False
        self.sched_to_close_timeout = timedelta(seconds=5)
        self.retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1),
                               backoff_coefficient=2,
                               maximum_interval=timedelta(seconds=30))

    @workflow.run
    async def run(self, input_items: list[TResponseInputItem] | None = None):
        if workflow.info().continued_run_id is None:
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

            # do we need to do a continue as new?
            if workflow.info().is_continue_as_new_suggested():
                # wait until everything finishes before doing Continue As New
                # FIXME: This will only ensure that things are added to our self.pending_ queues, it won't process them. They will be lost.
                await workflow.wait_condition(
                    lambda: workflow.all_handlers_finished()
                )
                workflow.continue_as_new(args=[self.input_items])

    async def _process_chat_message(self, message: str) -> list[ChatInteraction]:
        workflow.logger.info(f"processing chat message: {message}")
        length = len(self.chat_history)

        chat_interaction = ChatInteraction(
            user_prompt=message,
            text_response=""
        )
        try:
            await self._process_user_message(chat_interaction, message)
        except InputGuardrailTripwireTriggered as e:
            workflow.logger.info(f"Guardrail Tripwire triggered {e}")
            await self._handle_guardrail_failure(chat_interaction, e)

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
        result = await Runner.run(
            self.current_agent,
            self.input_items,
            context=self.context,
            run_config=self.run_config,
        )

        workflow.logger.info("Runner.run has exited.")
        self.input_items = result.to_input_list()
        self.current_agent = result.last_agent

        agent_trace, json_response, text_response = await self._process_llm_response(result)

        chat_interaction.text_response = text_response
        chat_interaction.json_response = json_response
        chat_interaction.agent_trace = agent_trace

    async def _handle_guardrail_failure(self, chat_interaction, e):
        workflow.logger.info(f"Guardrail tripwire triggered: {e}")
        text_response = "I'm sorry, but I can only help with wealth management questions related to beneficiaries and investments. Please ask me about your beneficiaries, investment accounts, or other wealth management topics."
        agent_trace = f"Guardrail blocked non-wealth-management question: {e}"
        if hasattr(e, 'result') and hasattr(e.result, 'output_info'):
            guardrail_output = e.result.output_info
            if hasattr(guardrail_output, 'reasoning'):
                workflow.logger.info(f"Blocked question reasoning: {guardrail_output.reasoning}")
                agent_trace += f" - Reasoning: {guardrail_output.reasoning}"
        chat_interaction.text_response = text_response
        chat_interaction.json_response = ""
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
                json_response += new_item.output + "\n"
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
        status_message = f"New {state_input.account_name} account status changed: {state_input.state}"
        await self.pending_status_updates.put(status_message)

    @workflow.signal
    async def process_user_message(self, message_input: ProcessUserMessageInput):
        workflow.logger.info(f"processing user message {message_input}")
        workflow.logger.info(f"Agent has guardrails: {hasattr(self.current_agent, 'input_guardrails') and self.current_agent.input_guardrails}")
        await self.pending_chat_messages.put(message_input.user_input)

