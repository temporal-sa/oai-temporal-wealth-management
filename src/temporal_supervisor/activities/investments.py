import json

from temporalio import activity

from common.investment_account_manager import InvestmentAccountManager

class Investments:
    @staticmethod
    @activity.defn
    async def list_investments(account_id :str ) -> list:
        activity.logger.info(f"Listing investments for {account_id}")
        data_dict = json.loads(account_id)
        activity.logger.info(f"input arguments: {data_dict}")
        account = data_dict["account_id"]
        investment_acct_mgr = InvestmentAccountManager()
        return investment_acct_mgr.list_investment_accounts(account)

    @staticmethod
    @activity.defn
    async def open_investment(account_id: str, name: str, balance: str) -> dict:
        activity.logger.info(f"Opening an investment account for {account_id}, Name: {name}, Balance: {balance}")
        data_dict = json.loads(account_id)
        acc_id = data_dict["account_id"]
        a_name = data_dict["name"]
        a_balance = data_dict["balance"]
        investment_acct_mgr = InvestmentAccountManager()
        return investment_acct_mgr.add_investment_account(acc_id, a_name, a_balance)

    @staticmethod
    @activity.defn
    async def close_investment(account_id: str, investment_id: str):
        activity.logger.info(f"Closing investment {account_id}, Investment ID: {investment_id} ")
        data_dict = json.loads(account_id)
        acc_id = data_dict["account_id"]
        invest_id = data_dict["investment_id"]
        investment_acct_mgr = InvestmentAccountManager()
        investment_acct_mgr.delete_investment_account(acc_id, invest_id)

