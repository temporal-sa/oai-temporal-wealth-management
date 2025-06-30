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

