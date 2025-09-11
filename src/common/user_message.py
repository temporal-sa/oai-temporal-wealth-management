from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

class ProcessUserMessageInput(BaseModel):
    user_input: str

@dataclass
class ChatInteraction:
    user_prompt: str
    text_response: str
    json_response: Optional[str] = None
    agent_trace: Optional[str] = None

    def __str__(self):
        return f"Prompt: {self.user_prompt}, Text: {self.text_response}, JSON: {self.json_response}, Agent: {self.agent_trace}"
