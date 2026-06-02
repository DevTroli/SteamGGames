"""Testes de segurança — SSRF, injeção, proteções."""

from __future__ import annotations

import pytest

from steamggames.config import ALLOWED_DOMAINS
from steamggames.utils import extract_host, is_download_link, is_steamgg_game_url


class TestSSRFProtection:
    """Proteção contra SSRF — domínios permitidos para abrir no navegador."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://steamgg.net/elden-ring-free-download",
            "https://www.steamgg.net/game",
            "http://steamgg.net/page",
        ],
    )
    def test_allowed_domains(self, url: str) -> None:
        host = extract_host(url)
        assert any(domain in host for domain in ALLOWED_DOMAINS)

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.com/steal-data",
            "https://internal.corp.local/admin",
            "https://169.254.169.254/metadata",  # AWS metadata
            "https://127.0.0.1:8080/admin",
            "file:///etc/passwd",
            "ftp://internal.server/data",
        ],
    )
    def test_blocked_domains(self, url: str) -> None:
        host = extract_host(url)
        assert not any(domain in host for domain in ALLOWED_DOMAINS)


class TestDownloadHostValidation:
    """Apenas hosts conhecidos são considerados links de download."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://datanodes.to/abc",
            "https://rootz.so/abc",
            "https://vikingfile.com/abc",
            "https://akirabox.com/abc",
            "https://buzzheavier.com/abc",
        ],
    )
    def test_known_hosts_pass(self, url: str) -> None:
        assert is_download_link(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://malware.evil.com/payload",
            "https://phishing-site.com/download",
            "https://localhost:4444/hack",
        ],
    )
    def test_unknown_hosts_blocked(self, url: str) -> None:
        assert is_download_link(url) is False


class TestURLValidation:
    """Validação de URLs do steamgg.net."""

    def test_game_url_must_have_free_download(self) -> None:
        """URLs de jogo devem conter '-free-download' no path."""
        assert is_steamgg_game_url("https://steamgg.net/elden-ring-free-download") is True
        assert is_steamgg_game_url("https://steamgg.net/?s=evil<script>") is False

    def test_javascript_url_blocked(self) -> None:
        assert is_steamgg_game_url("javascript:alert(1)") is False

    def test_data_url_blocked(self) -> None:
        assert is_steamgg_game_url("data:text/html,<h1>evil</h1>") is False

    def test_empty_url(self) -> None:
        assert is_steamgg_game_url("") is False
