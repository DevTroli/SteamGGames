"""SteamGGames — scraper assíncrono para steamgg.net.

Estrutura do site (atualizada):
  - Busca:     https://steamgg.net/?s={query}&page={page}
  - Resultados: links no formato <a href="https://steamgg.net/...-free-download">
  - Página individual:
      - Título em <h1> ou <h2>
      - Links de download: botões com classe "vc_btn3" apontando para
        datanodes.to, rootz.so, vikingfile.com, akirabox.com, buzzheavier.com
"""

from __future__ import annotations

import asyncio
import logging
import random
import ssl as ssl_module

import aiohttp
import certifi
from bs4 import BeautifulSoup, Tag

from steamggames.cache import (
    cache_key_game,
    cache_key_search,
)
from steamggames.cache import (
    get as cache_get,
)
from steamggames.cache import (
    set as cache_set,
)
from steamggames.config import (
    APP_NAME,
    BACKOFF_BASE_DELAY,
    BACKOFF_MAX_RETRIES,
    BACKOFF_STATUS_CODES,
    BASE_URL,
    CACHE_TTL_GAME,
    CACHE_TTL_SEARCH,
    DEBUG,
    REQUEST_TIMEOUT,
    SEARCH_URL,
    SEMAPHORE_LIMIT,
)
from steamggames.models import DownloadLink, GamePage, SearchResult
from steamggames.utils import (
    extract_host,
    extract_version,
    is_download_link,
    is_steamgg_game_url,
    random_delay,
    random_ua,
    sanitize_query,
)

logger = logging.getLogger(APP_NAME)


# ── Sessão HTTP ─────────────────────────────────────────────────────────────


def _make_ssl_context() -> ssl_module.SSLContext:
    """Cria SSL context com certifi CA bundle."""
    ctx = ssl_module.create_default_context(cafile=certifi.where())
    return ctx


