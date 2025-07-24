import os

from temporalio.converter import DataConverter
from temporalio.contrib.pydantic import pydantic_data_converter, PydanticPayloadConverter

from temporal_supervisor.claim_check_codec import ClaimCheckCodec

# Simple helper class that determines if we need the claim check codec
class DataConverterHelper:
    def __init__(self):
        self.useClaimCheck = str_to_bool(os.getenv("USE_CLAIM_CHECK", "False"))
        self.redisHost = os.getenv("REDIS_HOST", "localhost")
        self.redisPort = os.getenv("REDIS_PORT", "6379")

    # returns the appropriate data converter (with or without the claim check)
    def get_data_converter(self) -> DataConverter:
        # Default to the pydantic data converter
        data_converter = pydantic_data_converter
        if self.useClaimCheck:
            print(f"using claim check codec {self.useClaimCheck}")
            claim_check_codec = ClaimCheckCodec(self.redisHost, self.redisPort)
            data_converter = DataConverter(
                payload_converter_class=PydanticPayloadConverter,
                payload_codec=claim_check_codec
            )

        return data_converter

# Python's bool() function is stupid so we need to write our own
def str_to_bool(s) -> bool:
    s_lower = s.lower()
    if s_lower in ("true", "t", "yes", "y", "1"):
        return True
    elif s_lower in ("false", "f", "no", "n", "0"):
        return False
    else:
        raise ValueError(f"Cannot convert '{s}' to a bool")