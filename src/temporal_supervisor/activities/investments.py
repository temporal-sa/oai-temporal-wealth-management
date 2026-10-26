from typing import Optional

from temporalio import activity, workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from common.investment_manager import InvestmentManager, InvestmentAccount
    from common.chaos_manager import ChaosFlag
    from temporal_supervisor.chaos import core_banking_api, is_enabled, maybe_slow_down

MIN_INITIAL_DEPOSIT = 100.0
MAX_INITIAL_DEPOSIT = 1_000_000.0
WELCOME_BONUS_PROMO = "WELCOME-BONUS"


class Investments:
    @staticmethod
    @activity.defn
    async def list_investments(client_id :str) -> list:
        activity.logger.info(f"Listing investments for {client_id}")
        await core_banking_api()
        investment_acct_mgr = InvestmentManager()
        return investment_acct_mgr.list_investment_accounts(client_id)

    @staticmethod
    @activity.defn
    async def validate_new_account(client_id: str, account_name: str, initial_amount: float) -> None:
        """Check the business rules for opening an account. Raises a non-retryable error if one fails."""
        activity.logger.info(f"Validating new account for {client_id}, "
                             f"Name: {account_name}, Initial amount: {initial_amount}")
        if initial_amount < MIN_INITIAL_DEPOSIT:
            raise ApplicationError(
                f"The initial deposit must be at least ${MIN_INITIAL_DEPOSIT:,.2f}",
                type="DepositBelowMinimum",
                non_retryable=True,
            )
        if initial_amount > MAX_INITIAL_DEPOSIT:
            raise ApplicationError(
                f"Initial deposits over ${MAX_INITIAL_DEPOSIT:,.2f} cannot be opened online "
                "and must be arranged with a wealth advisor",
                type="DepositLimitExceeded",
                non_retryable=True,
            )

    @staticmethod
    @activity.defn
    async def find_promotion(client_id: str) -> Optional[str]:
        """The promo code for a new account, if a promotion is running.

        The chaos panel's "Bug in workflow code" switch runs the welcome-bonus
        promotion, whose code path in OpenInvestmentAccountWorkflow has a bug.
        """
        activity.logger.info(f"Finding promotions for {client_id}")
        return WELCOME_BONUS_PROMO if await is_enabled(ChaosFlag.WORKFLOW_BUG) else None

    @staticmethod
    @activity.defn
    async def open_investment(new_account: InvestmentAccount) -> dict:
        activity.logger.info(f"Opening an investment account for {new_account.client_id}, "
                             f"Name: {new_account.name}, Balance: {new_account.balance}")
        await maybe_slow_down()
        await core_banking_api()
        investment_acct_mgr = InvestmentManager()
        return investment_acct_mgr.add_investment_account(new_account)

    @staticmethod
    @activity.defn
    async def remove_investment(client_id: str, investment_id: str) -> bool:
        """Remove an investment account record (saga compensation for open_investment)."""
        activity.logger.info(f"Removing investment {client_id}, Investment ID: {investment_id}")
        await maybe_slow_down()
        await core_banking_api()
        investment_acct_mgr = InvestmentManager()
        investment_acct_mgr.delete_investment_account(client_id, investment_id)
        # Already gone counts as removed, so a retried compensation succeeds.
        return True

    @staticmethod
    @activity.defn
    async def close_investment(client_id: str, investment_id: str):
        activity.logger.info(f"Closing investment {client_id}, Investment ID: {investment_id} ")
        await core_banking_api()
        investment_acct_mgr = InvestmentManager()
        investment_acct_mgr.delete_investment_account(client_id, investment_id)
