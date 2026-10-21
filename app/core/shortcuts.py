"""Atalho do painel na Área de Trabalho (Windows)."""

from __future__ import annotations

import os
import subprocess

from app import APP_NAME
from app.core.scheduler import launch_command

_CREATE_NO_WINDOW = 0x08000000


class ShortcutError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def create_desktop_shortcut(name: str = APP_NAME) -> None:
    if os.name != "nt":
        raise ShortcutError("Atalho na Área de Trabalho só existe no Windows.")
    program, arguments = launch_command()
    workdir = os.path.dirname(program)
    script = (
        "$d=[Environment]::GetFolderPath('Desktop');"
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d {_ps_quote(name + '.lnk')}));"
        f"$s.TargetPath={_ps_quote(program)};"
        f"$s.Arguments={_ps_quote(arguments)};"
        f"$s.WorkingDirectory={_ps_quote(workdir)};"
        f"$s.IconLocation={_ps_quote(program + ',0')};"
        "$s.Save()"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )
    if proc.returncode != 0:
        raise ShortcutError("Não consegui criar o atalho na Área de Trabalho.")
