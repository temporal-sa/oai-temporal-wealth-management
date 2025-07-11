import asyncio
import concurrent.futures
import logging
from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.openai_agents import ModelActivity
from temporalio.contrib.openai_agents import ModelActivityParameters
from temporalio.contrib.pydantic import pydantic_data_converter

from temporalio.worker import Worker

from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.investments import Investments
from common.client_helper import ClientHelper

with workflow.unsafe.imports_passed_through():
    from temporal_supervisor.supervisor_workflow import (
        WealthManagementWorkflow
    )

from temporalio.contrib.openai_agents.temporal_openai_agents import (
    set_open_ai_agent_temporal_overrides,
)

async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")
    model_params = ModelActivityParameters(
        start_to_close_timeout=timedelta(seconds=60)
    )
    with set_open_ai_agent_temporal_overrides(model_params):
        client_helper = ClientHelper()
        client = await client_helper.get_client(pydantic_data_converter)

        model_activity = ModelActivity(model_provider=None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as activity_executor:
            worker = Worker(
                client,
                task_queue=client_helper.taskQueue,
                workflows=[WealthManagementWorkflow],
                activities=[
                    Beneficiaries.list_beneficiaries,
                    Beneficiaries.add_beneficiary,
                    Beneficiaries.delete_beneficiary,
                    Investments.list_investments,
                    Investments.open_investment,
                    Investments.close_investment,
                    model_activity.invoke_model_activity
                ],
                activity_executor=activity_executor,
            )
            print(f"Running worker on {client_helper.address}")
            await worker.run()

if __name__ == '__main__':
    asyncio.run(main())