import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from common.redis_config import RedisConfig


class ChaosFlag(str, Enum):
    TOOL_DOWN = "tool_down"
    LLM_DOWN = "llm_down"
    LLM_RATE_LIMITED = "llm_rate_limited"
    CUSTODIAN_REJECTS = "custodian_rejects"
    SLOW_SAGA = "slow_saga"
    WORKFLOW_BUG = "workflow_bug"


@dataclass(frozen=True)
class ChaosFlagInfo:
    flag: ChaosFlag
    label: str
    description: str


# Display metadata for the UI chaos panel, in the order it is shown.
CHAOS_FLAGS: List[ChaosFlagInfo] = [
    ChaosFlagInfo(
        ChaosFlag.TOOL_DOWN,
        "Core banking API down",
        "Investment and beneficiary tools raise a connection error. Temporal retries until you turn this off.",
    ),
    ChaosFlagInfo(
        ChaosFlag.LLM_DOWN,
        "OpenAI API down",
        "Every model call raises a connection error. The agent pauses mid-turn and resumes when you turn this off.",
    ),
    ChaosFlagInfo(
        ChaosFlag.LLM_RATE_LIMITED,
        "OpenAI rate limited (429)",
        "Every model call is throttled. Retries wait for the server's Retry-After delay instead of the normal backoff.",
    ),
    ChaosFlagInfo(
        ChaosFlag.CUSTODIAN_REJECTS,
        "Custodian rejects new accounts",
        "The last account-opening step fails non-retryably, so the saga rolls back the funds transfer and the account.",
    ),
    ChaosFlagInfo(
        ChaosFlag.SLOW_SAGA,
        "Slow account-opening steps",
        "Each account-opening step takes a few extra seconds, so you can watch the saga (or kill the worker mid-way).",
    ),
    ChaosFlagInfo(
        ChaosFlag.WORKFLOW_BUG,
        "Bug in workflow code",
        "New account openings get a welcome-bonus promo code, and the workflow's promo code path has a bug. "
        "It pauses after compliance approval until you fix the code and restart the worker. "
        "Turning this off does not unstick openings that already have the promo code.",
    ),
]

_FLAGS_KEY = "chaos:flags"
_EVENTS_KEY = "chaos:events"
_MAX_EVENTS = 50


class ChaosManager:
    """Stores failure-injection flags, and a log of the failures they caused, in Redis.

    Flags are read at runtime by activities and the model wrapper, so a failure can
    be switched on and off from the UI without restarting the worker.
    """

    def __init__(self, config: RedisConfig = None):
        config = config or RedisConfig()
        self.redis_client = redis.Redis(host=config.hostname, port=config.port, decode_responses=True)

    async def is_enabled(self, flag: ChaosFlag) -> bool:
        return await self.redis_client.hget(_FLAGS_KEY, flag.value) == "1"

    async def set_enabled(self, flag: ChaosFlag, enabled: bool) -> None:
        if enabled:
            await self.redis_client.hset(_FLAGS_KEY, flag.value, "1")
        else:
            await self.redis_client.hdel(_FLAGS_KEY, flag.value)

    async def get_flags(self) -> Dict[str, bool]:
        enabled = await self.redis_client.hgetall(_FLAGS_KEY)
        return {info.flag.value: enabled.get(info.flag.value) == "1" for info in CHAOS_FLAGS}

    async def record_event(
        self, flag: ChaosFlag, source: str, attempt: Optional[int], workflow_id: Optional[str]
    ) -> None:
        event = {
            "timestamp": time.time(),
            "flag": flag.value,
            "source": source,
            "attempt": attempt,
            "workflow_id": workflow_id,
        }
        await self.redis_client.lpush(_EVENTS_KEY, json.dumps(event))
        await self.redis_client.ltrim(_EVENTS_KEY, 0, _MAX_EVENTS - 1)

    async def get_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [json.loads(e) for e in await self.redis_client.lrange(_EVENTS_KEY, 0, limit - 1)]

    async def clear_events(self) -> None:
        await self.redis_client.delete(_EVENTS_KEY)

    async def close(self):
        await self.redis_client.aclose()
