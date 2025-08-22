import json
from dataclasses import dataclass

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from common.investment_manager import InvestmentManager, InvestmentAccount


class Investments:
    @staticmethod
    @activity.defn
    async def list_investments(client_id :str) -> list:
        activity.logger.info(f"Listing investments for {client_id}")
        investment_acct_mgr = InvestmentManager()
        return investment_acct_mgr.list_investment_accounts(client_id)

    @staticmethod
    @activity.defn
    async def open_investment(new_account: InvestmentAccount) -> dict:
        activity.logger.info(f"Opening an investment account for {new_account.client_id}, "
                             f"Name: {new_account.name}, Balance: {new_account.balance}")
        investment_acct_mgr = InvestmentManager()
        return investment_acct_mgr.add_investment_account(new_account)

    @staticmethod
    @activity.defn
    async def close_investment(client_id: str, investment_id: str):
        activity.logger.info(f"Closing investment {client_id}, Investment ID: {investment_id} ")
        investment_acct_mgr = InvestmentManager()
        investment_acct_mgr.delete_investment_account(client_id, investment_id)

