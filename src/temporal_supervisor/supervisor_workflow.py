from datetime import timedelta

from temporalio import workflow
from temporalio.contrib import openai_agents

from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.investments import Investments
from common.user_message import ProcessUserMessageInput, ChatInteraction
from common.agent_constants import BENE_AGENT_NAME, BENE_HANDOFF, BENE_INSTRUCTIONS, INVEST_AGENT_NAME, \
    INVEST_HANDOFF, \
    INVEST_INSTRUCTIONS, SUPERVISOR_AGENT_NAME, SUPERVISOR_HANDOFF, SUPERVISOR_INSTRUCTIONS

with workflow.unsafe.imports_passed_through():
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
        trace,
    )
    from pydantic import BaseModel


### Context

class WealthManagementContext(BaseModel):
    account_id: str | None = None

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
    )

    supervisor_agent = Agent[WealthManagementContext](
        name=SUPERVISOR_AGENT_NAME,
        handoff_description=SUPERVISOR_HANDOFF,
        instructions=SUPERVISOR_INSTRUCTIONS,
        handoffs=[
            beneficiary_agent,
            investment_agent,
        ]
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
        length = len(self.chat_history)
        # build the interaction
        chat_interaction = ChatInteraction(
            user_prompt=input.user_input,
            text_response = ""
        )
        # self.chat_history.append(f"User: {input.user_input}")

        self.input_items.append({"content": input.user_input, "role": "user"})
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

    @process_user_message.validator
    def validate_process_user_message(self, input: ProcessUserMessageInput) -> None:
        workflow.logger.info(f"validating user message {input}")
        if not input.user_input:
            workflow.logger.error("Input cannot be empty")
            raise ValueError("Input cannot be empty")
        if len(input.user_input) > 1000:
            workflow.logger.error("Input is too long. Please limit to 1000 characters")
            raise ValueError("Input is too long. Please limit to 1000 characters")

