import argparse
import asyncio
import logging

from temporalio.client import Client, WorkflowHandle
from common.client_helper import ClientHelper

from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin
from temporal_supervisor.open_account_workflow import OpenInvestmentAccountWorkflow


async def approve(workflow_id: str):
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

    handle = client.get_workflow_handle(workflow_id=workflow_id)
    await handle.signal(OpenInvestmentAccountWorkflow.compliance_approved)

async def main():
    parser = argparse.ArgumentParser(
        description="",
        epilog="Example usage:\n"
               "  export SKIP_OPENAI_PLUGIN=True; python run_send_compliance_approval.py --workflow-id myworkflow\n"
    )

    # Global argument for Workflow ID
    parser.add_argument(
        '--workflow-id',
        type=str,
        required=True,
        help='The ID of the workflow to send the approval to'
    )

    args = parser.parse_args()
    await approve(args.workflow_id)

if __name__ == "__main__":
    asyncio.run(main())