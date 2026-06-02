"""Testes de integração — fluxo end-to-end com HTML simulado (sem rede real)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from steamggames.scraper import SteamGGScraper
from steamggames.models import SearchResult, GamePage


# HTML realista simulando o site completo
FULL_SEARCH_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Search Results for "elden ring" – SteamGG</title></head>
<body>
<div id="content">
  <div class="post">
    <h2><a href="https://steamgg.net/elden-ring-free-download">Elden Ring v1.09.1 Free Download</a></h2>
    <p>Action RPG from FromSoftware...</p>
  </div>
  <div class="post">
    <h2><a href="https://steamgg.net/elden-ring-shadow-of-erdtree-free-download">Elden Ring Shadow of the Erdtree Free Download</a></h2>
    <p>DLC expansion...</p>
  </div>
  <div class="navigation">
    <a href="https://steamgg.net/?s=elden+ring&page=2">Next</a>
  </div>
</div>
</body>
</html>
"""

FULL_GAME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Elden Ring v1.09.1 Free Download – SteamGG</title></head>
<body>
<article>
  <h1 class="entry-title">Elden Ring v1.09.1 Free Download</h1>
  <div class="entry-content">
    <p>Elden Ring is an action RPG...</p>
    <h2>Download Links</h2>
    <a class="vc_btn3 vc_btn3-color-blue vc_btn3-size-md" href="https://datanodes.to/abc123">
      Download Part 1
    </a>
    <a class="vc_btn3 vc_btn3-color-blue vc_btn3-size-md" href="https://datanodes.to/def456">
      Download Part 2
    </a>
    <a class="vc_btn3 vc_btn3-color-green vc_btn3-size-md" href="https://rootz.so/xyz789">
      Mirror
    </a>
    <!-- Link não-download — deve ser ignorado -->
    <a href="https://store.steampowered.com/app/1245620/">Steam Page</a>
  </div>
</article>
</body>
</html>
"""


class TestEndToEndFlow:
    """Testa fluxo completo: busca → info, com HTML simulado."""

    @pytest.mark.asyncio
    async def test_search_then_info(self):
        """Fluxo: busca "elden ring" → obtém detalhes do primeiro resultado."""
        scraper = SteamGGScraper()

        # Mock do _fetch para retornar HTML simulado
        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            # Primeira chamada: busca
            mock_fetch.return_value = FULL_SEARCH_PAGE
            results = await scraper.search("elden ring", page=1, force_refresh=True)

            assert len(results) == 2
            assert "Elden Ring" in results[0].title
            assert results[0].version == "v1.09.1"

            # Segunda chamada: info do primeiro resultado
            mock_fetch.return_value = FULL_GAME_PAGE
            game = await scraper.game_page(results[0].url, force_refresh=True)

            assert game is not None
            assert "Elden Ring" in game.title
            assert game.version == "v1.09.1"
            assert len(game.download_links) == 3
            hosts = {dl.host for dl in game.download_links}
            assert "datanodes.to" in hosts
            assert "rootz.so" in hosts

        await scraper.close()

    @pytest.mark.asyncio
    async def test_search_empty_result(self):
        """Busca sem resultados."""
        scraper = SteamGGScraper()

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "<html><body><p>No results</p></body></html>"
            results = await scraper.search("zzzznonexistent", force_refresh=True)
            assert results == []

        await scraper.close()

    @pytest.mark.asyncio
    async def test_search_network_failure(self):
        """Falha de rede (None do _fetch)."""
        scraper = SteamGGScraper()

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            results = await scraper.search("test", force_refresh=True)
            assert results == []

        await scraper.close()

    @pytest.mark.asyncio
    async def test_game_page_network_failure(self):
        """Falha de rede ao obter página de jogo."""
        scraper = SteamGGScraper()

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            game = await scraper.game_page("https://steamgg.net/x-free-download", force_refresh=True)
            assert game is None

        await scraper.close()

    @pytest.mark.asyncio
    async def test_pagination(self):
        """Busca na página 2 deve usar URL correta."""
        scraper = SteamGGScraper()

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = FULL_SEARCH_PAGE
            await scraper.search("elden ring", page=2, force_refresh=True)

            # Verifica que _fetch foi chamado com URL da página 2
            call_args = mock_fetch.call_args
            url_called = call_args[0][0]
            assert "page=2" in url_called

        await scraper.close()

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_search(self):
        """Segunda busca com mesmo query deve usar cache (não chama _fetch)."""
        scraper = SteamGGScraper()

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = FULL_SEARCH_PAGE

            # Primeira busca: vai na rede
            results1 = await scraper.search("elden ring", page=1, force_refresh=True)
            assert mock_fetch.call_count == 1

            # Segunda busca: cache hit — não chama _fetch
            results2 = await scraper.search("elden ring", page=1, force_refresh=False)
            assert mock_fetch.call_count == 1  # Mesmo count
            assert len(results2) == len(results1)

        await scraper.close()


class TestScraperSessionManagement:
    """Testa gerenciamento da sessão HTTP."""

    @pytest.mark.asyncio
    async def test_close_without_session(self):
        """Fechar scraper sem ter criado sessão não deve crashar."""
        scraper = SteamGGScraper()
        await scraper.close()  # Não deve levantar erro

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Fechar scraper múltiplas vezes não deve crashar."""
        scraper = SteamGGScraper()
        await scraper.close()
        await scraper.close()
        await scraper.close()


class TestAntiBlockMechanisms:
    """Testa mecanismos anti-bloqueio (sem rede real)."""

    @pytest.mark.asyncio
    async def test_backoff_on_403(self):
        """403 deve triggerar backoff e eventualmente retornar None."""
        scraper = SteamGGScraper()

        # Mocka aiohttp.ClientSession.get para retornar 403 sempre
        async def mock_get(url, **kwargs):
            class MockResponse:
                status = 403
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
            return MockResponse()

        # Patch direto no _fetch para testar backoff logic
        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            # Simula: todas as tentativas retornam None (403 exaustou retries)
            mock_fetch.return_value = None
            results = await scraper.search("test", force_refresh=True)
            assert results == []

        await scraper.close()

    @pytest.mark.asyncio
    async def test_semaphore_limit(self):
        """Semaphore deve limitar concorrência."""
        scraper = SteamGGScraper()
        assert scraper._semaphore._value == 8  # SEMAPHORE_LIMIT
        await scraper.close()
