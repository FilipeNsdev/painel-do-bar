"""Descobre pastas de nuvem instaladas no computador.

O painel não fala direto com o Google/Microsoft: ele copia o backup para a
pasta que o aplicativo da nuvem (Google Drive para Desktop, OneDrive,
Dropbox) mantém sincronizada, e o próprio aplicativo faz o envio.
"""

from __future__ import annotations

import json
import os
import string
from dataclasses import dataclass
from pathlib import Path

BACKUP_SUBFOLDER = "Backups Painel do Bar"


@dataclass(frozen=True)
class CloudFolder:
    provider: str     # google | onedrive | dropbox
    label: str        # texto para o botão, ex.: "Google Drive (G:)"
    path: Path

    @property
    def suggested_destination(self) -> Path:
        return self.path / BACKUP_SUBFOLDER


def _windows_drive_letters() -> list[str]:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        mask = kernel32.GetLogicalDrives()
        letters = []
        for i, letter in enumerate(string.ascii_uppercase):
            if not mask & (1 << i) or letter in "AB":
                continue
            drive_type = kernel32.GetDriveTypeW(f"{letter}:\\")
            if drive_type in (2, 3, 4):   # removível, fixo, rede (CD-ROM fica de fora)
                letters.append(letter)
        return letters
    except Exception:  # noqa: BLE001
        return []


def detect_cloud_folders() -> list[CloudFolder]:
    found: list[CloudFolder] = []
    seen: set[str] = set()

    def add(provider: str, label: str, path: Path) -> None:
        key = os.path.normcase(str(path))
        if key not in seen and path.is_dir():
            seen.add(key)
            found.append(CloudFolder(provider, label, path))

    # Google Drive para Desktop: cria uma unidade (normalmente G:) com "Meu Drive"
    if os.name == "nt":
        for letter in _windows_drive_letters():
            for sub in ("Meu Drive", "My Drive"):
                p = Path(f"{letter}:\\") / sub
                try:
                    if p.is_dir():
                        add("google", f"Google Drive ({letter}:)", p)
                except OSError:
                    continue

    # Google Drive no modo "espelhar arquivos" ou o antigo Backup e Sincronização
    home = Path.home()
    for name in ("Google Drive", "GoogleDrive", "Meu Drive", "My Drive"):
        base = home / name
        for p in (base / "Meu Drive", base / "My Drive", base):
            if p.is_dir():
                add("google", "Google Drive", p)
                break

    # OneDrive: o Windows informa as pastas em variáveis de ambiente
    for env, label in (
        ("OneDriveConsumer", "OneDrive"),
        ("OneDriveCommercial", "OneDrive (empresa)"),
        ("OneDrive", "OneDrive"),
    ):
        value = os.environ.get(env)
        if value:
            add("onedrive", label, Path(value))

    # Dropbox: guarda o caminho num info.json
    for base in (os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA")):
        if not base:
            continue
        info = Path(base) / "Dropbox" / "info.json"
        try:
            data = json.loads(info.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for account in data.values():
            if isinstance(account, dict) and account.get("path"):
                add("dropbox", "Dropbox", Path(account["path"]))

    return found
