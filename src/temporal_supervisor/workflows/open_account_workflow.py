from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.exceptions import ActivityError, ApplicationError

from common.investment_manager import InvestmentAccount
from common.account_context import UpdateAccountOpeningStateInput

with workflow.unsafe.imports_passed_through():
    from temporal_supervisor.activities.clients import ClientActivities
    from temporal_supervisor.activities.custodian import Custodian
    from temporal_supervisor.activities.funding import Funding
    from temporal_supervisor.activities.investments import Investments
    from temporal_supervisor.retry_policies import TOOL_RETRY_POLICY

@dataclass
class OpenInvestmentAccountInput:
    client_id: str
    account_name: str
    initial_amount: float
    promo_code: Optional[str] = None

@dataclass
class OpenInvestmentAccountOutput:
    account_created: bool = False
    message : str = None

@dataclass
class WealthManagementClient:
    first_name: str = None
    last_name: str = None
    address: str = None
    phone: str = None
    email: str = None
    marital_status: str= None


@workflow.defn
class OpenInvestmentAccountWorkflow:
    def __init__(self):
        self.client = None
        self.inputs: OpenInvestmentAccountInput
        self.initialized = False
        # Bounds a single attempt only, so an outage is retried for as long as it lasts.
        self.start_to_close_timeout = timedelta(seconds=30)
        self.kyc_verified = False
        self.compliance_reviewed = False
        self.current_state = "Initializing"

    @workflow.run
    async def run(self, inputs: OpenInvestmentAccountInput) -> OpenInvestmentAccountOutput:
        workflow.logger.info(f"started workflow {inputs}")
        self.inputs = inputs

        workflow.logger.info(f"Retrieving current client information")
        self.client = await self._execute(ClientActivities.get_client, self.inputs.client_id)
        workflow.logger.info(f"Client {self.inputs.client_id} details {self.client}")
        self.initialized = True
        await self._set_state("Waiting KYC")

        # wait until the user has validated their information is correct
        workflow.logger.info("Waiting for KYC Verification")
        await workflow.wait_condition(lambda: self.kyc_verified)

        await self._set_state("Waiting Compliance Review")

        # wait until compliance review is complete
        # consider implementing a timeout condition
        workflow.logger.info("Waiting for compliance review")
        await workflow.wait_condition(lambda: self.compliance_reviewed)

        await self._set_state("Compliance review has been approved. Creating Investment Account")
        return await self._open_account(inputs)

    async def _open_account(self, inputs: OpenInvestmentAccountInput) -> OpenInvestmentAccountOutput:
        """Saga: create, fund, and register the account.

        Each completed step records how to undo it. If a later step fails with a
        non-retryable error, the recorded compensations run in reverse order.
        Transient failures never get here: activities retry until they succeed.
        """
        amount = inputs.initial_amount
        bonus = self._welcome_bonus(inputs) if inputs.promo_code else 0.0
        # Idempotency key: stable across activity retries and worker restarts. It
        # includes the run ID because the workflow ID is reused when the customer
        # opens an account with the same name again (e.g. after a rollback).
        transfer_id = f"{workflow.info().workflow_id}-{workflow.info().run_id}-initial-deposit"
        compensations = []  # (description, activity, args)
        try:
            await self._set_state("Creating the account record.")
            account = await self._execute(
                Investments.open_investment,
                InvestmentAccount(inputs.client_id, inputs.account_name, amount + bonus))
            investment_id = account["investment_id"]
            compensations.append(
                ("removing the account record", Investments.remove_investment, [inputs.client_id, investment_id]))

            await self._set_state(f"Transferring ${amount:,.2f} from the linked bank account.")
            await self._execute(Funding.debit_linked_account, inputs.client_id, amount, transfer_id)
            compensations.append(
                (f"refunding ${amount:,.2f} to the linked bank account",
                 Funding.credit_linked_account,
                 [inputs.client_id, amount, f"{transfer_id}-refund"]))

            await self._set_state("Registering the account with the custodian.")
            await self._execute(Custodian.register_account, inputs.client_id, investment_id, amount)
        except ActivityError as e:
            cause = e.__cause__
            reason = cause.message if isinstance(cause, ApplicationError) else str(cause or e)
            await self._set_state(f"Failed: {reason}. Rolling back.")
            for description, activity_fn, args in reversed(compensations):
                await self._set_state(f"Rolling back: {description}.")
                await self._execute(activity_fn, *args)
            await self._set_state(f"Rolled back. The account was not opened: {reason}.")
            return OpenInvestmentAccountOutput(account_created=False,
                                               message=f"The account was not opened: {reason}")

        await self._set_state("Complete")
        return OpenInvestmentAccountOutput(account_created=True, message="investment account created")

    @staticmethod
    def _welcome_bonus(inputs: OpenInvestmentAccountInput) -> float:
        """Welcome-bonus promotion: 1% of the initial deposit, up to $500."""
        # *** Bug-In-Workflow-Code ***
        # Intentional bug for the "Bug in workflow code" demo: OpenInvestmentAccountInput has no
        # initial_deposit field (it's initial_amount), so the line below raises an AttributeError.
        # To fix it, uncomment the first line below and comment out the second.
        # See README "Failure scenarios".
        # return min(inputs.initial_amount * 0.01, 500.0)
        return min(inputs.initial_deposit * 0.01, 500.0)

    async def _execute(self, activity_fn, *args):
        return await workflow.execute_activity(
            activity_fn,
            args=list(args),
            start_to_close_timeout=self.start_to_close_timeout,
            retry_policy=TOOL_RETRY_POLICY)

    @workflow.query
    def get_current_state(self) -> str:
        workflow.logger.info(f"Returning current state {self.current_state}")
        return self.current_state

    @workflow.update
    async def get_client_details(self) -> WealthManagementClient:
        workflow.logger.info(f"Returning client information for {self.inputs.client_id}")
        await workflow.wait_condition(lambda: self.initialized)
        return self.client

    @workflow.update
    async def update_client_details(self, client: dict) -> str:
        workflow.logger.info(f"Updating client information for {self.inputs.client_id}")
        result = await self._execute(ClientActivities.update_client, self.inputs.client_id, client)
        self.kyc_verified = True
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

    async def _set_state(self, state: str) -> None:
        self.current_state = state
        await self._update_parent_state(state)

    async def _update_parent_state(self, state: str) -> None:
        if workflow.info().parent is None:
            return

        parent_handle = workflow.get_external_workflow_handle(workflow.info().parent.workflow_id)
        await parent_handle.signal("update_account_opening_state",
                                   UpdateAccountOpeningStateInput(account_name=self.inputs.account_name,
                                                                  state=state,
                                                                  workflow_id=workflow.info().workflow_id))
