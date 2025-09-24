import json

import redis.asyncio as redis

class DBManager:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)

    # may need to revisit this later
    async def save(self, key: str, value):
        value_as_json = json.dumps(value)
        await self.redis_client.set(key, value_as_json)

    # may need to revisit this later
    async def read(self, key: str) -> any:
        print(f"Getting ready to retrieve the value for key {key}")
        value =  await self.redis_client.get(key)
        print(f"The value read is {value}")
        if value is not None:
            return_value = json.loads(value)
            print(f"The return value after reading Redis and parsing json is {return_value}")
            return return_value
        # TODO: Validate this is okay
        return None

    async def delete(self, key: str):
        print(f"Deleting key {key}")
        await self.redis_client.delete(key)