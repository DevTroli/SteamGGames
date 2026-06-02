"""Testes para steamggames.config — validação de constantes e configuração."""

from __future__ import annotations

import os

from steamggames.config import (
    BACKOFF_MAX_RETRIES,
    BACKOFF_STATUS_CODES,
    BASE_URL,
    CACHE_TTL_GAME,
    CACHE_TTL_SEARCH,
    DELAY_MAX,
    DELAY_MIN,
    DOWNLOAD_HOSTS,
    REQUEST_TIMEOUT,
    SEARCH_URL,
    SEMAPHORE_LIMIT,
    USER_AGENTS,
)


class TestConfigConstants:
    """Valida que as constantes têm valores sensatos."""

    def test_base_url(self) -> None:
        assert BASE_URL == "https://steamgg.net"

    def test_search_url_format(self) -> None:
        """SEARCH_URL deve conter placeholders {query} e {page}."""
        assert "{query}" in SEARCH_URL
        assert "{page}" in SEARCH_URL
        # Deve formatar sem erros
        url = SEARCH_URL.format(query="test", page=1)
        assert url.startswith(BASE_URL)

    def test_semaphore_sensible(self) -> None:
        assert 1 <= SEMAPHORE_LIMIT <= 50

    def test_delay_range(self) -> None:
        assert 0 < DELAY_MIN < DELAY_MAX
        assert DELAY_MAX < 30  # não mais que 30s

    def test_backoff_codes(self) -> None:
        assert 403 in BACKOFF_STATUS_CODES
        assert 429 in BACKOFF_STATUS_CODES
        assert 503 in BACKOFF_STATUS_CODES

    def test_backoff_retries(self) -> None:
        assert 1 <= BACKOFF_MAX_RETRIES <= 10

    def test_cache_ttls(self) -> None:
        assert CACHE_TTL_SEARCH > 0
        assert CACHE_TTL_GAME > CACHE_TTL_SEARCH
        # 4h = 14400s, 12h = 43200s
        assert CACHE_TTL_SEARCH == 4 * 3600
        assert CACHE_TTL_GAME == 12 * 3600

    def test_user_agents_not_empty(self) -> None:
        assert len(USER_AGENTS) >= 3
        for ua in USER_AGENTS:
            assert "Mozilla" in ua

    def test_download_hosts(self) -> None:
        assert "datanodes.to" in DOWNLOAD_HOSTS
        assert "rootz.so" in DOWNLOAD_HOSTS
        assert "vikingfile.com" in DOWNLOAD_HOSTS
        assert "akirabox.com" in DOWNLOAD_HOSTS
        assert "buzzheavier.com" in DOWNLOAD_HOSTS

    def test_request_timeout(self) -> None:
        assert 5 <= REQUEST_TIMEOUT <= 120
