import json

from temporalio import activity

from common.account_context import AccountContext
from common.beneficiaries_manager import BeneficiariesManager

class Beneficiaries:

    # Note for this demo, it references a file
    # a production level version would point to a data store
    @staticmethod
    @activity.defn
    async def list_beneficiaries(account_id: str) -> list:
        activity.logger.info(f"list_beneficiaries: Listing beneficiaries for {account_id}")
        data_dict = json.loads(account_id)
        activity.logger.info(f"input arguments: {data_dict}")
        account = data_dict["account_id"]
        beneficiaries_mgr = BeneficiariesManager()
        return beneficiaries_mgr.list_beneficiaries(account)
