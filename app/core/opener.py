"""Abrir arquivos, pastas e sites com o programa padrão do sistema."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path


class OpenError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


def open_path(path: Path) -> None:
    """Abre com o programa padrão (Excel para .xlsx, Explorer para pastas...)."""
    if not path.exists():
        raise OpenError(f"Não encontrei “{path.name}”. Ele pode ter sido movido ou apagado.")
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as exc:
        raise OpenError(
            f"O Windows não encontrou um programa para abrir “{path.name}”."
        ) from exc


def open_url(url: str) -> None:
    if not webbrowser.open(url):
        raise OpenError("Não consegui abrir o navegador.")


def reveal(path: Path) -> None:
    """Abre a pasta do arquivo com ele já selecionado."""
    if sys.platform == "win32" and path.exists():
        subprocess.Popen(f'explorer /select,"{path}"')
        return
    folder = path if path.is_dir() else path.parent
    open_path(folder)
