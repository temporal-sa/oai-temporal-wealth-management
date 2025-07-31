from pydantic import BaseModel

class ClientContext(BaseModel):
    client_id: str | None = None