"""SteamGGames — camada de cache em disco com TTL."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from typing import Any

from steamggames.config import CACHE_DIR, CACHE_TTL_SEARCH


def _ensure_cache_dir() -> None:
    """Cria o diretório de cache se não existir."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key: str) -> str:
    """Retorna o caminho completo do arquivo de cache para uma chave.

    Se a chave sanitizada exceder 200 caracteres (limite de filename
    é ~255 na maioria dos filesystems), usa hash SHA-256 como nome.
    """
    safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    # Limita o nome do arquivo para não exceder o limite do filesystem
    if len(safe_key) > 200:
        hash_key = hashlib.sha256(key.encode()).hexdigest()[:40]
        safe_key = f"long_{hash_key}"
    return os.path.join(CACHE_DIR, f"{safe_key}.json")


def get(key: str, ttl: int = CACHE_TTL_SEARCH) -> Any | None:
    """Lê dados do cache se existir e não estiver expirado.

    Args:
        key: Chave de cache (ex: "search:elden+ring:1")
        ttl: Tempo de vida em segundos (default: 4h para busca)

    Returns:
        Dados desserializados ou None se cache miss/expirado.
    """
    path = _cache_path(key)
    if not os.path.exists(path):
        return None

    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)

        timestamp = entry.get("timestamp", 0)
        if time.time() - timestamp > ttl:
            # Cache expirado — remove o arquivo
            with contextlib.suppress(OSError):
                os.remove(path)
            return None

        return entry.get("data")

    except (json.JSONDecodeError, OSError, KeyError):
        # Cache corrompido — remove
        with contextlib.suppress(OSError):
            os.remove(path)
        return None


def set(key: str, data: Any) -> None:
    """Salva dados no cache com timestamp atual.

    Args:
        key: Chave de cache
        data: Dados serializáveis (listas, dicts, etc.)
    """
    _ensure_cache_dir()
    path = _cache_path(key)

    entry = {
        "timestamp": time.time(),
        "data": data,
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # Falha silenciosa — cache é best-effort


def invalidate(key: str) -> None:
    """Remove uma entrada específica do cache."""
    path = _cache_path(key)
    with contextlib.suppress(OSError):
        os.remove(path)


def invalidate_all() -> None:
    """Remove todo o cache do disco."""
    if not os.path.exists(CACHE_DIR):
        return
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            with contextlib.suppress(OSError):
                os.remove(os.path.join(CACHE_DIR, filename))


def cache_key_search(query: str, page: int) -> str:
    """Gera chave de cache para resultados de busca."""
    return f"search:{query.lower().strip()}:{page}"


def cache_key_game(url: str) -> str:
    """Gera chave de cache para página de jogo."""
    # Usa o path da URL como parte da chave
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return f"game:{parsed.path.strip('/')}"
