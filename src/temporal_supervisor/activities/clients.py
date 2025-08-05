from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from common.client_manager import ClientManager

@dataclass
class WealthManagementClient:
    client_id: str
    first_name: str
    last_name: str
    address: str
    phone: str
    email: str
    marital_status: str

class ClientActivities:
    retry_policy = RetryPolicy(initial_interval=timedelta(seconds=1),
                               backoff_coefficient=2,
                               maximum_interval=timedelta(seconds=30))
    @staticmethod
    @activity.defn
    async def add_client(client_id: str, first_name: str, last_name: str, address: str, phone: str, email: str, marital_status: str) -> str:
        activity.logger.info(f"add_account. input: {first_name} {last_name} {address} {phone} {email} {marital_status}")
        account_manager = ClientManager()
        return account_manager.add_client(client_id=client_id,
                                          first_name=first_name,
                                          last_name=last_name,
                                          address=address,
                                          phone=phone,
                                          email=email,
                                          marital_status=marital_status)

    @staticmethod
    @activity.defn
    async def get_client(client_id: str) -> WealthManagementClient | None:
        activity.logger.info(f"get_client. input: {client_id}")
        client_manager = ClientManager()
        client_dict = client_manager.get_client(client_id=client_id)
        activity.logger.info(f"client_dict is {client_dict}")
        if "error" in client_dict:
            print(f"Error after trying to get client {client_id}. {client_dict['error']}")
            return None

        # add the client ID to the dictionary
        client_dict['client_id'] = client_id
        activity.logger.info(f"after adding client_id, client_dict is {client_dict}")
        my_client = WealthManagementClient(**client_dict)
        activity.logger.info(f"The client is {my_client}")
        return my_client

    @staticmethod
    @activity.defn
    async def update_client(client_id: str, field_dict: dict) -> str:
        activity.logger.info(f"update_client. input: {field_dict}")
        client_manager = ClientManager()
        result = client_manager.update_client(client_id, field_dict)
        activity.logger.info(f"The result of updating client: {result}")
        return result


if __name__ == '__main__':
    client_dict = {'first_name': 'Don', 'last_name': 'Doe', 'address': '123 Main Street', 'phone': '999-555-1212', 'email': 'jd@someplace.com', 'marital_status': 'married',  'client_id': '123'}
    print(f"client_dict is {client_dict}")
    client = WealthManagementClient(**client_dict)
    print(f"Client is {client}")
