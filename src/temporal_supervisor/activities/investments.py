import json

from temporalio import activity

from common.investment_account_manager import InvestmentAccountManager

class Investments:
    @staticmethod
    @activity.defn
    async def list_investments(account_id :str ) -> list:
        activity.logger.info(f"Listing investments for {account_id}")
        investment_acct_mgr = InvestmentAccountManager()
        return investment_acct_mgr.list_investment_accounts(account_id)

    @staticmethod
    @activity.defn
    async def open_investment(account_id: str, name: str, balance: str) -> dict:
        activity.logger.info(f"Opening an investment account for {account_id}, Name: {name}, Balance: {balance}")
        investment_acct_mgr = InvestmentAccountManager()
        return investment_acct_mgr.add_investment_account(account_id, name, balance)

    @staticmethod
    @activity.defn
    async def close_investment(account_id: str, investment_id: str):
        activity.logger.info(f"Closing investment {account_id}, Investment ID: {investment_id} ")
        investment_acct_mgr = InvestmentAccountManager()
        investment_acct_mgr.delete_investment_account(account_id, investment_id)

