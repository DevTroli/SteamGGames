"""SteamGGames — funções utilitárias."""

from __future__ import annotations

import random
import re
from urllib.parse import urlparse

from steamggames.config import USER_AGENTS


def random_ua() -> str:
    """Retorna um User-Agent aleatório da lista de rotação."""
    return random.choice(USER_AGENTS)


def random_delay() -> float:
    """Retorna um delay aleatório entre DELAY_MIN e DELAY_MAX segundos."""
    from steamggames.config import DELAY_MAX, DELAY_MIN

    return random.uniform(DELAY_MIN, DELAY_MAX)


def extract_version(title: str) -> str:
    """Extrai versão do título do jogo.

    Padrões suportados:
      - "v1.2.3", "V1.2.3"
      - "Build 1234567", "Build-1234567", "Build 1234567+ALL DLCs"
      - "v1.2.3 + DLC"  →  "v1.2.3"
      - "(v1.2)"  →  "v1.2"
      - "(V1.2)"  →  "v1.2"

    Retorna "-" se não encontrar.
    """
    # Padrão: v + números com pontos (ex: v1.2.3, v1.2, V1.2.3)
    m = re.search(r"\b[vV](\d+(?:\.\d+){1,3})", title)
    if m:
        return f"v{m.group(1)}"

    # Padrão: Build + hífen/espaço + número (ex: Build-20567064, Build 20567064)
    m = re.search(r"\bBuild[-\s]+(\d+)", title, re.IGNORECASE)
    if m:
        return f"Build {m.group(1)}"

    # Padrão: Update + número
    m = re.search(r"\bUpdate\s*(\d+(?:\.\d+)*)", title, re.IGNORECASE)
    if m:
        return f"Update {m.group(1)}"

    return "-"


def extract_host(url: str) -> str:
    """Extrai o host/domain de uma URL."""
    try:
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


def is_steamgg_game_url(url: str) -> bool:
    """Verifica se uma URL é de uma página de jogo no steamgg.net.

    Páginas de jogo geralmente contêm '-free-download' no path.
    Ex: https://steamgg.net/eldin-ring-free-download
    """
    try:
        if not url or not url.startswith(("http://", "https://")):
            return False
        parsed = urlparse(url)
        return bool(
            parsed.hostname and "steamgg.net" in parsed.hostname and "-free-download" in parsed.path
        )
    except Exception:
        return False


def is_download_link(url: str) -> bool:
    """Verifica se uma URL aponta para um host de download conhecido."""
    from steamggames.config import DOWNLOAD_HOSTS

    host = extract_host(url)
    return host in DOWNLOAD_HOSTS


def sanitize_query(query: str) -> str:
    """Limpa e normaliza uma query de busca para URL."""
    # Remove caracteres especiais que não funcionam bem em URLs
    return re.sub(r"\s+", "+", query.strip())


def truncate(text: str, max_len: int = 80) -> str:
    """Trunca texto com ellipsis se exceder max_len."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