class SteamGGScraper:
    """Scraper assíncrono para steamgg.net com anti-bloqueio e cache."""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
        self._session: aiohttp.ClientSession | None = None
        self._ssl = _make_ssl_context()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Cria ou retorna a sessão HTTP compartilhada."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self._base_headers(),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                connector=aiohttp.TCPConnector(
                    ssl=self._ssl,
                    limit=SEMAPHORE_LIMIT,
                    limit_per_host=2,  # no máximo 2 conexões por host
                ),
            )
        return self._session

    def _base_headers(self) -> dict[str, str]:
        """Headers base para todas as requisições."""
        return {
            "User-Agent": random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _fetch(
        self,
        url: str,
        retries: int = BACKOFF_MAX_RETRIES,
    ) -> str | None:
        """Faz GET com anti-bloqueio: semaphore, delay, backoff, UA rotation.

        Args:
            url: URL para fetch
            retries: tentativas restantes em caso de status de bloqueio

        Returns:
            HTML da página ou None se falhar
        """
        sem = self._semaphore
        async with sem:
            # Delay aleatório entre requisições
            delay = random_delay()
            if DEBUG:
                logger.debug(f"Delay {delay:.2f}s antes de: {url}")
            await asyncio.sleep(delay)

        session = await self._get_session()

        for attempt in range(retries + 1):
            try:
                # Rotação de UA a cada tentativa
                headers = {"User-Agent": random_ua()}

                async with session.get(url, headers=headers) as resp:
                    if resp.status in BACKOFF_STATUS_CODES:
                        # Backoff exponencial
                        wait = BACKOFF_BASE_DELAY * (2**attempt) + random.uniform(0, 2)
                        logger.warning(
                            f"Status {resp.status} em {url} — "
                            f"backoff {wait:.1f}s (tentativa {attempt + 1}/{retries + 1})"
                        )
                        await asyncio.sleep(wait)
                        continue

                    if resp.status == 200:
                        return await resp.text()

                    logger.warning(f"Status {resp.status} em {url}")
                    return None

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Erro de rede em {url}: {e}")
                if attempt < retries:
                    wait = BACKOFF_BASE_DELAY * (2**attempt)
                    await asyncio.sleep(wait)
                    continue
                return None

        return None

    # ── Busca ───────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        page: int = 1,
        force_refresh: bool = False,
    ) -> list[SearchResult]:
        """Busca jogos no steamgg.net.

        URL: https://steamgg.net/?s={query}&page={page}

        O site retorna resultados com links para páginas de jogos.
        Os resultados vêm em tags <a> que apontam para URLs contendo
        "-free-download" no path.

        Args:
            query: termo de busca (ex: "Elden Ring")
            page: número da página (1-indexed)
            force_refresh: se True, ignora cache

        Returns:
            Lista de SearchResult
        """
        safe_query = sanitize_query(query)
        ckey = cache_key_search(safe_query, page)

        # Tenta cache primeiro
        if not force_refresh:
            cached = cache_get(ckey, ttl=CACHE_TTL_SEARCH)
            if cached is not None:
                if DEBUG:
                    logger.debug(f"Cache hit para busca: {ckey}")
                return [SearchResult.from_dict(r) for r in cached]

        url = SEARCH_URL.format(query=safe_query, page=page)
        html = await self._fetch(url)

        if html is None:
            return []

        results = self._parse_search_page(html, query)

        # Salva no cache
        cache_set(ckey, [r.to_dict() for r in results])

        return results

    def _parse_search_page(self, html: str, query: str) -> list[SearchResult]:
        """Parseia a página de resultados de busca.

        Seletores usados (estratégia multi-camada):
        1. Procura todos os <a> com href contendo "-free-download"
           → Esses são os links de jogos no steamgg.net
        2. Fallback: procura <a> com href começando com BASE_URL
           que NÃO sejam navegação/paginação
        3. Extrai o título do texto do link ou do próximo elemento de texto

        A página de busca do steamgg.net lista os jogos como:
          <a href="https://steamgg.net/elden-ring-free-download">
            Elden Ring Free Download
          </a>
        """
        soup = BeautifulSoup(html, "html.parser")
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        # ── Estratégia 1: Links com "-free-download" no href ────────────
        # Principal seletor — captura a maioria dos resultados
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not is_steamgg_game_url(href):
                continue

            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Título: texto do link, limpo
            title = a_tag.get_text(strip=True)

            # Remove sufixo "Free Download" do título para display
            title = self._clean_search_title(title)

            if not title:
                # Tenta pegar texto do próximo elemento sibling
                title = self._extract_title_from_sibling(a_tag)

            if not title:
                # Fallback: usa o path da URL como título
                title = self._url_to_title(href)

            version = extract_version(title)

            results.append(
                SearchResult(
                    title=title,
                    url=href,
                    version=version,
                )
            )

        # ── Estratégia 2 (fallback): Links internos do steamgg.net ──────
        # Se a estratégia 1 não encontrou nada, tenta links genéricos
        if not results:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()

                # Filtra: deve ser do steamgg.net e não ser navegação
                if not href.startswith(BASE_URL):
                    continue
                if href in seen_urls:
                    continue
                # Ignora links de paginação e navegação
                skip_patterns = [
                    "/page/",
                    "/?s=",
                    "/category/",
                    "/tag/",
                    "/author/",
                    "/feed/",
                    "#",
                    "javascript:",
                ]
                if any(pat in href.lower() for pat in skip_patterns):
                    continue

                seen_urls.add(href)
                title = a_tag.get_text(strip=True)
                title = self._clean_search_title(title)

                if not title or len(title) < 3:
                    continue

                version = extract_version(title)
                results.append(
                    SearchResult(
                        title=title,
                        url=href,
                        version=version,
                    )
                )

        # ── Estratégia 3 (fallback): Procura por <h2>/<h3> com links ───
        # Alguns temas WordPress mostram resultados como <h2><a href="...">
        if not results:
            for heading in soup.find_all(["h2", "h3"]):
                a_tag = heading.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag["href"].strip()
                if href in seen_urls:
                    continue
                if "steamgg.net" not in href:
                    continue

                seen_urls.add(href)
                title = heading.get_text(strip=True)
                title = self._clean_search_title(title)

                if not title or len(title) < 3:
                    continue

                version = extract_version(title)
                results.append(
                    SearchResult(
                        title=title,
                        url=href,
                        version=version,
                    )
                )

        return results

    # ── Página individual do jogo ───────────────────────────────────────

    async def game_page(
        self,
        url: str,
        force_refresh: bool = False,
    ) -> GamePage | None:
        """Obtém detalhes de uma página individual de jogo.

        Args:
            url: URL da página do jogo (ex: https://steamgg.net/elden-ring-free-download)
            force_refresh: se True, ignora cache

        Returns:
            GamePage ou None se falhar
        """
        ckey = cache_key_game(url)

        if not force_refresh:
            cached = cache_get(ckey, ttl=CACHE_TTL_GAME)
            if cached is not None:
                if DEBUG:
                    logger.debug(f"Cache hit para jogo: {ckey}")
                return GamePage.from_dict(cached)

        html = await self._fetch(url)
        if html is None:
            return None

        game = self._parse_game_page(html, url)

        if game is not None:
            cache_set(ckey, game.to_dict())

        return game

    def _parse_game_page(self, html: str, url: str) -> GamePage | None:
        """Parseia a página individual de um jogo.

        Seletores usados:
        1. Título:
           - <h1 class="entry-title"> ou <h1>  (temas WordPress)
           - <h2 class="entry-title"> ou <h2>  (fallback)
           - <title> tag (último recurso)

        2. Links de download:
           - Botões com classe "vc_btn3" que apontam para
             hosts de download (datanodes.to, rootz.so, etc.)
           - Fallback: qualquer <a> com href apontando para
             os hosts de download conhecidos
        """
        soup = BeautifulSoup(html, "html.parser")

        # ── Título ──────────────────────────────────────────────────
        # O steamgg.net usa <h2> para o título do jogo nas páginas individuais
        # (padrão comum em temas WordPress que usam h2 para posts).
        # O <title> contém " - SteamGG.NET" como sufixo.
        # IMPORTANTE: priorizar entry-title e h1 sobre h2 genérico,
        # pois h2 pode ser "Download Links" ou outras seções.
        title = ""

        # Seletor 1: <h1 class="entry-title"> (tema WordPress padrão)
        h1_entry = soup.find("h1", class_="entry-title")
        if h1_entry:
            title = h1_entry.get_text(strip=True)

        # Seletor 2: qualquer <h1>
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Seletor 3: <h2 class="entry-title"> (tema WordPress com h2 para posts)
        h2_entry = soup.find("h2", class_="entry-title")
        if not title and h2_entry:
            title = h2_entry.get_text(strip=True)

        # Seletor 4: qualquer <h2> que contenha "Free Download"
        # (títulos de jogos sempre contêm "Free Download" no steamgg.net)
        if not title:
            for h2 in soup.find_all("h2"):
                text = h2.get_text(strip=True)
                if "Free Download" in text or "free download" in text:
                    title = text
                    break

        # Seletor 5: <h2> dentro de <article> que seja o PRIMEIRO h2
        # (provável título se não houver entry-title)
        if not title:
            article = soup.find("article")
            if article and isinstance(article, Tag):
                h2 = article.find("h2")
                if h2:
                    h2_text = h2.get_text(strip=True)
                    # Heurística: título deve ser longo o suficiente e
                    # não deve parecer uma seção como "Download Links"
                    skip_texts = {"download links", "requirements", "screenshots"}
                    if h2_text.lower() not in skip_texts and len(h2_text) > 3:
                        title = h2_text

        # Seletor 6: fallback para <title> tag
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Remove sufixos comuns do site (várias variações)
                for suffix in [
                    " – SteamGG.NET",
                    " - SteamGG.NET",
                    " | SteamGG.NET",
                    " – SteamGG",
                    " - SteamGG",
                    " | SteamGG",
                    " - steamgg.net",
                ]:
                    if suffix in title:
                        title = title.replace(suffix, "")
                        break

        if not title:
            return None

        title = self._clean_search_title(title)
        version = extract_version(title)

        # ── Links de download ───────────────────────────────────────
        download_links: list[DownloadLink] = []
        seen_urls: set[str] = set()

        # Seletor 1: botões com classe "vc_btn3"
        # Ex: <a class="vc_btn3 vc_btn3-color-blue..." href="https://datanodes.to/...">
        for btn in soup.find_all("a", class_="vc_btn3"):
            if not isinstance(btn, Tag):
                continue
            href = btn.get("href", "").strip()
            if not href or href in seen_urls:
                continue

            if is_download_link(href):
                seen_urls.add(href)
                label = btn.get_text(strip=True) or "Download"
                host = extract_host(href)
                download_links.append(DownloadLink(label=label, url=href, host=host))

        # Seletor 2: qualquer <a> com classe parcial "vc_btn"
        # Alguns temas usam variações como "vc_btn3-size-md"
        if not download_links:
            for a_tag in soup.find_all("a", class_=True):
                if not isinstance(a_tag, Tag):
                    continue
                classes = a_tag.get("class", [])
                if not any("vc_btn" in c for c in classes):
                    continue
                href = a_tag.get("href", "").strip()
                if not href or href in seen_urls:
                    continue
                if is_download_link(href):
                    seen_urls.add(href)
                    label = a_tag.get_text(strip=True) or "Download"
                    host = extract_host(href)
                    download_links.append(DownloadLink(label=label, url=href, host=host))

        # Seletor 3 (fallback): qualquer link <a> apontando para hosts de download
        if not download_links:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if href in seen_urls:
                    continue
                if is_download_link(href):
                    seen_urls.add(href)
                    label = a_tag.get_text(strip=True) or "Download"
                    host = extract_host(href)
                    download_links.append(DownloadLink(label=label, url=href, host=host))

        # Seletor 4 (fallback extremo): qualquer URL http/https no
        # conteúdo que aponte para hosts de download
        if not download_links:
            content_area = (
                soup.find("article")
                or soup.find(class_="entry-content")
                or soup.find(class_="post-content")
            )
            if content_area and isinstance(content_area, Tag):
                for a_tag in content_area.find_all("a", href=True):
                    href = a_tag["href"].strip()
                    if href in seen_urls:
                        continue
                    if is_download_link(href):
                        seen_urls.add(href)
                        label = a_tag.get_text(strip=True) or "Download"
                        host = extract_host(href)
                        download_links.append(DownloadLink(label=label, url=href, host=host))

        return GamePage(
            title=title,
            url=url,
            version=version,
            download_links=download_links,
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _clean_search_title(title: str) -> str:
        """Limpa o título removendo sufixos comuns do site.

        O steamgg.net usa títulos como:
          "Stellar Blade Free Download [v1.4.1/Build-19963153+ ALL DLCs]"
          "Elden Ring Free Download"

        Precisamos remover "Free Download" mesmo que não esteja no final,
        pois versões/infos vêm depois dele.
        """
        if not title:
            return ""

        import re

        # Regex unificado: remove "Free Download" com qualquer prefixo
        # (espaço, em-dash, hífen) e qualquer sufixo (espaço antes de versão)
        # Captura: " Free Download", "– Free Download", "- Free Download",
        #          " Free Download [v1.0]", etc.
        title = re.sub(
            r"\s*[-–]?\s*Free\s+Download\s*",
            " ",
            title,
            flags=re.IGNORECASE,
        ).strip()

        return title.strip()

    @staticmethod
    def _extract_title_from_sibling(a_tag: Tag) -> str:
        """Tenta extrair o título do próximo elemento irmão do link."""
        # Procura próximo sibling com texto
        sibling = a_tag.next_sibling
        while sibling:
            if isinstance(sibling, Tag):
                text = sibling.get_text(strip=True)
                if text and len(text) > 2:
                    return text
            elif isinstance(sibling, str) and sibling.strip():
                return sibling.strip()
            sibling = sibling.next_sibling
        return ""

    @staticmethod
    def _url_to_title(url: str) -> str:
        """Converte URL path em título legível.

        Ex: /elden-ring-free-download → "Elden Ring"
        """
        from urllib.parse import urlparse

        path = urlparse(url).path.strip("/")
        # Remove "-free-download" do final
        if path.endswith("-free-download"):
            path = path[: -len("-free-download")]
        # Substitui hífens por espaços e capitaliza
        title = path.replace("-", " ").replace("_", " ").strip()
        return title.title() if title else "Unknown"

    # ── Cleanup ──────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Fecha a sessão HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
