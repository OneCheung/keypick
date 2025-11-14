"""
Redis caching service for historical data
"""

import json
import logging
from typing import Any, Optional
import redis.asyncio as redis

from api.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Service for Redis caching operations"""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client: Optional[redis.Redis] = None
        self.enabled = bool(self.redis_url)

    async def _get_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client"""
        if not self.enabled:
            return None

        if not self.client:
            try:
                self.client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    encoding="utf-8"
                )
                await self.client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.enabled = False
                return None

        return self.client

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.enabled:
            return None

        try:
            client = await self._get_client()
            if not client:
                return None

            value = await client.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
            return value

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.enabled:
            return False

        try:
            client = await self._get_client()
            if not client:
                return False

            await client.set(key, value, ex=ttl)
            logger.debug(f"Cached key: {key} with TTL: {ttl}")
            return True

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False

        try:
            client = await self._get_client()
            if not client:
                return False

            result = await client.delete(key)
            logger.debug(f"Deleted key: {key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.enabled:
            return 0

        try:
            client = await self._get_client()
            if not client:
                return 0

            # Find all keys matching pattern
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.enabled:
            return False

        try:
            client = await self._get_client()
            if not client:
                return False

            return bool(await client.exists(key))

        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self.enabled:
            return False

        try:
            client = await self._get_client()
            if not client:
                return False

            return bool(await client.expire(key, ttl))

        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key: {key}")
        return None

    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set JSON value in cache"""
        try:
            json_str = json.dumps(value, default=str)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        if not self.enabled:
            return None

        try:
            client = await self._get_client()
            if not client:
                return None

            return await client.incr(key, amount)

        except Exception as e:
            logger.error(f"Redis increment error: {e}")
            return None

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key"""
        if not self.enabled:
            return None

        try:
            client = await self._get_client()
            if not client:
                return None

            ttl = await client.ttl(key)
            return ttl if ttl >= 0 else None

        except Exception as e:
            logger.error(f"Redis get TTL error: {e}")
            return None

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis connection closed")