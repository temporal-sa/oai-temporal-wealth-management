from pydantic import BaseModel

class AccountContext(BaseModel):
    account_id: str | None = None