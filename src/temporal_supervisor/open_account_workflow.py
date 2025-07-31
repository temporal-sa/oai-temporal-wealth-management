from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

from temporal_supervisor.activities.clients import Client, ClientActivities
from temporal_supervisor.activities.investments import Investments

@dataclass
class OpenInvestmentAccountInput:
    client_id: str
    account_name: str
    initial_amount: float

@dataclass
class OpenInvestmentAccountOutput:
    account_created: bool = False
    message : str = None

@workflow.defn
class OpenInvestmentAccountWorkflow:
    def __init__(self):
        self.client = None
        self.inputs: OpenInvestmentAccountInput
        self.initialized = False
        self.sched_to_close_timeout = timedelta(seconds=5)
        self.kyc_verified = False
        self.compliance_reviewed = False

    @workflow.run
    async def run(self, inputs: OpenInvestmentAccountInput) -> OpenInvestmentAccountOutput:
        workflow.logger.info(f"started workflow {inputs}")
        self.inputs = inputs

        workflow.logger.info(f"Retrieving current client information")
        self.client = await workflow.execute_activity(
                         ClientActivities.get_client,
                         self.inputs.client_id,
                         schedule_to_close_timeout=self.sched_to_close_timeout,
                         retry_policy=ClientActivities.retry_policy)

        self.initialized = True

        # wait until the user has validated their information is correct
        workflow.logger.info("Waiting for KYC Verification")
        await workflow.wait_condition(lambda: self.kyc_verified)

        # wait until compliance review is complete
        # consider implementing a timeout condition
        workflow.logger.info("Waiting for compliance review")
        await workflow.wait_condition(lambda: self.compliance_reviewed)

        # finally, let's create/open the account
        workflow.logger.info("Creating a new investment account")
        investment_account = await workflow.execute_activity(
            Investments.open_investment,
            args=[self.inputs.client_id, inputs.account_name, inputs.initial_amount],
            schedule_to_close_timeout=self.sched_to_close_timeout,
            retry_policy=ClientActivities.retry_policy)

        return_value = OpenInvestmentAccountOutput()
        return_value.account_created = investment_account is not None
        return_value.message = "investment account created" if investment_account is not None \
                                    else "An unexpected error occurred creating investment account"

        return return_value

    @workflow.query
    async def get_client_details(self) -> Client:
        workflow.logger.info(f"Returning client information for {self.inputs.client_id}")
        await workflow.wait_condition(lambda: self.initialized)
        return self.client

    @workflow.update
    async def update_client_details(self, client: dict) -> str:
        workflow.logger.info(f"Updating client information for {self.inputs.client_id}")
        result = await workflow.execute_activity(
                    ClientActivities.update_client,
                    args=[self.inputs.client_id, client],
                    schedule_to_close_timeout=self.sched_to_close_timeout,
                    retry_policy=ClientActivities.retry_policy)
        return result

    @workflow.signal
    async def verify_kyc(self) -> None:
        await workflow.wait_condition(lambda: self.initialized)
        workflow.logger.info(f"KYC has been verified")
        self.kyc_verified = True

    @workflow.signal
    async def compliance_approved(self) ->None:
        await workflow.wait_condition(lambda: self.initialized and self.kyc_verified)
        workflow.logger.info(f"Compliance has been approved")
        self.compliance_reviewed = True