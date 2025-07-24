from importlib.metadata import metadata

import uuid
import redis.asyncio as redis
from typing import Iterable, List

from temporalio.api.common.v1 import Payload
from temporalio.converter import PayloadCodec

#
# Substitutes the payload for a GUID
# and stores the original payload in Redis
#
class ClaimCheckCodec(PayloadCodec):

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)

    #
    # TODO: Figure out when/how to close the redis_client
    #       Can't be done in a __del__ as it aClose() needs to be awaited
    #
    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        out: list[Payload] = []
        for p in payloads:
            encoded = await self.encode_payload(p)
            out.append(encoded)

        return out

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        out: List[Payload] = []
        for p in payloads:
            if p.metadata.get("temporal.io/claim-check-codec", b"").decode() != "v1":
                out.append(p)
                continue

            redis_id = p.data.decode("utf-8")
            value = await self.redis_client.get(redis_id)
            new_payload = Payload.FromString(value)
            out.append(new_payload)
        return out

    async def encode_payload(self, payload: Payload) -> Payload:
        id = str(uuid.uuid4())
        value = payload.SerializeToString()
        await self.redis_client.set(id, value)
        out = Payload(
            metadata= {
                "encoding": b"claim-checked",
                "temporal.io/claim-check-codec": b"v1",
            },
            data=id.encode("utf-8"),
        )
        return out
