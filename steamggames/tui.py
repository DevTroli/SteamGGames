"""SteamGGames — TUI interativa (modo padrão sem argumentos)."""

from __future__ import annotations

import webbrowser

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from steamggames.cache import invalidate_all
from steamggames.config import ALLOWED_DOMAINS, APP_DESCRIPTION, APP_NAME, APP_VERSION
from steamggames.models import GamePage, SearchResult
from steamggames.scraper import SteamGGScraper
from steamggames.utils import extract_host

console = Console()


def _show_banner() -> None:
    """Exibe banner de boas-vindas."""
    banner = Text()
    banner.append(f"  {APP_NAME} ", style="bold cyan")
    banner.append(f"v{APP_VERSION}", style="dim")
    banner.append("\n  ")
    banner.append(APP_DESCRIPTION, style="white")
    banner.append("\n")
    console.print(Panel(banner, border_style="cyan", padding=(1, 2)))


def _show_help() -> None:
    """Exibe ajuda dos comandos TUI."""
    help_table = Table(
        title="📋 Comandos",
        box=box.SIMPLE_HEAVY,
        title_style="bold yellow",
        show_header=True,
    )
    help_table.add_column("Comando", style="bold cyan", width=20)
    help_table.add_column("Descrição", style="white")

    commands = [
        ("<texto>", "Busca jogo por nome"),
        ("info <número>", "Mostra detalhes do resultado #N"),
        ("info <url>", "Mostra detalhes de uma URL"),
        ("open <número>", "Abre resultado #N no navegador"),
        ("open <url>", "Abre URL no navegador"),
        ("next / n", "Próxima página de resultados"),
        ("prev / p", "Página anterior de resultados"),
        ("refresh", "Limpa cache e refaz busca"),
        ("help / h", "Mostra esta ajuda"),
        ("quit / q", "Sair"),
    ]

    for cmd, desc in commands:
        help_table.add_row(cmd, desc)

    console.print(help_table)


