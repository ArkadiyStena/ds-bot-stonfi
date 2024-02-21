import redis.asyncio as redis
from pytonconnect.storage import IStorage, DefaultStorage

storage = {}

class SimpleStorage(IStorage):
    def __init__(self, user_id: int):
        self.user_id = user_id

    def _get_key(self, key: str):
        return str(self.user_id) + key

    async def set_item(self, key: str, value: str):
        storage[self._get_key(key)] = value

    async def get_item(self, key: str, default_value: str = None):
        return storage.get(self._get_key(key), default_value)

    async def remove_item(self, key: str):
        storage.pop(self._get_key(key))