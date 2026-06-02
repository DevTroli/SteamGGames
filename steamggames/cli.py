"""SteamGGames — CLI (entry point principal)."""

from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console

from steamggames import __version__
from steamggames.config import APP_DESCRIPTION, APP_NAME
from steamggames.scraper import SteamGGScraper
from steamggames.tui import run_tui

console = Console()


def _build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=APP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  steamggames                          Modo TUI interativo
  steamggames search "Elden Ring"      Busca direta
  steamggames info <url>               Detalhes de um jogo
  steamggames open <url>               Abre jogo no navegador
  steamggames --refresh                Força refresh do cache
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Força refresh — ignora cache",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    # search
    sp_search = subparsers.add_parser(
        "search",
        help="Busca jogos por nome",
        aliases=["s"],
    )
    sp_search.add_argument(
        "query",
        nargs="+",
        help="Termo de busca (ex: 'Elden Ring')",
    )
    sp_search.add_argument(
        "--page", "-p",
        type=int,
        default=1,
        help="Número da página (default: 1)",
    )

    # info
    sp_info = subparsers.add_parser(
        "info",
        help="Mostra detalhes de um jogo",
        aliases=["i"],
    )
    sp_info.add_argument(
        "url",
        help="URL da página do jogo no steamgg.net",
    )

    # open
    sp_open = subparsers.add_parser(
        "open",
        help="Abre página do jogo no navegador",
        aliases=["o"],
    )
    sp_open.add_argument(
        "url",
        help="URL da página do jogo no steamgg.net",
    )

    return parser


async def _cmd_search(query: str, page: int, refresh: bool) -> None:
    """Executa busca e exibe resultados na tabela Rich."""
    from rich import box
    from rich.table import Table

    scraper = SteamGGScraper()
    try:
        results = await scraper.search(query, page=page, force_refresh=refresh)
    finally:
        await scraper.close()

    if not results:
        console.print(
            f"[yellow]Nenhum resultado para '[bold]{query}[/bold]' "
            f"(página {page}).[/yellow]"
        )
        return

    table = Table(
        title=f"🔍 Resultados para '{query}' (página {page})",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Título", style="white", min_width=30)
    table.add_column("Versão", style="green", width=12)
    table.add_column("URL", style="dim blue", max_width=50, overflow="ellipsis")

    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r.title,
            r.version,
            r.url,
        )

    console.print(table)
    console.print(
        f"[dim]Total: {len(results)} resultado(s) | "
        f"Use 'steamggames info <url>' para detalhes[/dim]"
    )


async def _cmd_info(url: str, refresh: bool) -> None:
    """Exibe detalhes de uma página de jogo."""
    from rich import box
    from rich.panel import Panel
    from rich.table import Table

    scraper = SteamGGScraper()
    try:
        game = await scraper.game_page(url, force_refresh=refresh)
    finally:
        await scraper.close()

    if game is None:
        console.print(f"[red]Não foi possível obter detalhes de: {url}[/red]")
        return

    # Painel com informações do jogo
    info_lines = [
        f"[bold]Título:[/bold] {game.title}",
        f"[bold]Versão:[/bold] {game.version}",
        f"[bold]URL:[/bold] [link={game.url}]{game.url}[/link]",
    ]

    console.print(Panel(
        "\n".join(info_lines),
        title="🎮 Detalhes do Jogo",
        border_style="cyan",
    ))

    # Tabela de links de download
    if game.download_links:
        dl_table = Table(
            title="📥 Links de Download",
            box=box.ROUNDED,
            title_style="bold green",
        )
        dl_table.add_column("#", style="dim", width=4, justify="right")
        dl_table.add_column("Label", style="white", min_width=15)
        dl_table.add_column("Host", style="yellow", width=20)
        dl_table.add_column("URL", style="dim blue", max_width=50, overflow="ellipsis")

        for i, dl in enumerate(game.download_links, 1):
            dl_table.add_row(str(i), dl.label, dl.host, dl.url)

        console.print(dl_table)
    else:
        console.print("[yellow]Nenhum link de download encontrado.[/yellow]")


async def _cmd_open(url: str) -> None:
    """Abre URL no navegador padrão."""
    import webbrowser

    from steamggames.config import ALLOWED_DOMAINS
    from steamggames.utils import extract_host

    host = extract_host(url)
    # Proteção SSRF: só abre URLs de domínios permitidos
    if not any(domain in host for domain in ALLOWED_DOMAINS):
        console.print(
            f"[red]Bloqueado: domínio '{host}' não permitido. "
            f"Domínios permitidos: {ALLOWED_DOMAINS}[/red]"
        )
        return

    webbrowser.open(url)
    console.print(f"[green]Abrindo no navegador: {url}[/green]")


async def async_main(args: argparse.Namespace) -> None:
    """Ponto de entrada async do CLI."""
    refresh = args.refresh

    if args.command in ("search", "s"):
        query = " ".join(args.query)
        await _cmd_search(query, page=args.page, refresh=refresh)

    elif args.command in ("info", "i"):
        await _cmd_info(args.url, refresh=refresh)

    elif args.command in ("open", "o"):
        await _cmd_open(args.url)

    else:
        # Sem subcomando → modo TUI
        await run_tui(refresh=refresh)


def main() -> None:
    """Entry point principal — chamado pelo console_scripts."""
    parser = _build_parser()
    args = parser.parse_args()

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        console.print("\n[dim]Saindo...[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
