from dataclasses import dataclass

@dataclass
class StatusUpdate:
    status: str

    def __str__(self):
        return f"Status: {self.status}"
