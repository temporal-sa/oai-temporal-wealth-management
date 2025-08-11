from datetime import timedelta

import asyncio
from temporalio import workflow
from temporalio.contrib import openai_agents

from common.user_message import ProcessUserMessageInput, ChatInteraction
from common.agent_constants import BENE_AGENT_NAME, BENE_HANDOFF, BENE_INSTRUCTIONS, INVEST_AGENT_NAME, \
    INVEST_HANDOFF, \
    INVEST_INSTRUCTIONS, SUPERVISOR_AGENT_NAME, SUPERVISOR_HANDOFF, SUPERVISOR_INSTRUCTIONS, \
    OPEN_ACCOUNT_AGENT_NAME, OPEN_ACCOUNT_HANDOFF, OPEN_ACCOUNT_INSTRUCTIONS

from temporal_supervisor.activities.open_account import OpenAccount, open_new_investment_account

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
    name="Routing Guardrail",
    instructions="""Analyze the user's question and determine if it's about wealth management topics (beneficiaries or investments). 
    
    Wealth management keywords: beneficiary, beneficiaries, add beneficiary, delete beneficiary, list beneficiaries, family member, son, daughter, spouse, child, children, inheritance, estate, investment, investments, account, accounts, balance, balances, open account, close account, list accounts, portfolio, money, funds, savings, checking, retirement, wealth, financial, finance
    
    IMPORTANT: If the question is about ANYTHING other than wealth management (geography, animals, science, history, general knowledge, personal questions, etc.), set is_wealth_management_question to FALSE.
    
    Examples of questions that should be BLOCKED (is_wealth_management_question = false):
    - "What is a cheetah?" (animal question)
    - "What is the capital of Florida?" (geography question)
    - "What is your name?" (personal question)
    - "How does photosynthesis work?" (science question)
    - "What is the weather like?" (general question)
    
    Examples of questions that should be ALLOWED (is_wealth_management_question = true):
    - "Who are my beneficiaries?" (beneficiary question)
    - "What investment accounts do I have?" (investment question)
    - "Add a beneficiary to my account" (beneficiary question)
    - "Show me my portfolio" (investment question)
    
    Be very strict - only allow questions that are clearly about wealth management topics.""",
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
def init_agents() -> Agent[WealthManagementContext]:
    """
    Initialize the agents for the Wealth Management Workflow

    Returns a supervisor agent
    """
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
        input_guardrails=[routing_guardrail],
    )

    open_account_agent = Agent[WealthManagementContext](
        name=OPEN_ACCOUNT_AGENT_NAME,
        handoff_description=OPEN_ACCOUNT_HANDOFF,
        instructions=OPEN_ACCOUNT_INSTRUCTIONS,
        tools=[
            open_new_investment_account,
            openai_agents.workflow.activity_as_tool(OpenAccount.get_current_client_info,start_to_close_timeout=timedelta(seconds=5)),
            openai_agents.workflow.activity_as_tool(OpenAccount.approve_kyc,start_to_close_timeout=timedelta(seconds=5)),
            openai_agents.workflow.activity_as_tool(OpenAccount.update_client_details,start_to_close_timeout=timedelta(seconds=5)),
            openai_agents.workflow.activity_as_tool(OpenAccount.current_state,start_to_close_timeout=timedelta(seconds=5)),
        ],
        input_guardrails=[routing_guardrail],
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
        input_guardrails=[routing_guardrail],
    )

    supervisor_agent = Agent[WealthManagementContext](
        name=SUPERVISOR_AGENT_NAME,
        handoff_description=SUPERVISOR_HANDOFF,
        instructions=SUPERVISOR_INSTRUCTIONS,
        handoffs=[
            beneficiary_agent,
            investment_agent,
        ],
        input_guardrails=[routing_guardrail],
    )

    beneficiary_agent.handoffs.append(supervisor_agent)
    investment_agent.handoffs.append(supervisor_agent)
    open_account_agent.handoffs.append(investment_agent)
    return supervisor_agent


