from pydantic import BaseModel

class ClientContext(BaseModel):
    client_id: str | None = None

class UpdateAccountOpeningStateInput(BaseModel):
    account_name: str
    state: str
    # The open-account workflow that reported the state. Optional so that
    # senders that don't set it keep working.
    workflow_id: str | None = None
