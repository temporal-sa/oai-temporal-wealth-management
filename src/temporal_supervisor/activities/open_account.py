from dataclasses import asdict
from datetime import timedelta

from temporalio import workflow, activity
from temporalio.client import WorkflowHandle, Client
from temporalio.exceptions import ActivityError, ApplicationError
from temporalio.workflow import ParentClosePolicy
from common.client_helper import ClientHelper
from temporal_supervisor.workflows.open_account_workflow import OpenInvestmentAccountWorkflow, OpenInvestmentAccountInput
from temporal_supervisor.activities.clients import WealthManagementClient
from temporal_supervisor.activities.investments import Investments
from temporal_supervisor.retry_policies import TOOL_RETRY_POLICY

from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin

with workflow.unsafe.imports_passed_through():
    from agents import function_tool

@function_tool
async def open_new_investment_account(client_id: str, account_name: str, initial_amount: float) -> str:
    """Begin opening a new investment account.

    Args:
        client_id: The customer's client ID.
        account_name: The name for the new investment account.
        initial_amount: The initial deposit amount.

    Returns:
        The workflow ID of the account opening, which the other open-account tools
        require, or the reason the account cannot be opened.
    """
    # We are in the context of the main workflow

    # Business rules are checked up front. A violation is a non-retryable error:
    # it fails on the first attempt, and the reason goes back to the agent.
    try:
        await workflow.execute_activity(
            Investments.validate_new_account,
            args=[client_id, account_name, initial_amount],
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=TOOL_RETRY_POLICY)
    except ActivityError as e:
        # The agent would only see str(e), which is "Activity task failed";
        # pass the business reason through instead.
        if isinstance(e.__cause__, ApplicationError):
            return f"The account cannot be opened: {e.__cause__.message}"
        raise

    # Read in an activity so the result is recorded in history and replays the same.
    promo_code = await workflow.execute_activity(
        Investments.find_promotion,
        client_id,
        start_to_close_timeout=timedelta(seconds=5),
        retry_policy=TOOL_RETRY_POLICY)
    account_input = OpenInvestmentAccountInput(client_id=client_id,
                                               account_name=account_name,
                                               initial_amount=initial_amount,
                                               promo_code=promo_code)

    # retrieve the current workflow id
    current_workflow_id = workflow.info().workflow_id
    child_workflow_id = f"OpenAccount-{current_workflow_id}-{account_input.client_id}-{account_input.account_name}"
    await workflow.start_child_workflow(
        OpenInvestmentAccountWorkflow.run,
        args=[account_input],
        id=child_workflow_id,
        parent_close_policy=ParentClosePolicy.TERMINATE,
    )
    # can't return the handle as we need something serializable for the other activities
    return child_workflow_id

class OpenAccount:

    @staticmethod
    async def get_workflow_handle(workflow_id) -> WorkflowHandle:
        client_helper = ClientHelper()
        print(f"(OpenAccount.get_temporal_client) address is {client_helper.address}")
        the_client = await Client.connect(**client_helper.client_config,
                                          plugins=[
                                             # OpenAIAgentsPlugin(),
                                             ClaimCheckPlugin()
                                         ])
        return the_client.get_workflow_handle_for(OpenInvestmentAccountWorkflow.run, workflow_id)

    @staticmethod
    @activity.defn
    async def get_current_client_info(workflow_id: str) -> WealthManagementClient:
        # get the handle from the workflow id
        handle = await OpenAccount.get_workflow_handle(workflow_id)
        client = await handle.execute_update(OpenInvestmentAccountWorkflow.get_client_details)
        return client

    @staticmethod
    @activity.defn
    async def approve_kyc(workflow_id: str):
        # get the handle from the workflow id
        handle = await OpenAccount.get_workflow_handle(workflow_id)
        await handle.signal(OpenInvestmentAccountWorkflow.verify_kyc)

    @staticmethod
    @activity.defn
    async def update_client_details(workflow_id: str, client_details: WealthManagementClient) -> str:
        # get the handle from the workflow id
        handle = await OpenAccount.get_workflow_handle(workflow_id)
        # convert the dataclass to a dict
        client_details_dict = asdict(client_details)
        result = await handle.execute_update(OpenInvestmentAccountWorkflow.update_client_details,
                                             args=[client_details_dict])
        return result
