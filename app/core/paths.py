"""Onde cada coisa fica guardada no disco.

Estrutura criada ao lado do executável:

    PainelDoBar.exe
    Dados/
        Arquivos/     -> as planilhas e demais arquivos do painel
        Backups/      -> cópias locais dos backups (.zip)
        Removidos/    -> arquivos tirados do painel (dá para recuperar daqui)
        Sistema/      -> configuração, fotos dos cartões e registros (não mexer)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app import APP_ID

DATA_DIR_ENV = "PAINEL_DADOS"   # permite apontar outra pasta (usado nos testes)

README_TEXT = """\
PAINEL DO BAR — O QUE TEM EM CADA PASTA

Arquivos   Os arquivos que aparecem no painel. Tudo que você colocar aqui
           aparece no painel sozinho; tudo que tirar daqui some do painel.

Backups    Cópias de segurança (.zip) feitas pelo painel. As mais antigas são
           apagadas automaticamente conforme a configuração.

Removidos  Arquivos que você removeu pelo painel. Para trazer um de volta,
           mova-o de novo para a pasta Arquivos.

Sistema    Configurações, fotos dos cartões e registros do painel.
           Não apague nem edite nada aqui.
"""


def is_frozen() -> bool:
    """True quando o programa está rodando como .exe (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    """Pasta onde o executável (ou o projeto, em desenvolvimento) está."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundle_dir() -> Path:
    """Pasta dos recursos empacotados (fontes, ícones)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", install_dir()))
    return install_dir()


def asset_path(*parts: str) -> Path:
    return bundle_dir().joinpath("assets", *parts)


def _is_writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".teste_escrita"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve_data_root() -> Path:
    """Escolhe a pasta Dados.

    1. Variável de ambiente PAINEL_DADOS (testes / uso avançado);
    2. Pasta "Dados" ao lado do executável (modo portátil);
    3. %LOCALAPPDATA%/PainelDoBar/Dados, se a pasta do .exe não aceitar escrita
       (por exemplo, se alguém colocar o programa em "Arquivos de Programas").
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override)

    portable = install_dir() / "Dados"
    if _is_writable(portable):
        return portable

    base = os.environ.get("LOCALAPPDATA")
    fallback_base = Path(base) if base else Path.home() / ".local" / "share"
    return fallback_base / APP_ID / "Dados"


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @property
    def files(self) -> Path:
        return self.root / "Arquivos"

    @property
    def backups(self) -> Path:
        return self.root / "Backups"

    @property
    def removed(self) -> Path:
        return self.root / "Removidos"

    @property
    def system(self) -> Path:
        return self.root / "Sistema"

    @property
    def images(self) -> Path:
        return self.system / "imagens"

    @property
    def logs(self) -> Path:
        return self.system / "registros"

    @property
    def config_file(self) -> Path:
        return self.system / "config.json"

    @property
    def history_file(self) -> Path:
        return self.system / "historico_backups.json"

    @property
    def backup_lock(self) -> Path:
        return self.system / "backup.lock"

    def ensure(self) -> "AppPaths":
        for folder in (self.files, self.backups, self.removed, self.images, self.logs):
            folder.mkdir(parents=True, exist_ok=True)
        readme = self.root / "LEIA-ME.txt"
        if not readme.exists():
            readme.write_text(README_TEXT, encoding="utf-8")
        return self


def default_paths() -> AppPaths:
    return AppPaths(resolve_data_root()).ensure()
