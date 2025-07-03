from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.openai_agents.temporal_tools import activity_as_tool

from common.user_message import ProcessUserMessageInput
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
    )
    from pydantic import BaseModel
    from common.agent_constants import BENE_AGENT_NAME, BENE_HANDOFF, BENE_INSTRUCTIONS, INVEST_AGENT_NAME, \
        INVEST_HANDOFF, \
        INVEST_INSTRUCTIONS, SUPERVISOR_AGENT_NAME, SUPERVISOR_HANDOFF, SUPERVISOR_INSTRUCTIONS

### Context

class WealthManagementContext(BaseModel):
    account_id: str | None = None


### Tools

@function_tool
async def list_investments(
        context: RunContextWrapper[WealthManagementContext], account_id: str
) -> dict:
    """
    List the investment accounts and balances for the given account id.

    Args:
        account_id: The customer's account id'
    """
    # update the context
    context.context.account_id = account_id
    return [
        { "Checking", 203.45 },
        { "Savings", 375.81 },
        { "Retirement", 24648.63 },
    ]


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
        tools=[activity_as_tool(Beneficiaries.list_beneficiaries,
                                start_to_close_timeout=timedelta(seconds=5)),
               activity_as_tool(Beneficiaries.add_beneficiary,
                                start_to_close_timeout=timedelta(seconds=5)),
               activity_as_tool(Beneficiaries.delete_beneficiary,
                                start_to_close_timeout=timedelta(seconds=5))
               ],
    )

    investment_agent = Agent[WealthManagementContext](
        name=INVEST_AGENT_NAME,
        handoff_description=INVEST_HANDOFF,
        instructions=INVEST_INSTRUCTIONS,
        tools=[activity_as_tool(Investments.list_investments,
                                start_to_close_timeout=timedelta(seconds=5)),
               activity_as_tool(Investments.open_investment,
                                start_to_close_timeout=timedelta(seconds=5)),
               activity_as_tool(Investments.close_investment,
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
        self.chat_history: list[str] = []
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
    def get_chat_history(self) -> list[str]:
        return self.chat_history

    @workflow.signal
    async def end_workflow(self):
        self.end_workflow = True

    @workflow.update
    async def process_user_message(self, input: ProcessUserMessageInput) -> list[str]:
        workflow.logger.info("processing user message")
        length = len(self.chat_history)
        self.chat_history.append(f"User: {input.user_input}")
        with trace("wealth management", group_id=workflow.info().workflow_id):
            self.input_items.append({"content": input.user_input, "role": "user"})
            result = await Runner.run(
                self.current_agent,
                self.input_items,
                context=self.context,
                run_config=self.run_config,
            )

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    self.chat_history.append(f"{agent_name} {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    self.chat_history.append(f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
                elif isinstance(new_item, ToolCallItem):
                    workflow.logger.info(f"{agent_name}: Calling a tool")
                    self.chat_history.append(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    workflow.logger.info(f"{agent_name}: Tool call output: {new_item.output}")
                    self.chat_history.append(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    self.chat_history.append(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            self.input_items = result.to_input_list()
            self.current_agent = result.last_agent

        workflow.set_current_details("\n\n".join(self.chat_history))
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
        if input.chat_length != len(self.chat_history):
            workflow.logger.error(f"Stale chat history length does not match {input.chat_length} != {len(self.chat_history)}")
            raise ValueError("Stale chat history. Please refresh the chat history.")