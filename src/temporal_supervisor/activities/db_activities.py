import json
import os
import redis.asyncio as redis

from temporalio import activity

from common.db_manager import DBManager


class DBActivities:

    # may need to revisit this later
    @staticmethod
    @activity.defn
    async def save_conversation(key: str, value):
        activity.logger.info(f"Saving conversation {key}, {value}")
        await DBManager().save(key, value)

    # may need to revisit this later
    @staticmethod
    @activity.defn
    async def read_conversation(key: str) -> any:
        activity.logger.info(f"Reading conversation {key}")
        value = await DBManager().read(key)
        activity.logger.info(f"Read conversation {key} got {value}")
        return value

    @staticmethod
    @activity.defn
    async def delete_conversation(key: str):
        activity.logger.info(f"Deleting conversation {key}")
        await DBManager().delete(key)
        activity.logger.info(f"Deleted conversation {key}")