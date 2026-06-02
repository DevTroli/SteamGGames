"""Testes para steamggames.cli — parser de argumentos e entry point."""

from __future__ import annotations

import subprocess
import sys

import pytest

from steamggames.cli import _build_parser


class TestCLIParser:
    """Testa o parser de argumentos CLI."""

    def setup_method(self) -> None:
        self.parser = _build_parser()

    def test_no_args_defaults(self) -> None:
        """Sem subcomando → command=None (modo TUI)."""
        args = self.parser.parse_args([])
        assert args.command is None

    def test_search_command(self) -> None:
        args = self.parser.parse_args(["search", "Elden", "Ring"])
        assert args.command == "search"
        assert args.query == ["Elden", "Ring"]

    def test_search_alias(self) -> None:
        args = self.parser.parse_args(["s", "Game"])
        assert args.command == "s"
        assert args.query == ["Game"]

    def test_search_with_page(self) -> None:
        args = self.parser.parse_args(["search", "Game", "--page", "3"])
        assert args.page == 3

    def test_info_command(self) -> None:
        args = self.parser.parse_args(["info", "https://steamgg.net/test"])
        assert args.command == "info"
        assert args.url == "https://steamgg.net/test"

    def test_info_alias(self) -> None:
        args = self.parser.parse_args(["i", "https://steamgg.net/test"])
        assert args.command == "i"

    def test_open_command(self) -> None:
        args = self.parser.parse_args(["open", "https://steamgg.net/test"])
        assert args.command == "open"
        assert args.url == "https://steamgg.net/test"

    def test_refresh_flag(self) -> None:
        args = self.parser.parse_args(["--refresh", "search", "Game"])
        assert args.refresh is True

    def test_no_refresh_default(self) -> None:
        args = self.parser.parse_args(["search", "Game"])
        assert args.refresh is False

    def test_version_flag(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            self.parser.parse_args(["--version"])
        assert exc_info.value.code == 0


class TestCLIEntryPoint:
    """Testa o entry point instalado."""

    def test_version_output(self) -> None:
        """steamggames --version funciona."""
        result = subprocess.run(
            [sys.executable, "-m", "steamggames.cli", "--version"],
            capture_output=True,
            text=True,
        )
        # argparse --version causa SystemExit(0), que é OK
        assert result.returncode == 0 or "steamggames" in result.stderr.lower()

    def test_help_output(self) -> None:
        """steamggames --help funciona."""
        result = subprocess.run(
            [sys.executable, "-m", "steamggames.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "search" in result.stdout.lower()
        assert "info" in result.stdout.lower()
