"""Testes unitários para steamggames.utils — edge cases de extração e validação."""

from __future__ import annotations

import pytest

from steamggames.utils import (
    extract_host,
    extract_version,
    is_download_link,
    is_steamgg_game_url,
    sanitize_query,
    truncate,
)


# ── extract_version ─────────────────────────────────────────────────────────

class TestExtractVersion:
    """Edge cases para extração de versão do título."""

    # Padrões que DEVEM funcionar
    @pytest.mark.parametrize(
        "title, expected",
        [
            # Versão simples
            ("Elden Ring v1.2.3", "v1.2.3"),
            ("Game V2.0", "v2.0"),
            # Versão com patch
            ("Cyberpunk v1.2.3.4", "v1.2.3.4"),
            # Build number
            ("Hades Build 1234567", "Build 1234567"),
            ("hades build 99", "Build 99"),
            # Update
            ("No Man's Sky Update 4.50", "Update 4.50"),
            ("Game Update 3.1.2", "Update 3.1.2"),
            # Versão com sufixo extra no título
            ("Game v1.0 + DLC", "v1.0"),
            ("Game v2.3 + All DLCs", "v2.3"),
            # Versão entre parênteses
            ("Some Game (v1.5)", "v1.5"),
            # Build com hífen (padrão steamgg.net: [Build-20567064+ALL DLCs])
            ("Game [Build-20567064+ALL DLCs]", "Build 20567064"),
            ("Game Build-99", "Build 99"),
            # Versão com V maiúsculo entre parênteses
            ("Game (V1.0.0.2)", "v1.0.0.2"),
        ],
    )
    def test_valid_patterns(self, title: str, expected: str) -> None:
        assert extract_version(title) == expected

    # Padrões que NÃO devem extrair nada
    @pytest.mark.parametrize(
        "title",
        [
            "Elden Ring",
            "No Version Here",
            "",                       # string vazia
            "   ",                    # só espaços
            "v without number",       # 'v' sem número
            "version 1.0",            # 'version' não é 'v'
            "V not a number",         # 'V' sem dígitos
        ],
    )
    def test_no_version(self, title: str) -> None:
        assert extract_version(title) == "-"

    # Ambíguos — primeiro match vence
    def test_multiple_versions(self) -> None:
        # Se tem v1.0 e v2.0, pega o primeiro
        result = extract_version("Game v1.0 and v2.0")
        assert result == "v1.0"


# ── extract_host ─────────────────────────────────────────────────────────────

class TestExtractHost:
    """Edge cases para extração de host."""

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://datanodes.to/abc", "datanodes.to"),
            ("https://steamgg.net/elden-ring-free-download", "steamgg.net"),
            ("http://example.com:8080/path", "example.com"),
            ("", ""),
        ],
    )
    def test_valid_urls(self, url: str, expected: str) -> None:
        assert extract_host(url) == expected

    def test_malformed_url(self) -> None:
        # URL totalmente malformada
        result = extract_host("not-a-url-at-all")
        assert result == ""


# ── is_steamgg_game_url ──────────────────────────────────────────────────────

class TestIsSteamggGameUrl:
    """Edge cases para validação de URL de jogo."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://steamgg.net/elden-ring-free-download",
            "https://www.steamgg.net/game-free-download",
            "http://steamgg.net/something-free-download",
        ],
    )
    def test_valid_game_urls(self, url: str) -> None:
        assert is_steamgg_game_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://steamgg.net/",                      # sem -free-download
            "https://steamgg.net/?s=elden+ring",         # URL de busca
            "https://evil.com/elden-ring-free-download", # host errado
            "",                                          # vazio
            "not-a-url",                                 # malformada
        ],
    )
    def test_invalid_game_urls(self, url: str) -> None:
        assert is_steamgg_game_url(url) is False


# ── is_download_link ─────────────────────────────────────────────────────────

class TestIsDownloadLink:
    """Edge cases para validação de links de download."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://datanodes.to/abc123",
            "https://rootz.so/file/xyz",
            "https://vikingfile.com/dl/123",
            "https://akirabox.com/get/abc",
            "https://buzzheavier.com/file",
        ],
    )
    def test_known_hosts(self, url: str) -> None:
        assert is_download_link(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://google.com/file",
            "https://steamgg.net/page",
            "",
            "https://unknown-host.com/file",
        ],
    )
    def test_unknown_hosts(self, url: str) -> None:
        assert is_download_link(url) is False


# ── sanitize_query ───────────────────────────────────────────────────────────

class TestSanitizeQuery:
    """Edge cases para sanitização de query."""

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("Elden Ring", "Elden+Ring"),
            ("  extra  spaces  ", "extra+spaces"),
            ("single", "single"),
            ("", ""),
        ],
    )
    def test_sanitization(self, query: str, expected: str) -> None:
        assert sanitize_query(query) == expected


# ── truncate ─────────────────────────────────────────────────────────────────

class TestTruncate:
    """Edge cases para truncagem de texto."""

    def test_short_text(self) -> None:
        assert truncate("hello", 80) == "hello"

    def test_exact_length(self) -> None:
        assert truncate("a" * 80, 80) == "a" * 80

    def test_over_length(self) -> None:
        result = truncate("a" * 100, 80)
        assert len(result) == 80
        assert result.endswith("...")

    def test_zero_max(self) -> None:
        # max_len < 3 — não deve crashar
        result = truncate("hello", 2)
        assert isinstance(result, str)
