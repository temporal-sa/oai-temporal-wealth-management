from dataclasses import asdict

from temporalio import workflow, activity
from temporalio.client import WorkflowHandle, Client
from temporalio.workflow import ParentClosePolicy
from common.client_helper import ClientHelper
from temporal_supervisor.workflows.open_account_workflow import OpenInvestmentAccountWorkflow, OpenInvestmentAccountInput
from temporal_supervisor.activities.clients import WealthManagementClient

from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin

with workflow.unsafe.imports_passed_through():
    from agents import function_tool

@function_tool
async def open_new_investment_account(account_input: OpenInvestmentAccountInput) -> str:
    # We are in the context of the main workflow
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
        the_client = await Client.connect(target_host=client_helper.address,
                                          namespace=client_helper.namespace,
                                          tls=client_helper.get_tls_config(),
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
