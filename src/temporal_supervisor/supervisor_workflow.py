from temporalio import workflow

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
    from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
    from pydantic import BaseModel

### Context

class WealthManagementContext(BaseModel):
    account_id: str | None = None


### Tools

@function_tool
async def list_beneficiaries(
        context: RunContextWrapper[WealthManagementContext], account_id: str
) -> dict:
    """
    List the beneficiaries for the given account id.

    Args:
        account_id: The customer's account id
    """
    # update the context
    context.context.account_id = account_id
    return [
        { "Fred", "son" },
        { "Sandy", "daughter" },
        { "Jessica", "daughter" },
    ]

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
        name="Beneficiary Agent",
        handoff_description="A helpful agent that handles changes to a customers beneficiaries.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
        You are a beneficiary agent. If you are speaking with a customer you were likely transfered from the supervisor agent.
        # Routine
        1. Ask for their account id if you don't already have one.
        2. Display a list of their beneficaires using the list_beneficiaries tool.
        If the customer asks a question that is not related to the routine, transfer back to the supervisor agent.""",
        tools=[list_beneficiaries],
    )

    investment_agent = Agent[WealthManagementContext](
        name="Investment Agent",
        handoff_description="A helpful agent that handles a customers's investment accounts.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
        You are an investment agent. If you are speaking with a customer, you were likely transfered from the supervisor agent.
        # Routine
        1. Ask for their account id if you don't already have one.
        2. Display a list of their accounts and balances using the list_investments tool
        If the customer asks a question that is not related to the routine, transfer back to the supervisor agent.""",
        tools=[list_investments],
    )

    supervisor_agent = Agent[WealthManagementContext](
        name="Supervisor Agent",
        handoff_description="A supervisor agent that can delegate customer's requests to the appropriate agent",
        instructions=f""""{RECOMMENDED_PROMPT_PREFIX}
        You are a helpful agent. You can use your tools to delegate questions to other appropriate agents
        # Routine
        1. if you don't have an account ID, ask for one
        2. Route to another agent""",
        handoffs=[
            beneficiary_agent,
            investment_agent,
        ]
    )

    beneficiary_agent.handoffs.append(supervisor_agent)
    investment_agent.handoffs.append(supervisor_agent)
    return supervisor_agent

class ProcessUserMessageInput(BaseModel):
    user_input: str
    chat_length: int

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
                    self.chat_history.append(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    self.chat_history.append(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    self.chat_history.append(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            self.input_items = result.to_input_list()
            self.current_agent = result.last_agent

        workflow.set_current_details("\n\n".join(self.chat_history))
        return self.chat_history[length:]

    @process_user_message.validator
    def validate_process_user_message(self, input: ProcessUserMessageInput) -> None:
        if not input.user_input:
            raise ValueError("Input cannot be empty")
        if len(input.user_input) > 1000:
            raise ValueError("Input is too long. Please limit to 1000 characters")
        if input.chat_length != len(self.chat_history):
            raise ValueError("Stale chat history. Please refresh the chat history.")