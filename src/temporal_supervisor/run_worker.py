import asyncio
import concurrent.futures
from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.openai_agents.invoke_model_activity import ModelActivity
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)
from temporalio.worker import Worker

from temporal_supervisor.client_helper import ClientHelper

with workflow.unsafe.imports_passed_through():
    from temporal_supervisor.supervisor_workflow import (
        WealthManagementWorkflow
    )

from temporalio.contrib.openai_agents.temporal_openai_agents import (
    set_open_ai_agent_temporal_overrides,
)

async def main():
    with set_open_ai_agent_temporal_overrides(
        start_to_close_timeout=timedelta(seconds=60),
    ):
        client_helper = ClientHelper()
        client = await client_helper.get_client(open_ai_data_converter)

        model_activity = ModelActivity(model_provider=None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as activity_executor:
            worker = Worker(
                client,
                task_queue=client_helper.taskQueue,
                workflows=[WealthManagementWorkflow],
                activities=[
                    model_activity.invoke_model_activity
                ],
                activity_executor=activity_executor,
            )
            print(f"Running worker on {client_helper.address}")
            await worker.run()

if __name__ == '__main__':
    asyncio.run(main())