import asyncio
import logging

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

from common.client_helper import ClientHelper
from temporal_supervisor.activities.clients import ClientActivities
from temporal_supervisor.activities.open_account import OpenAccount
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin

from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.investments import Investments

with workflow.unsafe.imports_passed_through():
    from temporal_supervisor.supervisor_workflow import (
        WealthManagementWorkflow
    )
    from temporal_supervisor.open_account_workflow import (
        OpenInvestmentAccountWorkflow
    )

async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")

    client_helper = ClientHelper()
    # Normally we would just include the OpenAIAgentsPlugin and the
    # ClaimCheckPlugin. But, when we want to just test the
    # child open account workflow, we don't need the OpenAIAgentsPlugin
    # plugins = [ ClaimCheckPlugin() ] if client_helper.skipOpenAIPlugin else [ OpenAIAgentsPlugin(), ClaimCheckPlugin() ]
    # print(f"address is {client_helper.address} and plugins are {plugins}")
    plugins = [ OpenAIAgentsPlugin(), ClaimCheckPlugin() ]
    client = await Client.connect(target_host=client_helper.address,
                                  namespace=client_helper.namespace,
                                  tls=client_helper.get_tls_config(),
                                  plugins=plugins)

    # for the demo, we're using the same task queue as
    # the agents and the child workflow. In a production
    # situation, this would likely be a different task queue
    worker = Worker(
        client,
        task_queue=client_helper.taskQueue,
        workflows=[
            WealthManagementWorkflow,
            OpenInvestmentAccountWorkflow
        ],
        activities=[
            Beneficiaries.list_beneficiaries,
            Beneficiaries.add_beneficiary,
            Beneficiaries.delete_beneficiary,
            Investments.list_investments,
            Investments.open_investment,
            Investments.close_investment,
            ClientActivities.get_client,
            ClientActivities.add_client,
            ClientActivities.update_client,
            OpenAccount.get_current_client_info,
            OpenAccount.update_client_details,
            OpenAccount.approve_kyc,
            OpenAccount.current_state
        ],
    )
    print(f"Running worker on {client_helper.address}")
    await worker.run()

if __name__ == '__main__':
    asyncio.run(main())