from temporalio import activity, workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from common.funding_manager import FundingManager, InsufficientFundsError
    from temporal_supervisor.chaos import maybe_slow_down


class Funding:
    """Moves money to and from the client's linked bank account.

    Each call takes a transfer ID that is stable across retries, so a retried
    activity never moves the money twice.
    """

    @staticmethod
    @activity.defn
    async def debit_linked_account(client_id: str, amount: float, transfer_id: str) -> dict:
        activity.logger.info(f"debit_linked_account: {client_id}, {amount}, {transfer_id}")
        await maybe_slow_down()
        try:
            return FundingManager().debit(client_id, amount, transfer_id)
        except InsufficientFundsError as e:
            # A business-rule failure: retrying will not make the money appear.
            raise ApplicationError(str(e), type="InsufficientFunds", non_retryable=True)

    @staticmethod
    @activity.defn
    async def credit_linked_account(client_id: str, amount: float, transfer_id: str) -> dict:
        """Refund money to the client's linked bank account (saga compensation)."""
        activity.logger.info(f"credit_linked_account: {client_id}, {amount}, {transfer_id}")
        await maybe_slow_down()
        return FundingManager().credit(client_id, amount, transfer_id)
