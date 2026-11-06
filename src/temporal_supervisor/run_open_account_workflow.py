import asyncio
import logging

from temporalio.client import Client
from common.client_helper import ClientHelper

from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin
from temporal_supervisor.workflows.open_account_workflow import OpenInvestmentAccountWorkflow, OpenInvestmentAccountInput


async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")

    client_helper = ClientHelper()
    print(f"address is {client_helper.address}, open-account task queue is {client_helper.taskQueueOpenAccount}")
    client = await Client.connect(**client_helper.client_config,
                                  plugins=[
                                      # OpenAIAgentsPlugin(),
                                      ClaimCheckPlugin()
                                  ])
    print("Running the first scenario:")
    await scenario1(client, client_helper)
    print("Running the second scenario:")
    await scenario2(client, client_helper)
    print("Running the third scenario:")
    await scenario3(client, client_helper)

async def scenario1(client : Client, client_helper: ClientHelper):
    new_investment = OpenInvestmentAccountInput(
        client_id="123",
        account_name="Vacation",
        initial_amount=150.78)

    # The Open Account task queue (TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT) defaults to the
    # agents' task queue; set it to run the workflow on the Java worker's queue.
    handle = await client.start_workflow(
        OpenInvestmentAccountWorkflow.run,
        args=[new_investment],
        id="testing-open-investment-account-workflow",
        task_queue=client_helper.taskQueueOpenAccount)

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

async def scenario2(client : Client, client_helper: ClientHelper):
    new_investment = OpenInvestmentAccountInput(
        client_id="123",
        account_name="Vacation2",
        initial_amount=350.72)

    # The Open Account task queue (TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT) defaults to the
    # agents' task queue; set it to run the workflow on the Java worker's queue.
    handle = await client.start_workflow(
        OpenInvestmentAccountWorkflow.run,
        args=[new_investment],
        id="testing-open-investment-account-workflow-2",
        task_queue=client_helper.taskQueueOpenAccount)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"The current state is {the_state}")

    # give a pause before continuing
    await asyncio.sleep(1)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"After sleeping, the current state is {the_state}")

    # get the current customer info
    customer_details = await handle.execute_update(OpenInvestmentAccountWorkflow.get_client_details)
    print(f"Customer details are {customer_details}")

    # now update customer details
    changed_dict = { "last_name": "Doenut" }
    result = await handle.execute_update(OpenInvestmentAccountWorkflow.update_client_details, changed_dict)
    print(f"The result from updating client details is {result}")

    # after this KYC is verified

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"After verifying KYC, the current state is {the_state}")

    # give a pause before continuing
    await asyncio.sleep(1)

    the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
    print(f"Before signaling compliance approved, the current state is {the_state}")

    # signal compliance approved
    # (Normally this would be done outside of the app)
    await handle.signal(OpenInvestmentAccountWorkflow.compliance_approved)

    print(f"After compliance approved, the current state is {the_state}")

    # get the result
    result = await handle.result()
    print(f"The result from the second scenario is {result}")

async def scenario3(client : Client, client_helper: ClientHelper):
    new_investment = OpenInvestmentAccountInput(
        client_id="123",
        account_name="Vacation3",
        initial_amount=176.73)

    # The Open Account task queue (TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT) defaults to the
    # agents' task queue; set it to run the workflow on the Java worker's queue.
    workflow_id = "testing-open-investment-account-workflow3"
    handle = await client.start_workflow(
        OpenInvestmentAccountWorkflow.run,
        args=[new_investment],
        id=workflow_id,
        task_queue=client_helper.taskQueueOpenAccount)

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

    while True:
        # pause before continuing
        print(f"*****>>> Remember to signal this workflow: {workflow_id}")
        await asyncio.sleep(1)

        the_state = await handle.query(OpenInvestmentAccountWorkflow.get_current_state)
        print(f"Before signaling compliance approved, the current state is {the_state}")
        if the_state != "Waiting Compliance Review":
            break

    print(f"Out of the loop, the current state is {the_state}")

    # get the result
    result = await handle.result()
    print(f"The result from the workflow execution is {result}")

if __name__ == "__main__":
    asyncio.run(main())