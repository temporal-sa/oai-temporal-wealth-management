from pydantic import BaseModel

class ClientContext(BaseModel):
    client_id: str | None = None

class UpdateAccountOpeningStateInput(BaseModel):
    account_name: str
    state: str
