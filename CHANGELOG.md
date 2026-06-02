# Changelog

Todos os cambios notáveis deste projeto serão documentados neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.0.0] — 2025-06-02

### Adicionado
- CLI com subcomandos: `search`, `info`, `open`
- Modo TUI interativo (padrão sem argumentos)
- Scraper async para steamgg.net com aiohttp
- Anti-bloqueio: semaphore=8, delay 1.5~4.5s, backoff em 403/429/503
- Rotação de User-Agent (6 UAs)
- Cache em disco com TTL (4h busca, 12h página de jogo)
- Extração de versão: v1.2.3, Build-N, Update-N
- Extração de links de download: botões `vc_btn3`
- Proteção SSRF (domínios permitidos)
- SSL/TLS com certifi CA bundle
- Seletores multi-camada (3 estratégias para busca, 4 para download)
- Bateria de testes: 151 testes unitários + integração + segurança
- README em inglês (principal) e português (secundário)
- CI/CD com GitHub Actions (lint + testes)

[1.0.0]: https://github.com/DevTroli/SteamGGames/releases/tag/v1.0.0
