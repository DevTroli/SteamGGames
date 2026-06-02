# SteamGGames — CLI + TUI for steamgg.net

Interactive game browser for [steamgg.net](https://steamgg.net), right from the terminal.

**Author:** DevTroli · **License:** MIT · **Version:** 1.0

<sub><a href="README.md">🇺🇸 English</a> | <a href="README_pt.md">🇧🇷 Português</a></sub>

---

## Installation

**Global (recommended):**
```bash
pip install steamggames
steamggames
```

**Development:**
```bash
git clone https://github.com/DevTroli/SteamGGames.git && cd SteamGGames
uv venv && uv pip install -r requirements.txt
uv run steamggames
```

## Usage

```bash
steamggames                        # Interactive TUI mode
steamggames search "Elden Ring"    # Direct search
steamggames info <url>             # Game details
steamggames open <url>             # Open in browser
steamggames --refresh              # Force cache refresh
```

## TUI Commands

| Command | Action |
|---------|--------|
| `<text>` | Search by name |
| `info <n>` | Details for result #N |
| `info <url>` | Details from URL |
| `open <n>` | Open result #N in browser |
| `open <url>` | Open URL in browser |
| `next` / `n` | Next page |
| `prev` / `p` | Previous page |
| `refresh` | Clear cache and re-fetch |
| `help` / `h` | Help |
| `quit` / `q` | Quit |

## Features

- ⚡ **Async**: 8 concurrent connections (aiohttp) with semaphore
- 🛡️ **Anti-block**: 1.5~4.5s delay, backoff on 403/429/503, User-Agent rotation
- 📦 **Smart cache**: 4h for search, 12h for game page (XDG)
- 🔒 **SSL/TLS**: certifi CA bundle + SSRF protection
- 🎨 **Rich TUI**: colored interface with tables and panels
- 🔍 **Version extraction**: detects v1.2.3, Build N, Update N automatically
- 🔗 **Download links**: extracts `vc_btn3` buttons for datanodes.to, rootz.so, etc.

## Project Structure

```
steamggames/
├── __init__.py     # Version and metadata
├── config.py       # Constants, URLs, anti-block, cache config
├── models.py       # Dataclasses: SearchResult, GamePage, DownloadLink
├── utils.py        # User-Agent rotation, extract_version, helpers
├── cache.py        # Disk cache with TTL (XDG)
├── scraper.py      # Async scraper with multi-layer selectors
├── cli.py          # CLI with argparse + entry point
└── tui.py          # Interactive TUI with Rich
```

## Cache Location

Cache is stored at:
- **Linux/macOS**: `~/.cache/steamggames/`
- **Windows**: `%LOCALAPPDATA%\steamggames\`

To clear: use the `refresh` command in TUI, or delete the folder manually.

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Lint
ruff check steamggames/

# Type check
mypy steamggames/

# Tests
pytest
```

---

> Not affiliated with steamgg.net. Use in accordance with the site's terms.
