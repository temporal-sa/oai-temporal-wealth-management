import asyncio
import random
import uuid

from pydantic import BaseModel

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

class WealthManagementContext(BaseModel):
    account_id: str | None = None


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
    context.account_id = account_id
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
    context.account_id = account_id
    return [
        { "Checking", 203.45 },
        { "Savings", 375.81 },
        { "Retirement", 24648.63 },
    ]

beneficiary_agent = Agent[WealthManagementContext](
    name="Beneficiary Agent",
    handoff_description="A helpful agent that handles changes to a customers beneficiaries.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a beneficiary agent. If you are speaking with a customer you were likely transfered from the supervisor agent.
    # Routine
    1. Ask for their account id,
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
    1. Ask for their account id.
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
        1. Before routing to another agent, ask for their account ID if you don't already have it.""",
    handoffs=[
        beneficiary_agent,
        investment_agent,
    ]
)

beneficiary_agent.handoffs.append(supervisor_agent)
investment_agent.handoffs.append(supervisor_agent)

async def main():
    current_agent: Agent[WealthManagementContext] = supervisor_agent
    input_items: list[TResponseInputItem] = []
    context = WealthManagementContext()

    conversation_id = uuid.uuid4().hex[:16]

    print("Welcome to ABC Wealth Management. How can I help you?")
    while True:
        user_input = input("Enter your message: ")
        lower_input = user_input.lower() if user_input is not None else ""
        if lower_input == "exit" or lower_input == "end" or lower_input == "quit":
            break
        with trace("wealth management", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items, context=context)
            # print(f"Account ID: {context.account_id}")

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"{agent_name} {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, HandoffOutputItem):
                    print(f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: Calling a tool")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"{agent_name}: Tool call output: {new_item.output}")
                else:
                    print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")
            input_items = result.to_input_list()
            current_agent = result.last_agent

if __name__ == "__main__":
    asyncio.run(main())