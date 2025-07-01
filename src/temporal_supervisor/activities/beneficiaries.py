import json
from dataclasses import dataclass


from temporalio import activity, workflow

from common.beneficiaries_manager import BeneficiariesManager

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel

@dataclass
class Beneficiary:
    account_id: str
    first_name: str
    last_name: str
    relationship: str

@dataclass
class BeneficiaryInput:
    beneficiary: Beneficiary

@activity.defn
async def add_beneficiary(account_id: str, first_name: str, last_name: str, relationship: str):
    activity.logger.info(f"add_beneficiary: input: {account_id}, {first_name}, {last_name}, {relationship}")
    beneficiaries_mgr = BeneficiariesManager()
    beneficiaries_mgr.add_beneficiary(account_id, first_name, last_name, relationship)

class Beneficiaries:
    # Note for this demo, it references a file
    # a production level version would point to a data store
    @staticmethod
    @activity.defn
    async def list_beneficiaries(account_id: str) -> list:
        activity.logger.info(f"list_beneficiaries: Listing beneficiaries for {account_id}")
        data_dict = json.loads(account_id)
        activity.logger.info(f"input arguments: {data_dict}")
        acc_id = data_dict["account_id"]
        beneficiaries_mgr = BeneficiariesManager()
        return beneficiaries_mgr.list_beneficiaries(acc_id)

    # @staticmethod
    # @activity.defn
    # async def add_beneficiary(account_id: str, first_name: str, last_name: str, relationship: str):
    #     activity.logger.info(f"add_beneficiary: input: {account_id}, {first_name}, {last_name}, {relationship}")
    #     beneficiaries_mgr = BeneficiariesManager()
    #     beneficiaries_mgr.add_beneficiary(account_id, first_name, last_name, relationship)

    @staticmethod
    @activity.defn
    async def delete_beneficiary(account_id: str, beneficiary_id: str):
        activity.logger.info(f"delete_beneficiary: account ID {account_id}, beneficiary_id: {beneficiary_id}")
        data_dict = json.loads(account_id)
        acc_id = data_dict["account_id"]
        bene_id = data_dict["beneficiary_id"]
        beneficiaries_mgr = BeneficiariesManager()
        beneficiaries_mgr.delete_beneficiary(acc_id, bene_id)