from temporalio import activity, workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from common.chaos_manager import ChaosFlag
    from temporal_supervisor.chaos import inject_failure, maybe_slow_down


class Custodian:
    """The third-party custodian that holds the assets of a new investment account."""

    @staticmethod
    @activity.defn
    async def register_account(client_id: str, investment_id: str, amount: float) -> str:
        """Register a new investment account with the custodian. Returns its reference."""
        activity.logger.info(f"register_account: {client_id}, {investment_id}, {amount}")
        await maybe_slow_down()
        await inject_failure(
            ChaosFlag.CUSTODIAN_REJECTS,
            ApplicationError(
                "The custodian rejected the account registration",
                type="CustodianRejected",
                non_retryable=True,
            ),
        )
        return f"CUST-{investment_id}"