@workflow.defn
class WealthManagementWorkflow:
    def __init__(self, input_items: list[TResponseInputItem] | None = None ):
        self.pending_messages: asyncio.Queue[str] = asyncio.Queue()
        self.message_processed = False
        self.processed_response: list[ChatInteraction] | None = None
        self.run_config = RunConfig()
        self.chat_history: list[ChatInteraction] = []
        self.current_agent: Agent[WealthManagementContext] = init_agents()
        self.context = WealthManagementContext()
        self.input_items = [] if input_items is None else input_items
        self.end_workflow = False

    @workflow.run
    async def run(self, input_items: list[TResponseInputItem] | None = None):
        while True:
            workflow.logger.info("At top of loop - waiting for another message")
            # Wait for queue item or end workflow
            await workflow.wait_condition(
                lambda: not self.pending_messages.empty() or self.end_workflow
            )

            if self.end_workflow:
                workflow.logger.info("Ending workflow.")
                return

            # Get the message, process it, save the response, and
            # change the flag to indicate that it was processed.
            workflow.logger.info("Changing message processed flag to false")
            self.message_processed = False
            # clear the previous response, if any
            self.processed_response = None
            message = self.pending_messages.get_nowait()
            self.processed_response = await self._process_chat_message(message)
            workflow.logger.info("message processed. setting flag to true")
            self.message_processed = True

            # do we need to do a continue as new?
            if workflow.info().is_continue_as_new_suggested():
                # wait until everything finishes before doing Continue As New
                await workflow.wait_condition(
                    lambda: workflow.all_handlers_finished()
                )
                workflow.continue_as_new(self.input_items)

    async def _process_chat_message(self, message: str) -> list[ChatInteraction]:
        workflow.logger.info("processing user message")
        length = len(self.chat_history)
        # build the interaction
        chat_interaction = ChatInteraction(
            user_prompt=message,
            text_response=""
        )
        # self.chat_history.append(f"User: {input.user_input}")

        self.input_items.append({"content": message, "role": "user"})
        try: 
            result = await Runner.run(
                self.current_agent,
                self.input_items,
                context=self.context,
                run_config=self.run_config,
            )

            text_response = ""
            json_response = ""
            agent_trace = ""

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    workflow.logger.info(f"{agent_name} {ItemHelpers.text_message_output(new_item)}")
                    text_response += f"{ItemHelpers.text_message_output(new_item)}\n"
                    # self.chat_history.append(f"{agent_name} {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    workflow.logger.info(f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
                    agent_trace += f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}\n"
                    # self.chat_history.append(f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
                elif isinstance(new_item, ToolCallItem):
                    workflow.logger.info(f"{agent_name}: Calling a tool")
                    agent_trace += f"{agent_name}: Calling a tool\n"
                    # self.chat_history.append(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    workflow.logger.info(f"{agent_name}: Tool call output: {new_item.output}")
                    # this might be problematic... TODO: validate
                    json_response += new_item.output + "\n"
                    # self.chat_history.append(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    agent_trace += f"{agent_name}: Skipping item: {new_item.__class__.__name__}\n"
                    # self.chat_history.append(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            self.input_items = result.to_input_list()
            self.current_agent = result.last_agent

            chat_interaction.text_response = text_response
            chat_interaction.json_response = json_response
            chat_interaction.agent_trace = agent_trace
            self.chat_history.append(chat_interaction)

            current_details = "\n\n"
            for item in self.chat_history:
                current_details.join(str(item))

            workflow.set_current_details(current_details)
            return self.chat_history[length:]
        except InputGuardrailTripwireTriggered as e:
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
            self.chat_history.append(chat_interaction)
            
            current_details = "\n\n"
            for item in self.chat_history:
                current_details.join(str(item))
            
            workflow.set_current_details(current_details)
            return self.chat_history[length:]

    @workflow.query
    def get_chat_history(self) -> list[ChatInteraction]:
        return self.chat_history

    @workflow.signal
    async def end_workflow(self):
        self.end_workflow = True

    @workflow.update
    async def process_user_message(self, message_input: ProcessUserMessageInput) -> list[ChatInteraction]:
        workflow.logger.info(f"processing user message {message_input}")
        workflow.logger.info(f"Agent has guardrails: {hasattr(self.current_agent, 'input_guardrails') and self.current_agent.input_guardrails}")

        await self.pending_messages.put(message_input.user_input)
        self.message_processed = False
        workflow.logger.info("waiting for the message to be processed")
        await workflow.wait_condition(
            self.is_message_processed
        )
        workflow.logger.info(f"message has been processed. Processed? {self.message_processed}, Response = {self.processed_response} ")
        return self.processed_response

    def is_message_processed(self) -> bool:
        return_value = self.message_processed and self.processed_response is not None
        workflow.logger.info(f"is message processed? {return_value}")
        return return_value

    @process_user_message.validator
    def validate_process_user_message(self, message_input: ProcessUserMessageInput) -> None:
        workflow.logger.info(f"validating user message {message_input}")
        if not message_input.user_input:
            workflow.logger.error("Input cannot be empty")
            raise ValueError("Input cannot be empty")
        if len(message_input.user_input) > 1000:
            workflow.logger.error("Input is too long. Please limit to 1000 characters")
            raise ValueError("Input is too long. Please limit to 1000 characters")

