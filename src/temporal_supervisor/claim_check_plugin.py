import os

from temporalio.client import Plugin, ClientConfig
from temporalio.service import TLSConfig
from temporalio.converter import DataConverter
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from typing import Optional
from temporalio.contrib.openai_agents._invoke_model_activity import ModelActivity
from temporalio.contrib.openai_agents._model_parameters import ModelActivityParameters

from temporal_supervisor.claim_check_codec import ClaimCheckCodec

class ClaimCheckPlugin(Plugin):
    def __init__(self):
        self.useClaimCheck = str_to_bool(os.getenv("USE_CLAIM_CHECK", "False"))
        self.redisHost = os.getenv("REDIS_HOST", "localhost")
        self.redisPort = int(os.getenv("REDIS_PORT", "6379"))

    def get_data_converter(self, config: ClientConfig) -> DataConverter:
        default_converter_class = config["data_converter"].payload_converter_class
        if self.useClaimCheck:
            print(f"using claim check codec {self.useClaimCheck}")
            claim_check_codec = ClaimCheckCodec(self.redisHost, self.redisPort)

            return DataConverter(
                payload_converter_class=default_converter_class,
                payload_codec=claim_check_codec
            )
        else:
            return DataConverter(
                payload_converter_class=default_converter_class
            )

    def configure_client(self, config: ClientConfig) -> ClientConfig:
        config["data_converter"] = self.get_data_converter(config)
        return super().configure_client(config)

# Python's bool() function is stupid so we need to write our own
def str_to_bool(s) -> bool:
    s_lower = s.lower()
    if s_lower in ("true", "t", "yes", "y", "1"):
        return True
    elif s_lower in ("false", "f", "no", "n", "0"):
        return False
    else:
        raise ValueError(f"Cannot convert '{s}' to a bool")