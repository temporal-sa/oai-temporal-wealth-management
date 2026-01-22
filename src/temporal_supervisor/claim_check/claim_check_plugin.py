import os

from temporalio.client import Plugin, ClientConfig
from temporalio.converter import DataConverter

from common.redis_config import RedisConfig
from common.util import str_to_bool
from temporal_supervisor.claim_check.claim_check_codec import ClaimCheckCodec

class ClaimCheckPlugin(Plugin):
    def __init__(self):
        self.useClaimCheck = str_to_bool(os.getenv("USE_CLAIM_CHECK", "False"))

        # Redis configuration
        self.redis_config = RedisConfig()

    def get_data_converter(self, config: ClientConfig) -> DataConverter:
        default_converter_class = config["data_converter"].payload_converter_class
        if self.useClaimCheck:
            print(f"using claim check codec {self.useClaimCheck}")
            claim_check_codec = ClaimCheckCodec(self.redis_config)

            return DataConverter(
                payload_converter_class=default_converter_class,
                payload_codec=claim_check_codec
            )
        else:
            return DataConverter(
                payload_converter_class=default_converter_class
            )

    def init_client_plugin(self, next: Plugin) -> None:
        """Initialize the plugin chain"""
        self.next_plugin = next

    def configure_client(self, config: ClientConfig) -> ClientConfig:
        config["data_converter"] = self.get_data_converter(config)
        return self.next_plugin.configure_client(config)

    async def connect_service_client(self, config):
        """Pass through to next plugin in chain"""
        return await self.next_plugin.connect_service_client(config)
