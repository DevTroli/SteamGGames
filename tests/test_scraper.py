"""Testes unitários para steamggames.scraper — parsing de HTML com mock."""

from __future__ import annotations

import pytest

from steamggames.scraper import SteamGGScraper


# ── Fixtures de HTML ─────────────────────────────────────────────────────────

# HTML simulando página de resultados de busca
SEARCH_HTML = """
<html>
<body>
<div class="search-results">
  <a href="https://steamgg.net/elden-ring-free-download">Elden Ring Free Download</a>
  <a href="https://steamgg.net/cyberpunk-2077-free-download">Cyberpunk 2077 Free Download</a>
  <a href="https://steamgg.net/hades-free-download">Hades v1.0 Free Download</a>
  <a href="https://steamgg.net/baldurs-gate-3-free-download">Baldur's Gate 3 Build 123456 Free Download</a>
</div>
<!-- Links de navegação que NÃO devem aparecer -->
<a href="https://steamgg.net/page/2/">Next</a>
<a href="https://steamgg.net/category/rpg/">RPG</a>
</body>
</html>
"""

# HTML simulando página individual de jogo
GAME_HTML = """
<html>
<head><title>Elden Ring Free Download – SteamGG</title></head>
<body>
<article>
  <h1 class="entry-title">Elden Ring Free Download</h1>
  <div class="entry-content">
    <p>Some description...</p>
    <a class="vc_btn3 vc_btn3-color-blue" href="https://datanodes.to/abc123">Download Part 1</a>
    <a class="vc_btn3 vc_btn3-color-green" href="https://rootz.so/xyz789">Download Part 2</a>
    <a class="vc_btn3" href="https://vikingfile.com/dl/456">Mirror</a>
  </div>
</article>
</body>
</html>
"""

# HTML sem resultados
EMPTY_SEARCH_HTML = """
<html><body><p>No results found.</p></body></html>
"""

# HTML de jogo sem botões vc_btn3 mas com links de download no conteúdo
GAME_NO_VCBTN_HTML = """
<html>
<body>
<article>
  <h1 class="entry-title">Some Game Free Download</h1>
  <div class="entry-content">
    <p>Download links:</p>
    <a href="https://datanodes.to/direct123">Direct Link</a>
    <a href="https://akirabox.com/get/abc">AkiraBox</a>
  </div>
</article>
</body>
</html>
"""

# HTML de jogo sem título e sem links
GAME_MINIMAL_HTML = """
<html><body><p>Nothing here</p></body></html>
"""

# HTML de jogo com versão no título
GAME_VERSION_HTML = """
<html>
<body>
<article>
  <h1 class="entry-title">Cyberpunk 2077 v2.1 Free Download</h1>
  <div class="entry-content">
    <a class="vc_btn3" href="https://buzzheavier.com/cp2077">Download</a>
  </div>
</article>
</body>
</html>
"""

# HTML de jogo com <h2> no lugar de <h1>
GAME_H2_HTML = """
<html>
<body>
<article>
  <h2 class="entry-title">Hades Build 98765 Free Download</h2>
  <div class="entry-content">
    <a class="vc_btn3" href="https://datanodes.to/hades">Download</a>
  </div>
</article>
</body>
</html>
"""

# HTML de jogo com links duplicados (mesma URL em múltiplos botões)
GAME_DUPLICATES_HTML = """
<html>
<body>
<article>
  <h1>Duplicate Links Free Download</h1>
  <div class="entry-content">
    <a class="vc_btn3" href="https://datanodes.to/same">Part 1</a>
    <a class="vc_btn3" href="https://datanodes.to/same">Part 1 (Mirror)</a>
    <a class="vc_btn3" href="https://rootz.so/different">Part 2</a>
  </div>
</article>
</body>
</html>
"""

# HTML de jogo com botão vc_btn3 apontando para site não-download
GAME_MIXED_BTNS_HTML = """
<html>
<body>
<article>
  <h1>Mixed Buttons Free Download</h1>
  <div class="entry-content">
    <a class="vc_btn3" href="https://google.com/search">Not a Download</a>
    <a class="vc_btn3" href="https://datanodes.to/real">Real Download</a>
    <a class="vc_btn3" href="https://steamgg.net/another-page">Internal Link</a>
  </div>
</article>
</body>
</html>
"""

# HTML com resultados em <h2><a> (fallback strategy 3)
SEARCH_H2_HTML = """
<html><body>
<h2><a href="https://steamgg.net/game-a-free-download">Game A</a></h2>
<h2><a href="https://steamgg.net/game-b-free-download">Game B</a></h2>
</body></html>
"""


# ── Testes de parsing de busca ───────────────────────────────────────────────

