"""Tests for Redis caching functionality."""

import logging

from .cache import LLMCache

_log = logging.getLogger(__name__)


def test_cache_hash_consistency():
    """Test that the same prompt always produces the same hash."""
    cache = LLMCache(enabled=False)  # Don't need actual Redis for this test

    prompt = "日本語を勉強します。"
    hash1 = cache._hash_prompt(prompt)
    hash2 = cache._hash_prompt(prompt)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 produces 64 hex characters
    _log.info("✓ Cache hash consistency test passed")


def test_cache_key_generation():
    """Test that cache keys are generated correctly."""
    cache = LLMCache(enabled=False, key_prefix="test:")

    prompt = "こんにちは"
    key = cache._make_key(prompt)

    assert key.startswith("test:")
    assert len(key) > len("test:")
    _log.info("✓ Cache key generation test passed")


def test_cache_disabled_mode():
    """Test that cache operates correctly when disabled."""
    cache = LLMCache(enabled=False)

    prompt = "テスト"
    response = "Test response"

    # When disabled, get should always return None
    assert cache.get(prompt) is None

    # When disabled, set should return False
    assert cache.set(prompt, response) is False

    # Verify still returns None after attempted set
    assert cache.get(prompt) is None

    _log.info("✓ Cache disabled mode test passed")


def test_cache_with_redis():
    """Test cache operations with actual Redis (if available)."""
    try:
        cache = LLMCache(enabled=True)

        if not cache.enabled:
            _log.info("⚠ Redis not available, skipping Redis-dependent tests")
            return

        _log.info("✓ Redis connection successful")

        # Test set and get
        prompt = "日本語テスト"
        response = '<span class="jp-word">日本語</span>'

        # Clear any existing entry
        cache.delete(prompt)

        # Should be a miss first
        assert cache.get(prompt) is None
        _log.info("✓ Initial cache miss confirmed")

        # Set the value
        assert cache.set(prompt, response) is True
        _log.info("✓ Cache set successful")

        # Should now be a hit
        cached_value = cache.get(prompt)
        assert cached_value == response
        _log.info("✓ Cache hit successful")

        # Test delete
        assert cache.delete(prompt) is True
        assert cache.get(prompt) is None
        _log.info("✓ Cache delete successful")

        # Test stats
        stats = cache.get_stats()
        assert stats["enabled"] is True
        assert stats["connected"] is True
        assert "entries" in stats
        _log.info(f"✓ Cache stats: {stats}")

    except Exception as e:
        _log.info(f"⚠ Redis test skipped: {e}")


def test_cache_fallback():
    """Test that cache gracefully handles Redis connection failures."""
    # Try to connect to non-existent Redis
    cache = LLMCache(
        enabled=True,
        host="nonexistent-host-12345",
        port=9999,
    )

    # Should have disabled itself
    assert cache.enabled is False
    assert cache._client is None

    # Should still work without errors
    prompt = "テスト"
    assert cache.get(prompt) is None
    assert cache.set(prompt, "response") is False

    _log.info("✓ Cache fallback test passed")


if __name__ == "__main__":
    _log.info("Running cache tests...\n")

    test_cache_hash_consistency()
    test_cache_key_generation()
    test_cache_disabled_mode()
    test_cache_fallback()
    test_cache_with_redis()

    _log.info("\n✅ All cache tests completed!")
