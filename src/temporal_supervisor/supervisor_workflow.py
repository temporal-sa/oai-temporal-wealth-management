from datetime import timedelta

from temporalio import workflow
from temporalio.contrib import openai_agents

from common.user_message import ProcessUserMessageInput, ChatInteraction
from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.investments import Investments

with workflow.unsafe.imports_passed_through():
    from agents import (
        Agent,
        HandoffOutputItem,
        ItemHelpers,
        MessageOutputItem,
        RunConfig,
        RunContextWrapper,
        Runner,
        ToolCallItem,
        ToolCallOutputItem,
        TResponseInputItem,
        function_tool,
        trace,
        input_guardrail,
        GuardrailFunctionOutput,
        InputGuardrailTripwireTriggered,
    )
    from pydantic import BaseModel
    from common.agent_constants import BENE_AGENT_NAME, BENE_HANDOFF, BENE_INSTRUCTIONS, INVEST_AGENT_NAME, \
        INVEST_HANDOFF, \
        INVEST_INSTRUCTIONS, SUPERVISOR_AGENT_NAME, SUPERVISOR_HANDOFF, SUPERVISOR_INSTRUCTIONS

### Context

class WealthManagementContext(BaseModel):
    account_id: str | None = None

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

    investment_agent = Agent[WealthManagementContext](
        name=INVEST_AGENT_NAME,
        handoff_description=INVEST_HANDOFF,
        instructions=INVEST_INSTRUCTIONS,
        tools=[openai_agents.workflow.activity_as_tool(Investments.list_investments,
                                start_to_close_timeout=timedelta(seconds=5)),
               openai_agents.workflow.activity_as_tool(Investments.open_investment,
                                start_to_close_timeout=timedelta(seconds=5)),
               openai_agents.workflow.activity_as_tool(Investments.close_investment,
                                start_to_close_timeout=timedelta(seconds=5))],
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
    return supervisor_agent


@workflow.defn
class WealthManagementWorkflow:
    def __init__(self, input_items: list[TResponseInputItem] | None = None ):
        self.run_config = RunConfig()
        self.chat_history: list[ChatInteraction] = []
        self.current_agent: Agent[WealthManagementContext] = init_agents()
        self.context = WealthManagementContext()
        self.input_items = [] if input_items is None else input_items
        self.end_workflow = False

    @workflow.run
    async def run(self, input_items: list[TResponseInputItem] | None = None):
        await workflow.wait_condition(
            lambda: self.end_workflow or (workflow.info().is_continue_as_new_suggested()
            and workflow.all_handlers_finished())
        )
        if self.end_workflow:
            workflow.logger.info("Ending workflow.")
            return
        workflow.continue_as_new(self.input_items)

    @workflow.query
    def get_chat_history(self) -> list[ChatInteraction]:
        return self.chat_history

    @workflow.signal
    async def end_workflow(self):
        self.end_workflow = True

    @workflow.update
    async def process_user_message(self, input: ProcessUserMessageInput) -> list[ChatInteraction]:
        workflow.logger.info("processing user message")
        workflow.logger.info(f"Current agent: {self.current_agent.name}")
        workflow.logger.info(f"Agent has guardrails: {hasattr(self.current_agent, 'input_guardrails') and self.current_agent.input_guardrails}")
        
        length = len(self.chat_history)
        chat_interaction = ChatInteraction(
            user_prompt=input.user_input,
            text_response = ""
        )
        
        self.input_items.append({"content": input.user_input, "role": "user"})
        workflow.logger.info(f"Running agent with {len(self.input_items)} input items")
        
        text_response = ""
        json_response = ""
        agent_trace = ""
        
        try:
            result = await Runner.run(
                self.current_agent,
                self.input_items,
                context=self.context,
                run_config=self.run_config,
            )

            workflow.logger.info(f"Agent run completed. New items: {len(result.new_items)}")

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    workflow.logger.info(f"{agent_name} {ItemHelpers.text_message_output(new_item)}")
                    text_response += f"{ItemHelpers.text_message_output(new_item)}\n"
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
                    
            self.input_items = result.to_input_list()
            self.current_agent = result.last_agent
            workflow.logger.info(f"Current agent after run: {self.current_agent.name}")

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
        chat_interaction.json_response = json_response
        chat_interaction.agent_trace = agent_trace
        self.chat_history.append(chat_interaction)

        current_details = "\n\n"
        for item in self.chat_history:
            current_details.join(str(item))

        workflow.set_current_details(current_details)
        return self.chat_history[length:]

    @process_user_message.validator
    def validate_process_user_message(self, input: ProcessUserMessageInput) -> None:
        workflow.logger.info(f"validating user message {input}")
        if not input.user_input:
            workflow.logger.error("Input cannot be empty")
            raise ValueError("Input cannot be empty")
        if len(input.user_input) > 1000:
            workflow.logger.error("Input is too long. Please limit to 1000 characters")
            raise ValueError("Input is too long. Please limit to 1000 characters")