def _show_results(
    results: list[SearchResult],
    query: str,
    page: int,
) -> None:
    """Exibe resultados de busca em tabela Rich."""
    if not results:
        console.print(
            f"[yellow]Nenhum resultado para '[bold]{query}[/bold]' (página {page}).[/yellow]"
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
    table.add_column("URL", style="dim blue", max_width=55, overflow="ellipsis")

    for i, r in enumerate(results, 1):
        table.add_row(str(i), r.title, r.version, r.url)

    console.print(table)
    console.print(
        f"[dim]Total: {len(results)} resultado(s) | "
        f"Use 'info <n>' para detalhes, 'open <n>' para abrir[/dim]"
    )


def _show_game_info(game: GamePage) -> None:
    """Exibe detalhes de uma página de jogo."""
    info_lines = [
        f"[bold]Título:[/bold] {game.title}",
        f"[bold]Versão:[/bold] {game.version}",
        f"[bold]URL:[/bold] [link={game.url}]{game.url}[/link]",
    ]

    console.print(
        Panel(
            "\n".join(info_lines),
            title="🎮 Detalhes do Jogo",
            border_style="cyan",
        )
    )

    if game.download_links:
        dl_table = Table(
            title="📥 Links de Download",
            box=box.ROUNDED,
            title_style="bold green",
        )
        dl_table.add_column("#", style="dim", width=4, justify="right")
        dl_table.add_column("Label", style="white", min_width=15)
        dl_table.add_column("Host", style="yellow", width=20)
        dl_table.add_column("URL", style="dim blue", max_width=55, overflow="ellipsis")

        for i, dl in enumerate(game.download_links, 1):
            dl_table.add_row(str(i), dl.label, dl.host, dl.url)

        console.print(dl_table)
    else:
        console.print("[yellow]Nenhum link de download encontrado.[/yellow]")


def _open_url(url: str) -> None:
    """Abre URL no navegador com proteção SSRF."""
    host = extract_host(url)
    if not any(domain in host for domain in ALLOWED_DOMAINS):
        console.print(
            f"[red]Bloqueado: domínio '{host}' não permitido. "
            f"Domínios permitidos: {ALLOWED_DOMAINS}[/red]"
        )
        return
    webbrowser.open(url)
    console.print(f"[green]Abrindo: {url}[/green]")


async def run_tui(refresh: bool = False) -> None:
    """Loop principal da TUI interativa.

    Fluxo:
    1. Exibe banner e ajuda
    2. Aguarda input do usuário
    3. Processa comando (search, info, open, etc.)
    4. Repete até 'quit'
    """
    _show_banner()
    _show_help()
    console.print()

    scraper = SteamGGScraper()

    # Estado da TUI
    current_results: list[SearchResult] = []
    current_query: str = ""
    current_page: int = 1
    force_refresh = refresh

    try:
        while True:
            try:
                user_input = Prompt.ask(
                    "[bold cyan]steamggames[/]",
                    default="",
                ).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Saindo...[/dim]")
                break

            if not user_input:
                continue

            # ── Quit ────────────────────────────────────────────────────
            if user_input.lower() in ("quit", "q", "exit"):
                console.print("[dim]Até! 👋[/dim]")
                break

            # ── Help ────────────────────────────────────────────────────
            if user_input.lower() in ("help", "h", "?"):
                _show_help()
                continue

            # ── Refresh ─────────────────────────────────────────────────
            if user_input.lower() == "refresh":
                invalidate_all()
                force_refresh = True
                console.print("[yellow]Cache limpo! Próximas buscas serão ao vivo.[/yellow]")
                # Se tinha busca anterior, refaz
                if current_query:
                    console.print(f"[dim]Refazendo busca: '{current_query}'...[/dim]")
                    current_results = await scraper.search(
                        current_query,
                        page=current_page,
                        force_refresh=True,
                    )
                    _show_results(current_results, current_query, current_page)
                    force_refresh = False
                continue

            # ── Next page ──────────────────────────────────────────────
            if user_input.lower() in ("next", "n") and current_query:
                current_page += 1
                console.print(f"[dim]Buscando página {current_page}...[/dim]")
                current_results = await scraper.search(
                    current_query,
                    page=current_page,
                    force_refresh=force_refresh,
                )
                _show_results(current_results, current_query, current_page)
                continue

            # ── Prev page ──────────────────────────────────────────────
            if user_input.lower() in ("prev", "p") and current_query:
                if current_page > 1:
                    current_page -= 1
                    console.print(f"[dim]Buscando página {current_page}...[/dim]")
                    current_results = await scraper.search(
                        current_query,
                        page=current_page,
                        force_refresh=force_refresh,
                    )
                    _show_results(current_results, current_query, current_page)
                else:
                    console.print("[yellow]Já está na primeira página.[/yellow]")
                continue

            # ── Info <n> ou Info <url> ──────────────────────────────────
            if user_input.lower().startswith("info"):
                arg = user_input[4:].strip()
                if not arg:
                    console.print("[yellow]Uso: info <número> ou info <url>[/yellow]")
                    continue

                # Se é um número, usa o resultado da busca
                if arg.isdigit() and current_results:
                    idx = int(arg) - 1
                    if 0 <= idx < len(current_results):
                        url = current_results[idx].url
                    else:
                        console.print(f"[red]Número inválido. Use 1-{len(current_results)}.[/red]")
                        continue
                else:
                    url = arg

                console.print(f"[dim]Obtendo detalhes: {url}...[/dim]")
                game = await scraper.game_page(url, force_refresh=force_refresh)
                if game:
                    _show_game_info(game)
                else:
                    console.print(f"[red]Falha ao obter detalhes de: {url}[/red]")
                continue

            # ── Open <n> ou Open <url> ──────────────────────────────────
            if user_input.lower().startswith("open"):
                arg = user_input[4:].strip()
                if not arg:
                    console.print("[yellow]Uso: open <número> ou open <url>[/yellow]")
                    continue

                if arg.isdigit() and current_results:
                    idx = int(arg) - 1
                    if 0 <= idx < len(current_results):
                        url = current_results[idx].url
                    else:
                        console.print(f"[red]Número inválido. Use 1-{len(current_results)}.[/red]")
                        continue
                else:
                    url = arg

                _open_url(url)
                continue

            # ── Busca (qualquer outro input) ──────────────────────────
            # Trata como termo de busca
            current_query = user_input
            current_page = 1
            console.print(f"[dim]Buscando: '{current_query}'...[/dim]")

            current_results = await scraper.search(
                current_query,
                page=current_page,
                force_refresh=force_refresh,
            )
            _show_results(current_results, current_query, current_page)

            # Depois da primeira busca, desativa force_refresh
            force_refresh = False

    finally:
        await scraper.close()