class TestParseSearchPage:
    """Testa _parse_search_page com diferentes estruturas HTML."""

    def setup_method(self) -> None:
        self.scraper = SteamGGScraper()

    def test_standard_results(self) -> None:
        """Links com -free-download são capturados."""
        results = self.scraper._parse_search_page(SEARCH_HTML, "elden ring")
        assert len(results) == 4
        assert results[0].title == "Elden Ring"
        assert "elden-ring-free-download" in results[0].url

    def test_titles_cleaned(self) -> None:
        """'Free Download' é removido dos títulos."""
        results = self.scraper._parse_search_page(SEARCH_HTML, "test")
        for r in results:
            assert "Free Download" not in r.title

    def test_version_extraction(self) -> None:
        """Versão é extraída do título."""
        results = self.scraper._parse_search_page(SEARCH_HTML, "test")
        # Hades v1.0 → version "v1.0"
        hades = next(r for r in results if "Hades" in r.title)
        assert hades.version == "v1.0"
        # Baldur's Gate 3 Build 12345
        bg3 = next(r for r in results if "Baldur" in r.title)
        assert bg3.version == "Build 123456"

    def test_no_navigation_links(self) -> None:
        """Links de paginação e categoria são ignorados."""
        results = self.scraper._parse_search_page(SEARCH_HTML, "test")
        urls = [r.url for r in results]
        assert not any("/page/" in u for u in urls)
        assert not any("/category/" in u for u in urls)

    def test_empty_results(self) -> None:
        """Página sem resultados retorna lista vazia."""
        results = self.scraper._parse_search_page(EMPTY_SEARCH_HTML, "nothing")
        assert results == []

    def test_h2_fallback(self) -> None:
        """Fallback: resultados em <h2><a> são capturados."""
        results = self.scraper._parse_search_page(SEARCH_H2_HTML, "game")
        assert len(results) == 2

    def test_no_duplicates(self) -> None:
        """Mesma URL não aparece duas vezes."""
        html = """
        <html><body>
        <a href="https://steamgg.net/game-free-download">Game</a>
        <a href="https://steamgg.net/game-free-download">Game Again</a>
        </body></html>
        """
        results = self.scraper._parse_search_page(html, "game")
        assert len(results) == 1


# ── Testes de parsing de página de jogo ──────────────────────────────────────

class TestParseGamePage:
    """Testa _parse_game_page com diferentes estruturas HTML."""

    def setup_method(self) -> None:
        self.scraper = SteamGGScraper()

    def test_standard_game_page(self) -> None:
        """Título + 3 links vc_btn3."""
        game = self.scraper._parse_game_page(GAME_HTML, "https://steamgg.net/elden-ring-free-download")
        assert game is not None
        assert game.title == "Elden Ring"
        assert len(game.download_links) == 3
        assert game.download_links[0].host == "datanodes.to"
        assert game.download_links[1].host == "rootz.so"
        assert game.download_links[2].host == "vikingfile.com"

    def test_version_from_title(self) -> None:
        """Versão extraída do título."""
        game = self.scraper._parse_game_page(GAME_VERSION_HTML, "https://steamgg.net/cp2077")
        assert game is not None
        assert game.version == "v2.1"

    def test_h2_title_fallback(self) -> None:
        """<h2 class="entry-title"> funciona se não houver <h1>."""
        game = self.scraper._parse_game_page(GAME_H2_HTML, "https://steamgg.net/hades")
        assert game is not None
        assert "Hades" in game.title
        assert game.version == "Build 98765"

    def test_no_vcbtn_fallback(self) -> None:
        """Sem vc_btn3, fallback captura links de hosts de download."""
        game = self.scraper._parse_game_page(GAME_NO_VCBTN_HTML, "https://steamgg.net/some-game")
        assert game is not None
        assert len(game.download_links) == 2
        assert game.download_links[0].host == "datanodes.to"
        assert game.download_links[1].host == "akirabox.com"

    def test_minimal_page(self) -> None:
        """Página sem título retorna None."""
        game = self.scraper._parse_game_page(GAME_MINIMAL_HTML, "https://steamgg.net/empty")
        assert game is None

    def test_duplicate_links_deduped(self) -> None:
        """URLs duplicadas são deduplicadas."""
        game = self.scraper._parse_game_page(GAME_DUPLICATES_HTML, "https://steamgg.net/dup")
        assert game is not None
        # 2 links únicos (datanodes.to/same e rootz.so/different)
        assert len(game.download_links) == 2

    def test_mixed_buttons_filtered(self) -> None:
        """Botões vc_btn3 para hosts não-download são ignorados."""
        game = self.scraper._parse_game_page(GAME_MIXED_BTNS_HTML, "https://steamgg.net/mixed")
        assert game is not None
        assert len(game.download_links) == 1
        assert game.download_links[0].host == "datanodes.to"


# ── Testes de helpers ────────────────────────────────────────────────────────

class TestScraperHelpers:
    """Testa métodos helper do scraper."""

    def setup_method(self) -> None:
        self.scraper = SteamGGScraper()

    def test_clean_search_title(self) -> None:
        assert SteamGGScraper._clean_search_title("Elden Ring Free Download") == "Elden Ring"
        assert SteamGGScraper._clean_search_title("Game – Free Download") == "Game"
        assert SteamGGScraper._clean_search_title("") == ""
        assert SteamGGScraper._clean_search_title("No Suffix") == "No Suffix"

    def test_url_to_title(self) -> None:
        title = SteamGGScraper._url_to_title("https://steamgg.net/elden-ring-free-download")
        assert title == "Elden Ring"

    def test_url_to_title_no_suffix(self) -> None:
        title = SteamGGScraper._url_to_title("https://steamgg.net/some-game")
        assert "Some Game" in title
