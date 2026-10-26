import asyncio
import logging
import os
from datetime import timedelta
from typing import Optional, Sequence, Callable, Type

from agents import Model, ModelProvider
import httpx
from openai import AsyncOpenAI
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

from common.client_helper import ClientHelper
from temporal_supervisor.activities.clients import ClientActivities
from temporal_supervisor.activities.event_stream_activities import EventStreamActivities
from temporal_supervisor.activities.open_account import OpenAccount
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin, ModelActivityParameters

from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin

from temporal_supervisor.activities.beneficiaries import Beneficiaries
from temporal_supervisor.activities.custodian import Custodian
from temporal_supervisor.activities.funding import Funding
from temporal_supervisor.activities.investments import Investments
from temporal_supervisor.model_config import ChaosAwareOpenAIModel
from temporal_supervisor.retry_policies import LLM_RETRY_POLICY

from temporal_supervisor.workflows.supervisor_workflow import (
    WealthManagementWorkflow
)
from temporal_supervisor.workflows.open_account_workflow import (
    OpenInvestmentAccountWorkflow
)

openai_client = AsyncOpenAI(
    base_url="https://api.openai.com/v1",  # Override for alternate endpoint
    api_key=os.getenv("OPENAI_API_KEY"),
    # Let the Temporal activity retry policy decide how failed model calls are retried
    max_retries=0,
    http_client=httpx.AsyncClient(
        verify=True,  # change to set client cert
    ),
)


class CustomModelProvider(ModelProvider):
    def get_model(self, model_name: Optional[str]) -> Model:
        model = ChaosAwareOpenAIModel(
            model=model_name if model_name else "gpt-4o",
            openai_client=openai_client,
        )
        return model

def choose_workflows(client_helper: ClientHelper) -> Sequence[Type]:
    # returns the workflows depending if we have one or two task queues
    if client_helper.taskQueue == client_helper.taskQueueOpenAccount:
        return [
            WealthManagementWorkflow,
            OpenInvestmentAccountWorkflow
        ]
    else:
        return [
            WealthManagementWorkflow,
        ]

async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s")

    client_helper = ClientHelper()
    # Normally we would just include the OpenAIAgentsPlugin and the
    # ClaimCheckPlugin. But, when we want to just test the
    # child open account workflow, we don't need the OpenAIAgentsPlugin
    plugins = [ ClaimCheckPlugin() ] if client_helper.skipOpenAIPlugin else \
        [ OpenAIAgentsPlugin(
            model_provider=CustomModelProvider(),
            model_params=ModelActivityParameters(
                task_queue=client_helper.taskQueueLLM,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=LLM_RETRY_POLICY,
            ),
          ),
         ClaimCheckPlugin()
        ]
    print(f"address is {client_helper.address} and plugins are {plugins}")
    plugins = plugins
    client = await Client.connect(**client_helper.client_config,
                                  plugins=plugins)

    # for the demo, we're using the same task queue as
    # the agents and the child workflow. In a production
    # situation, this would likely be a different task queue
    worker = Worker(
        client,
        task_queue=client_helper.taskQueue,
        workflows=choose_workflows(client_helper),
        activities=[
            Beneficiaries.list_beneficiaries,
            Beneficiaries.add_beneficiary,
            Beneficiaries.delete_beneficiary,
            Investments.list_investments,
            Investments.validate_new_account,
            Investments.find_promotion,
            Investments.open_investment,
            Investments.remove_investment,
            Investments.close_investment,
            Funding.debit_linked_account,
            Funding.credit_linked_account,
            Custodian.register_account,
            ClientActivities.get_client,
            ClientActivities.add_client,
            ClientActivities.update_client,
            OpenAccount.get_current_client_info,
            OpenAccount.update_client_details,
            OpenAccount.approve_kyc,
            EventStreamActivities.append_chat_interaction,
            EventStreamActivities.append_status_update,
            EventStreamActivities.delete_conversation,
        ],
    )
    if client_helper.skipOpenAIPlugin:
        print(f"Running worker on {client_helper.address}")
        await worker.run()
        return

    # Model calls run on their own task queue. The OpenAIAgentsPlugin registers the
    # model activity on every worker built from the client, so this worker needs
    # nothing else. Setting LLM_MAX_CALLS_PER_SECOND has the Temporal service rate
    # limit model calls across all workers, so they queue up instead of hitting the
    # provider's rate limit.
    max_llm_calls = os.getenv("LLM_MAX_CALLS_PER_SECOND")
    llm_worker = Worker(
        client,
        task_queue=client_helper.taskQueueLLM,
        max_task_queue_activities_per_second=float(max_llm_calls) if max_llm_calls else None,
    )
    print(f"Running worker on {client_helper.address}. "
          f"Model calls on {client_helper.taskQueueLLM}, max calls per second: {max_llm_calls or 'unlimited'}")
    await asyncio.gather(worker.run(), llm_worker.run())

if __name__ == '__main__':
    asyncio.run(main())
