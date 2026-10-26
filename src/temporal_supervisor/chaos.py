"""Failure injection for the demo, driven by the flags in the UI chaos panel.

Called from inside activities (including the model activity), never from workflow
code: it reads Redis, which is non-deterministic I/O.
"""

import asyncio
import logging

from temporalio import activity

from common.chaos_manager import ChaosFlag, ChaosManager

logger = logging.getLogger(__name__)

SLOW_SAGA_DELAY_SECONDS = 4


async def is_enabled(flag: ChaosFlag) -> bool:
    # Fail open: if Redis is unreachable, chaos is off rather than breaking the demo.
    manager = ChaosManager()
    try:
        return await manager.is_enabled(flag)
    except Exception as e:
        logger.warning(f"Could not read chaos flag {flag.value}: {e}")
        return False
    finally:
        await manager.close()


async def record_event(flag: ChaosFlag) -> None:
    """Log an injected failure for the chaos panel."""
    info = activity.info()
    manager = ChaosManager()
    try:
        await manager.record_event(flag, info.activity_type, info.attempt, info.workflow_id)
    except Exception as e:
        logger.warning(f"Could not record chaos event: {e}")
    finally:
        await manager.close()


async def inject_failure(flag: ChaosFlag, error: BaseException) -> None:
    """Raise ``error`` if ``flag`` is on, logging the hit for the chaos panel."""
    if not await is_enabled(flag):
        return
    await record_event(flag)
    activity.logger.warning(f"Chaos [{flag.value}] attempt {activity.info().attempt}: {error}")
    raise error


async def core_banking_api() -> None:
    """Fail the way the core banking API would while it is down."""
    await inject_failure(ChaosFlag.TOOL_DOWN, ConnectionError("Core banking API unavailable"))


async def maybe_slow_down() -> None:
    """Simulate a slow downstream system when the slow-saga flag is on."""
    if await is_enabled(ChaosFlag.SLOW_SAGA):
        await asyncio.sleep(SLOW_SAGA_DELAY_SECONDS)
