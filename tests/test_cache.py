"""Testes unitários para steamggames.cache — TTL, corrupção, edge cases."""

from __future__ import annotations

import json
import os
import time
import tempfile

import pytest

from steamggames import cache


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _tmp_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.Path) -> None:
    """Redireciona CACHE_DIR para tmp_path para cada teste."""
    monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path))


# ── Cache básico ─────────────────────────────────────────────────────────────

class TestCacheBasic:
    """Set/get/invalidate básicos."""

    def test_set_and_get(self) -> None:
        cache.set("test:key", {"hello": "world"})
        result = cache.get("test:key")
        assert result == {"hello": "world"}

    def test_cache_miss(self) -> None:
        result = cache.get("nonexistent:key")
        assert result is None

    def test_invalidate(self) -> None:
        cache.set("test:del", "data")
        cache.invalidate("test:del")
        assert cache.get("test:del") is None

    def test_invalidate_nonexistent(self) -> None:
        # Não deve crashar
        cache.invalidate("no:such:key")

    def test_invalidate_all(self) -> None:
        cache.set("a", "1")
        cache.set("b", "2")
        cache.invalidate_all()
        assert cache.get("a") is None
        assert cache.get("b") is None


# ── TTL ──────────────────────────────────────────────────────────────────────

class TestCacheTTL:
    """Expiração por TTL."""

    def test_ttl_not_expired(self) -> None:
        cache.set("ttl:ok", "data")
        # TTL grande = não expirado
        assert cache.get("ttl:ok", ttl=3600) == "data"

    def test_ttl_expired(self) -> None:
        # Salva com timestamp no passado
        path = cache._cache_path("ttl:old")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"timestamp": time.time() - 100, "data": "old"}, f)
        # TTL de 1 segundo = expirado
        assert cache.get("ttl:old", ttl=1) is None


# ── Corrupção ────────────────────────────────────────────────────────────────

class TestCacheCorruption:
    """Arquivos de cache corrompidos não devem crashar."""

    def test_invalid_json(self, tmp_path: pytest.Path) -> None:
        path = cache._cache_path("corrupt:json")
        with open(path, "w") as f:
            f.write("{invalid json!!!")
        result = cache.get("corrupt:json")
        assert result is None

    def test_missing_timestamp_key(self, tmp_path: pytest.Path) -> None:
        path = cache._cache_path("corrupt:keys")
        with open(path, "w") as f:
            json.dump({"data": "no timestamp"}, f)
        # Sem timestamp = timestamp 0 = expirado
        result = cache.get("corrupt:keys", ttl=3600)
        # Pode retornar None (expirado) ou o data — depende da lógica
        # Timestamp 0 → time.time() - 0 > ttl → expirado
        assert result is None

    def test_empty_file(self, tmp_path: pytest.Path) -> None:
        path = cache._cache_path("corrupt:empty")
        with open(path, "w") as f:
            f.write("")
        result = cache.get("corrupt:empty")
        assert result is None


# ── Chave sanitização ────────────────────────────────────────────────────────

class TestCacheKeySanitization:
    """Chaves com caracteres especiais não devem crashar."""

    def test_special_chars(self) -> None:
        # Chave com /, :, ?, etc.
        cache.set("search:Elden Ring:1", "data")
        assert cache.get("search:Elden Ring:1") == "data"

    def test_unicode_key(self) -> None:
        cache.set("busca:jörgen", "data")
        assert cache.get("busca:jörgen") == "data"

    def test_very_long_key(self) -> None:
        long_key = "a" * 500
        cache.set(long_key, "data")
        assert cache.get(long_key) == "data"


# ── Tipos de dados ───────────────────────────────────────────────────────────

class TestCacheDataTypes:
    """Diferentes tipos de dados serializáveis."""

    @pytest.mark.parametrize(
        "data",
        [
            "string",
            42,
            3.14,
            True,
            None,
            ["list", "of", "items"],
            {"dict": "value", "nested": {"a": 1}},
        ],
    )
    def test_various_types(self, data: object) -> None:
        cache.set("type:test", data)
        assert cache.get("type:test") == data


# ── Cache key helpers ────────────────────────────────────────────────────────

class TestCacheKeyHelpers:
    """Funções geradoras de chave de cache."""

    def test_cache_key_search(self) -> None:
        key = cache.cache_key_search("Elden Ring", 1)
        assert "elden ring" in key
        assert "1" in key

    def test_cache_key_game(self) -> None:
        key = cache.cache_key_game("https://steamgg.net/elden-ring-free-download")
        assert "elden-ring-free-download" in key
