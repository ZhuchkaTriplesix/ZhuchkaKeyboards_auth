"""Redis client with convenient methods for cache operations."""

import json
from typing import Any

import redis.asyncio as redis

from src import config

r: redis.Redis = redis.Redis(decode_responses=True, **config.redis_cfg.dict())


class RedisController:
    """Redis controller with common cache operations."""

    # Default TTL (Time To Live) in seconds
    DEFAULT_TTL = 3600  # 1 hour

    @classmethod
    async def get(cls, key: str) -> str | None:
        """
        Get value from Redis by key.

        Args:
            key: Redis key

        Returns:
            Value if exists, None otherwise
        """
        return await r.get(key)

    @classmethod
    async def get_json(cls, key: str) -> Any | None:
        """
        Get JSON value from Redis by key.

        Args:
            key: Redis key

        Returns:
            Parsed JSON value if exists, None otherwise
        """
        value = await r.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    @classmethod
    async def set(cls, key: str, value: str, ttl: int | None = None) -> bool:
        """
        Set value in Redis with optional TTL.

        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        if ttl is None:
            ttl = cls.DEFAULT_TTL
        return await r.set(key, value, ex=ttl)

    @classmethod
    async def set_json(cls, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set JSON value in Redis with optional TTL.

        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        json_value = json.dumps(value)
        return await cls.set(key, json_value, ttl)

    @classmethod
    async def delete(cls, key: str) -> int:
        """
        Delete key from Redis.

        Args:
            key: Redis key to delete

        Returns:
            Number of keys deleted
        """
        return await r.delete(key)

    @classmethod
    async def delete_many(cls, *keys: str) -> int:
        """
        Delete multiple keys from Redis.

        Args:
            keys: Redis keys to delete

        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        return await r.delete(*keys)

    @classmethod
    async def update(cls, key: str, value: str, ttl: int | None = None) -> bool:
        """
        Update value in Redis. Alias for set().

        Args:
            key: Redis key
            value: New value
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        return await cls.set(key, value, ttl)

    @classmethod
    async def update_json(cls, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Update JSON value in Redis. Alias for set_json().

        Args:
            key: Redis key
            value: New value (will be JSON serialized)
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful
        """
        return await cls.set_json(key, value, ttl)

    @classmethod
    async def exists(cls, key: str) -> bool:
        """
        Check if key exists in Redis.

        Args:
            key: Redis key

        Returns:
            True if key exists
        """
        return await r.exists(key) > 0

    @classmethod
    async def expire(cls, key: str, ttl: int) -> bool:
        """
        Set expiration time for existing key.

        Args:
            key: Redis key
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        return await r.expire(key, ttl)

    @classmethod
    async def ttl(cls, key: str) -> int:
        """
        Get remaining TTL for key.

        Args:
            key: Redis key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        return await r.ttl(key)

    # Legacy methods for backward compatibility
