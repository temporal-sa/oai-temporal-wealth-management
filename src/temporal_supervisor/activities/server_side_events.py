from temporalio import activity
from temporalio.exceptions import ApplicationError
import requests

class ServerSideEvents:
    @staticmethod
    @activity.defn
    async def update_status(endpoint: str, status: str) -> str:
        if endpoint is None or endpoint == "":
            raise ApplicationError("Endpoint is not set. Non-recoverable error", non_retryable=True)

        activity.logger.info(f"Sending updated status {status} to {endpoint}")
        payload = {"status": status}
        response = requests.post(endpoint, json=payload)
        return_value = "Status Updated!"
        if response.status_code != 200:
            activity.logger.error(f"POST request failed with status code {response.status_code}")
            return_value = "Update failed with status code {response.status_code}"

        return return_value
