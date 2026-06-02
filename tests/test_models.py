"""Testes unitários para steamggames.models — serialização e roundtrip."""

from __future__ import annotations

import pytest

from steamggames.models import DownloadLink, GamePage, SearchResult


class TestSearchResult:
    """Testa SearchResult roundtrip dict."""

    def test_to_dict_roundtrip(self) -> None:
        r = SearchResult(title="Elden Ring", url="https://steamgg.net/elden-ring-free-download", version="v1.0", snippet="RPG")
        d = r.to_dict()
        r2 = SearchResult.from_dict(d)
        assert r2.title == r.title
        assert r2.url == r.url
        assert r2.version == r.version
        assert r2.snippet == r.snippet

    def test_defaults(self) -> None:
        r = SearchResult(title="Game", url="https://example.com")
        assert r.version == "-"
        assert r.snippet == ""

    def test_empty_from_dict(self) -> None:
        r = SearchResult.from_dict({})
        assert r.title == ""
        assert r.url == ""
        assert r.version == "-"


class TestDownloadLink:
    """Testa DownloadLink roundtrip."""

    def test_roundtrip(self) -> None:
        dl = DownloadLink(label="Download", url="https://datanodes.to/abc", host="datanodes.to")
        dl2 = DownloadLink.from_dict(dl.to_dict())
        assert dl2.label == dl.label
        assert dl2.url == dl.url
        assert dl2.host == dl.host

    def test_empty(self) -> None:
        dl = DownloadLink.from_dict({})
        assert dl.label == ""
        assert dl.url == ""
        assert dl.host == ""


class TestGamePage:
    """Testa GamePage roundtrip com download_links aninhados."""

    def test_roundtrip_with_links(self) -> None:
        game = GamePage(
            title="Elden Ring",
            url="https://steamgg.net/elden-ring-free-download",
            version="v1.2",
            download_links=[
                DownloadLink(label="Part 1", url="https://datanodes.to/a", host="datanodes.to"),
                DownloadLink(label="Part 2", url="https://rootz.so/b", host="rootz.so"),
            ],
        )
        d = game.to_dict()
        game2 = GamePage.from_dict(d)
        assert game2.title == game.title
        assert len(game2.download_links) == 2
        assert game2.download_links[0].host == "datanodes.to"
        assert game2.download_links[1].host == "rootz.so"

    def test_empty_links(self) -> None:
        game = GamePage(title="Game", url="https://example.com")
        d = game.to_dict()
        game2 = GamePage.from_dict(d)
        assert game2.download_links == []

    def test_from_dict_no_links(self) -> None:
        game = GamePage.from_dict({"title": "X", "url": "https://x.com"})
        assert game.download_links == []
