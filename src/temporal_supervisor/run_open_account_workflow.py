import asyncio
import logging

from temporalio.client import Client
from common.client_helper import ClientHelper

from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporal_supervisor.claim_check_plugin import ClaimCheckPlugin
from temporal_supervisor.open_account_workflow import OpenInvestmentAccountWorkflow, OpenInvestmentAccountInput


async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")

    client_helper = ClientHelper()
    print(f"address is {client_helper.address}")
    client = await Client.connect(target_host=client_helper.address,
                                  namespace=client_helper.namespace,
                                  tls=client_helper.get_tls_config(),
                                  plugins=[
                                      # OpenAIAgentsPlugin(),
                                      ClaimCheckPlugin()
                                  ])

    new_investment = OpenInvestmentAccountInput(
        client_id="123",
        account_name="Vacation",
        initial_amount=150.78)

    # for the demo, we're using the same task queue as
    # the agents. In a production situation, this
    # would likely be a different task queue
    handle = await client.start_workflow(
        OpenInvestmentAccountWorkflow.run,
        args=[new_investment],
        id="testing-open-investment-account-workflow",
        task_queue=client_helper.taskQueue)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"The current state is {the_state}")

    # give a pause before continuing
    await asyncio.sleep(1)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"After sleeping, the current state is {the_state}")

    # verify KYC
    await handle.signal(OpenInvestmentAccountWorkflow.verify_kyc)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"After verifying KYC, the current state is {the_state}")

    # give a pause before continuing
    await asyncio.sleep(1)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"Before signaling compliance approved, the current state is {the_state}")

    # signal compliance approved
    await handle.signal(OpenInvestmentAccountWorkflow.compliance_approved)

    print(f"After compliance approved, the current state is {the_state}")

    # get the result
    result = await handle.result()
    print(f"The result from the workflow execution is {result}")


if __name__ == "__main__":
    asyncio.run(main())