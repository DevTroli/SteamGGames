# SteamGGames — CLI + TUI para steamgg.net

Buscador interativo de jogos no [steamgg.net](https://steamgg.net), diretamente do terminal.

**Autor:** DevTroli · **Licença:** MIT · **Versão:** 1.0

<sub><a href="README.md">🇺🇸 English</a> | <a href="README_pt.md">🇧🇷 Português</a></sub>

---

## Instalação

**Global (recomendado):**
```bash
pip install steamggames
steamggames
```

**Desenvolvimento:**
```bash
git clone https://github.com/DevTroli/SteamGGames.git && cd SteamGGames
uv venv && uv pip install -r requirements.txt
uv run steamggames
```

## Uso

```bash
steamggames                        # Modo TUI interativo
steamggames search "Elden Ring"    # Busca direta
steamggames info <url>             # Detalhes de um jogo
steamggames open <url>             # Abre no navegador
steamggames --refresh              # Força refresh do cache
```

## Comandos da TUI

| Comando | Ação |
|---------|------|
| `<texto>` | Busca jogo por nome |
| `info <n>` | Detalhes do resultado #N |
| `info <url>` | Detalhes de uma URL |
| `open <n>` | Abre resultado #N no navegador |
| `open <url>` | Abre URL no navegador |
| `next` / `n` | Próxima página |
| `prev` / `p` | Página anterior |
| `refresh` | Limpa cache e refaz busca |
| `help` / `h` | Ajuda |
| `quit` / `q` | Sair |

## Funcionalidades

- ⚡ **Async**: 8 conexões concorrentes (aiohttp) com semaphore
- 🛡️ **Anti-bloqueio**: delay 1.5~4.5s, backoff em 403/429/503, rotação de User-Agent
- 📦 **Cache inteligente**: 4h para busca, 12h para página de jogo (XDG)
- 🔒 **SSL/TLS**: certifi CA bundle + proteção SSRF
- 🎨 **Rich TUI**: interface colorida com tabelas e painéis
- 🔍 **Extração de versão**: detecta v1.2.3, Build N, Update N automaticamente
- 🔗 **Links de download**: extrai botões `vc_btn3` para datanodes.to, rootz.so, etc.

## Estrutura do Projeto

```
steamggames/
├── __init__.py     # Versão e metadados
├── config.py       # Constantes, URLs, anti-bloqueio, cache config
├── models.py       # Dataclasses: SearchResult, GamePage, DownloadLink
├── utils.py        # User-Agent rotation, extract_version, helpers
├── cache.py        # Cache em disco com TTL (XDG)
├── scraper.py      # Scraper async com seletores multi-camada
├── cli.py          # CLI com argparse + entry point
└── tui.py          # TUI interativa com Rich
```

## Configuração de Cache

O cache é salvo em:
- **Linux/macOS**: `~/.cache/steamggames/`
- **Windows**: `%LOCALAPPDATA%\steamggames\`

Para limpar: use o comando `refresh` na TUI ou delete a pasta manualmente.

## Desenvolvimento

```bash
# Instalar dependências de dev
uv pip install -e ".[dev]"

# Lint
ruff check steamggames/

# Type check
mypy steamggames/

# Testes
pytest
```

---

> Não afiliado ao steamgg.net. Use de acordo com os termos do site.
