"""Atualização pelo GitHub: procura versão nova, baixa e troca o .exe.

Cada versão publicada é um "release" no GitHub com o PainelDoBar.exe anexado
(veja ferramentas/publicar_versao.py). O painel pergunta ao GitHub qual é o
último release; se o número for maior que o dele, oferece atualizar.

Para trocar o .exe, que está em uso, o painel baixa o novo ao lado
(PainelDoBar.new.exe), chama um PowerShell que espera o painel fechar, troca
os arquivos (o antigo fica como PainelDoBar.old.exe) e abre o painel de novo.
A pasta Dados não é tocada.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app import APP_ID, UPDATE_REPO, __version__

ASSET_NAME = f"{APP_ID}.exe"
_API = "https://api.github.com/repos/{repo}/releases/latest"
_TIMEOUT_S = 10
_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008


class UpdateError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


@dataclass
class UpdateInfo:
    version: str
    notes: str
    url: str
    size: int


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.10' -> (1, 2, 10). Texto estranho vira (0,), que nunca é mais novo."""
    m = re.fullmatch(r"v?(\d+(?:\.\d+)*)", text.strip())
    return tuple(int(p) for p in m.group(1).split(".")) if m else (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def parse_release(data: dict, current: str = __version__) -> UpdateInfo | None:
    """Lê a resposta do GitHub. Devolve a atualização, ou None se não houver."""
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "")
    if not is_newer(tag, current):
        return None
    asset = next((a for a in data.get("assets") or [] if a.get("name") == ASSET_NAME), None)
    if not asset:
        return None
    notes = " ".join(str(data.get("body") or "").split())
    return UpdateInfo(version=tag.lstrip("v"), notes=notes,
                      url=asset["browser_download_url"], size=int(asset.get("size") or 0))


def check(repo: str = UPDATE_REPO, current: str = __version__) -> UpdateInfo | None:
    """Pergunta ao GitHub. Sem internet ou sem release: devolve None, sem erro."""
    req = urllib.request.Request(
        _API.format(repo=repo),
        headers={"Accept": "application/vnd.github+json", "User-Agent": APP_ID},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            data = json.load(resp)
    except (OSError, ValueError):
        return None
    return parse_release(data, current)


def download(info: UpdateInfo, folder: Path,
             progress: Callable[[float], None] | None = None) -> Path:
    """Baixa o .exe novo para a pasta do painel e confere se veio inteiro."""
    target = folder / f"{APP_ID}.new.exe"
    req = urllib.request.Request(info.url, headers={"User-Agent": APP_ID})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(target, "wb") as out:
            done = 0
            while chunk := resp.read(256 * 1024):
                out.write(chunk)
                done += len(chunk)
                if progress and info.size:
                    progress(min(1.0, done / info.size))
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise UpdateError("Não consegui baixar a versão nova. Confira a internet e tente de novo.") from exc
    with open(target, "rb") as f:
        ok = f.read(2) == b"MZ"                       # todo .exe do Windows começa assim
    if not ok or (info.size and target.stat().st_size != info.size):
        target.unlink(missing_ok=True)
        raise UpdateError("A versão nova veio incompleta. Tente de novo em instantes.")
    return target


def cleanup(folder: Path) -> None:
    """Apaga as sobras de uma atualização anterior (.old.exe e .new.exe)."""
    for name in (f"{APP_ID}.old.exe", f"{APP_ID}.new.exe"):
        try:
            (folder / name).unlink(missing_ok=True)
        except OSError:
            pass


def swap_script(new_exe: Path, current_exe: Path, pids: list[int]) -> str:
    """PowerShell que espera o painel fechar, troca o .exe e abre o novo."""
    def q(p: Path) -> str:
        return "'" + str(p).replace("'", "''") + "'"
    old = current_exe.with_name(f"{APP_ID}.old.exe")
    return f"""
$ErrorActionPreference = 'SilentlyContinue'
Wait-Process -Id {",".join(str(p) for p in pids)} -Timeout 60
$cur = {q(current_exe)}; $new = {q(new_exe)}; $old = {q(old)}
$ok = $false
for ($i = 0; $i -lt 30 -and -not $ok; $i++) {{
    try {{
        if (Test-Path $old) {{ Remove-Item $old -Force -ErrorAction Stop }}
        Move-Item $cur $old -Force -ErrorAction Stop
        try {{ Move-Item $new $cur -Force -ErrorAction Stop; $ok = $true }}
        catch {{ Move-Item $old $cur -Force; throw }}
    }} catch {{ Start-Sleep -Seconds 1 }}
}}
Start-Process $cur
"""


def apply(new_exe: Path, current_exe: Path) -> None:
    """Dispara a troca. Quem chamou deve fechar o painel logo em seguida."""
    pids = [os.getpid()]
    parent = os.getppid()
    if parent:
        pids.append(parent)            # no .exe de arquivo único, o pai segura o arquivo
    encoded = base64.b64encode(swap_script(new_exe, current_exe, pids).encode("utf-16-le")).decode("ascii")
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
             "-EncodedCommand", encoded],
            creationflags=_CREATE_NO_WINDOW | _DETACHED_PROCESS, close_fds=True,
        )
    except OSError as exc:
        raise UpdateError("Não consegui instalar a versão nova.") from exc
