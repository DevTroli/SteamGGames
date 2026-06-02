"""SteamGGames — configuração central e constantes."""

from __future__ import annotations

import os
import sys

# ── Identidade ──────────────────────────────────────────────────────────────
APP_NAME = "steamggames"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "SteamGGames — CLI + TUI para buscar jogos no steamgg.net"

# ── URLs do site ────────────────────────────────────────────────────────────
BASE_URL = "https://steamgg.net"
# Busca: https://steamgg.net/?s={query}&page={page}
SEARCH_URL = BASE_URL + "/?s={query}&page={page}"

# ── Anti-bloqueio ───────────────────────────────────────────────────────────
# Semáforo para limitar requisições concorrentes
SEMAPHORE_LIMIT = 8
# Delay aleatório entre requisições (em segundos)
DELAY_MIN = 1.5
DELAY_MAX = 4.5
# Timeout total por requisição (segundos)
REQUEST_TIMEOUT = 25
# Backoff em status codes de bloqueio
BACKOFF_STATUS_CODES = {403, 429, 503}
BACKOFF_BASE_DELAY = 10  # segundos base para backoff exponencial
BACKOFF_MAX_RETRIES = 3

# ── Rotação de User-Agent ───────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ── Cache ───────────────────────────────────────────────────────────────────
# TTL do cache em segundos: 4h para busca, 12h para página de jogo
CACHE_TTL_SEARCH = 4 * 3600    # 4 horas
CACHE_TTL_GAME = 12 * 3600     # 12 horas

# Diretório de cache (XDG)
if sys.platform == "win32":
    XDG_CACHE_HOME = os.path.join(
        os.environ.get("LOCALAPPDATA", "."), "steamggames"
    )
else:
    XDG_CACHE_HOME = os.environ.get(
        "XDG_CACHE_HOME", os.path.expanduser("~/.cache")
    )
CACHE_DIR = os.path.join(XDG_CACHE_HOME, "steamggames")

# ── Paginação ───────────────────────────────────────────────────────────────
PAGE_SIZE = 20  # resultados por página na TUI

# ── Domínios permitidos para abrir no navegador (SSRF protection) ────────────
ALLOWED_DOMAINS = {"steamgg.net"}

# ── Domínios de download conhecidos (para extração de links) ────────────────
# Botões com classe vc_btn3 apontam para estes hosts
DOWNLOAD_HOSTS = {
    "datanodes.to",
    "rootz.so",
    "vikingfile.com",
    "akirabox.com",
    "buzzheavier.com",
}

# ── Debug ───────────────────────────────────────────────────────────────────
DEBUG = os.environ.get("STEAMGGAMES_DEBUG", "").strip() not in ("", "0", "false")
