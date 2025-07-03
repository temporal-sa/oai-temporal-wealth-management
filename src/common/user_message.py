from pydantic import BaseModel


class ProcessUserMessageInput(BaseModel):
    user_input: str
    chat_length: int
