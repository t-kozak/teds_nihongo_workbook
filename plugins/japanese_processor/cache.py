"""Redis-based caching for LLM responses."""

import hashlib
import logging
from functools import wraps
from typing import Optional

import redis

_log = logging.getLogger(__name__)


class LLMCache:
    """
    Redis-based cache for LLM responses with automatic fallback to no-cache mode.

    The cache uses SHA256 hashing of prompts as keys to store and retrieve
    LLM responses. This significantly reduces costs by avoiding duplicate
    API calls for identical prompts.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        key_prefix: str = "",
        enabled: bool = True,
    ):
        """
        Initialize the LLM cache.

        Args:
            host: Redis host address
            port: Redis port number
            db: Redis database number
            ttl: Time-to-live for cache entries in seconds (default: 30 days)
            key_prefix: Prefix for all cache keys
            enabled: Whether caching is enabled (can be disabled for debugging)
        """
        self.enabled = enabled
        self.key_prefix = key_prefix
        self._client = None
        self._connection_attempted = False

        if self.enabled:
            try:
                self._client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # Test connection
                self._client.ping()
                _log.info(
                    f"[japanese_processor:cache] Connected to Redis at {host}:{port}"
                )
            except Exception as e:
                _log.info(f"Redis connection failed: {e}")
                _log.info(" Running without cache")
                self._client = None
                self.enabled = False

    def _hash_prompt(self, prompt: str) -> str:
        """
        Generate a SHA256 hash of the prompt for use as cache key.

        Args:
            prompt: The prompt string to hash

        Returns:
            Hex digest of the SHA256 hash
        """
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def _make_key(self, prompt: str) -> str:
        """
        Create a full Redis key from a prompt.

        Args:
            prompt: The prompt string

        Returns:
            Full Redis key with prefix and hash
        """
        prompt_hash = self._hash_prompt(prompt)
        return f"{self.key_prefix}:{prompt_hash}"

    def get(self, prompt: str) -> Optional[str]:
        """
        Get cached response for a prompt.

        Args:
            prompt: The prompt string to look up

        Returns:
            Cached response string if found, None otherwise
        """
        if not self.enabled or self._client is None:
            return None

        key = self._make_key(prompt)
        value = self._client.get(key)
        if value is not None and isinstance(value, str):
            _log.info("Cache HIT")
            return value
        else:
            _log.info("Cache MISS")
            return None

    def set(self, prompt: str, response: str) -> bool:
        """
        Store a response in the cache.

        Args:
            prompt: The prompt string (will be hashed for key)
            response: The response string to cache

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or self._client is None:
            return False

        key = self._make_key(prompt)
        self._client.set(key, response)
        _log.info("Cache STORE")
        return True

    def delete(self, prompt: str) -> bool:
        """
        Delete a cached response.

        Args:
            prompt: The prompt string to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or self._client is None:
            return False

        try:
            key = self._make_key(prompt)
            self._client.delete(key)
            return True
        except Exception as e:
            _log.info(f"Cache delete error: {e}")
            return False

    def clear_all(self) -> bool:
        """
        Clear all cache entries with this prefix.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or self._client is None:
            return False

        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = list(self._client.scan_iter(match=pattern))
            if keys:
                self._client.delete(*keys)
                _log.info(
                    f"[japanese_processor:cache] Cleared {len(keys)} cache entries"
                )
            return True
        except Exception as e:
            _log.info(f"Cache clear error: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or self._client is None:
            return {
                "enabled": False,
                "connected": False,
                "entries": 0,
            }

        try:
            # Count keys with our prefix
            pattern = f"{self.key_prefix}*"
            key_count = sum(1 for _ in self._client.scan_iter(match=pattern))

            return {
                "enabled": True,
                "connected": True,
                "entries": key_count,
                "prefix": self.key_prefix,
            }
        except Exception as e:
            _log.info(f"Stats error: {e}")
            return {
                "enabled": True,
                "connected": False,
                "error": str(e),
            }


def cached_llm_call(cache: LLMCache):
    """
    Decorator to cache async LLM function calls.

    Args:
        cache: LLMCache instance to use

    Example:
        @cached_llm_call(my_cache)
        async def process_text(prompt: str) -> str:
            # Expensive LLM call
            return await agent.run_async(prompt)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(prompt: str, *args, **kwargs) -> str:
            # Try to get from cache
            cached_response = cache.get(prompt)
            if cached_response is not None:
                return cached_response

            # Call the actual function
            response = await func(prompt, *args, **kwargs)

            # Store in cache if we got a valid response
            if response:
                cache.set(prompt, response)

            return response

        return wrapper

    return decorator


# Global cache instance
_cache = None


def get_cache(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    enabled: bool = True,
    key_prefix: str = "",
) -> LLMCache:
    """
    Get or create the global cache instance.

    Args:
        host: Redis host address
        port: Redis port number
        db: Redis database number
        ttl: Time-to-live for cache entries in seconds
        enabled: Whether caching is enabled

    Returns:
        LLMCache instance
    """
    global _cache
    if _cache is None:
        _cache = LLMCache(
            host=host, port=port, db=db, enabled=enabled, key_prefix=key_prefix
        )
    return _cache


if __name__ == "__main__":
    import uuid

    cache = get_cache()

    prompt = str(uuid.uuid4())
    in_cache = cache.get(prompt)
    assert in_cache is None
    cache.set(prompt, "some_val")
    assert cache.get(prompt) == "some_val"
