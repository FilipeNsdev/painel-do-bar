"""Tipos de arquivo que o painel reconhece.

Para reconhecer uma extensão nova, basta acrescentá-la em EXTENSIONS.
Para criar um tipo novo, acrescente uma entrada em CATEGORIES e inclua a
chave dele em FILTER_ORDER (ordem dos filtros na tela).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileCategory:
    key: str
    label: str      # singular, ex.: "Planilha"
    plural: str     # ex.: "Planilhas"
    color: str      # cor da capa do cartão quando não há foto


CATEGORIES: dict[str, FileCategory] = {
    c.key: c
    for c in (
        FileCategory("planilha", "Planilha", "Planilhas", "#22604A"),
        FileCategory("documento", "Documento", "Documentos", "#2D5887"),
        FileCategory("pdf", "PDF", "PDFs", "#A3402F"),
        FileCategory("apresentacao", "Apresentação", "Apresentações", "#B0612A"),
        FileCategory("imagem", "Imagem", "Imagens", "#5F4E86"),
        FileCategory("texto", "Texto", "Textos", "#4A585E"),
        FileCategory("compactado", "Compactado", "Compactados", "#5E5A52"),
        FileCategory("pasta", "Pasta", "Pastas", "#8A6C33"),
        FileCategory("link", "Site", "Sites", "#226D7A"),
        FileCategory("outro", "Arquivo", "Outros", "#5F6B66"),
    )
}

EXTENSIONS: dict[str, str] = {
    # planilhas
    **dict.fromkeys(
        [".xlsx", ".xlsm", ".xls", ".xlsb", ".xltx", ".xltm", ".ods", ".csv", ".tsv", ".numbers"],
        "planilha",
    ),
    # documentos
    **dict.fromkeys([".docx", ".docm", ".doc", ".dotx", ".odt", ".rtf", ".pages"], "documento"),
    ".pdf": "pdf",
    **dict.fromkeys([".pptx", ".pptm", ".ppt", ".odp", ".key"], "apresentacao"),
    **dict.fromkeys(
        [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic", ".svg"],
        "imagem",
    ),
    **dict.fromkeys([".txt", ".md", ".xml", ".json", ".log", ".ofx", ".sped"], "texto"),
    **dict.fromkeys([".zip", ".rar", ".7z", ".tar", ".gz"], "compactado"),
}

# Ordem em que os filtros aparecem na tela
FILTER_ORDER = [
    "planilha", "documento", "pdf", "apresentacao", "imagem",
    "texto", "compactado", "pasta", "link", "outro",
]


def category_for(path: str | Path, *, is_dir: bool = False, is_link: bool = False) -> FileCategory:
    if is_link:
        return CATEGORIES["link"]
    if is_dir:
        return CATEGORIES["pasta"]
    key = EXTENSIONS.get(Path(path).suffix.lower(), "outro")
    return CATEGORIES[key]


def badge_for(path: str | Path, *, is_dir: bool = False, is_link: bool = False) -> str:
    """Texto grande mostrado no cartão sem foto (ex.: XLSM, PDF, PASTA)."""
    if is_link:
        return "SITE"
    if is_dir:
        return "PASTA"
    ext = Path(path).suffix.lstrip(".").upper()
    return ext[:5] if ext else "ARQ"
