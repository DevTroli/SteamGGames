"""SteamGGames — modelos de dados (dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Resultado de busca — um jogo listado na página de resultados."""

    title: str
    url: str
    # Versão extraída do título (ex: "v1.2.3", "Build 1234567")
    version: str = "-"
    # Snippet/preview do conteúdo (se disponível)
    snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "version": self.version,
            "snippet": self.snippet,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SearchResult:
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            version=data.get("version", "-"),
            snippet=data.get("snippet", ""),
        )


@dataclass
class GamePage:
    """Página individual de um jogo — detalhes e links de download."""

    title: str
    url: str
    version: str = "-"
    # Links de download extraídos dos botões vc_btn3
    download_links: list[DownloadLink] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "version": self.version,
            "download_links": [dl.to_dict() for dl in self.download_links],
        }

    @classmethod
    def from_dict(cls, data: dict) -> GamePage:
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            version=data.get("version", "-"),
            download_links=[
                DownloadLink.from_dict(dl)
                for dl in data.get("download_links", [])
            ],
        )


@dataclass
class DownloadLink:
    """Link de download extraído de um botão vc_btn3."""

    label: str   # texto do botão (ex: "Download", "Part 1")
    url: str     # URL do link
    host: str    # host/domain (ex: "datanodes.to")

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "url": self.url,
            "host": self.host,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DownloadLink:
        return cls(
            label=data.get("label", ""),
            url=data.get("url", ""),
            host=data.get("host", ""),
        )
