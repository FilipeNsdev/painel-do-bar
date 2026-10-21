"""Backup dos arquivos do painel.

Como funciona
-------------
1. Junta tudo num .zip com data no nome:
       Arquivos/    -> conteúdo de Dados/Arquivos
       Vinculados/  -> arquivos/pastas vinculados de outros lugares do PC
       Sistema/     -> configuração do painel (nomes, fotos, ordem)
       manifesto.json e LEIA-ME.txt
2. Confere se o .zip ficou íntegro.
3. Guarda uma cópia em Dados/Backups e outra na pasta da nuvem escolhida
   (Google Drive, OneDrive...). O app da nuvem se encarrega de subir.
4. Apaga os backups mais antigos, mantendo os N mais recentes em cada lugar.
   Só apaga arquivos com o padrão de nome do painel: nada mais é tocado.

Se a nuvem não estiver acessível, o backup fica salvo no computador e o
resultado vem como "aviso", em vez de falhar.
"""

from __future__ import annotations

import errno
import json
import logging
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from app import APP_NAME, __version__
from app.core.history import BackupHistory
from app.core.library import is_ignored, name_key
from app.core.locks import FileLock, LockBusy
from app.core.office import find_open_files
from app.core.models import (
    BackupRecord, BackupStatus, BackupTrigger, Item, ItemKind, Settings, now_iso,
)
from app.core.paths import AppPaths

log = logging.getLogger(__name__)

BACKUP_PREFIX = "Backup_PainelDoBar_"
_BACKUP_RE = re.compile(
    r"^Backup_PainelDoBar_(\d{4}-\d{2}-\d{2}_\d{2}h\d{2})(?:-(\d+))?\.zip$"
)
_CHUNK = 1024 * 1024

ProgressFn = Callable[[int, int, str], None]   # (bytes feitos, total, arquivo atual)


class CloudUnavailable(Exception):
    pass


@dataclass
class _Entry:
    source: Path
    arcname: str
    size: int
    is_dir: bool = False


# --------------------------------------------------------------------------- funções auxiliares

def backup_files_in(folder: Path) -> list[Path]:
    """Backups do painel numa pasta, do mais antigo para o mais novo."""
    if not folder.is_dir():
        return []
    matches = []
    for p in folder.iterdir():
        m = _BACKUP_RE.match(p.name)
        if m and p.is_file():
            matches.append(((m.group(1), int(m.group(2) or 1)), p))
    return [p for _, p in sorted(matches)]


def apply_retention(folder: Path, keep: int) -> list[Path]:
    """Mantém só os `keep` backups mais novos. Devolve os apagados."""
    removed = []
    for old in backup_files_in(folder)[: -max(1, keep)]:
        try:
            old.unlink()
            removed.append(old)
        except OSError:
            log.warning("Não foi possível apagar o backup antigo %s", old)
    for part in folder.glob(BACKUP_PREFIX + "*.zip.part"):
        try:
            if time.time() - part.stat().st_mtime > 86400:
                part.unlink()
        except OSError:
            pass
    return removed


def _unique_name(folder: Path, base: str) -> str:
    name = f"{base}.zip"
    n = 2
    while (folder / name).exists():
        name = f"{base}-{n}.zip"
        n += 1
    return name


def _zip_info(path: Path, arcname: str) -> zipfile.ZipInfo:
    mtime = time.localtime(path.stat().st_mtime)
    date_time = max(mtime[:6], (1980, 1, 1, 0, 0, 0))
    info = zipfile.ZipInfo(arcname, date_time=date_time)
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _open_with_retry(path: Path, attempts: int = 3):
    for i in range(attempts):
        try:
            return open(path, "rb")
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(1.0)
    raise OSError(path)


def friendly_error(exc: BaseException) -> str:
    if isinstance(exc, OSError):
        if exc.errno == errno.ENOSPC:
            return "Não há espaço livre suficiente no disco para criar o backup."
        if isinstance(exc, PermissionError):
            where = f" ({exc.filename})" if exc.filename else ""
            return f"Sem permissão para ler ou gravar um arquivo{where}."
    return str(exc) or exc.__class__.__name__


# --------------------------------------------------------------------------- serviço

class BackupService:
    def __init__(self, paths: AppPaths, history: BackupHistory):
        self.paths = paths
        self.history = history

    def run(
        self,
        items: list[Item],
        settings: Settings,
        trigger: BackupTrigger,
        progress: ProgressFn | None = None,
    ) -> BackupRecord:
        """Faz o backup completo e registra no histórico. Nunca levanta exceção:
        qualquer problema volta como um BackupRecord com status 'falha'."""
        started = now_iso()
        lock = FileLock(self.paths.backup_lock)
        try:
            lock.acquire()
        except LockBusy:
            return BackupRecord(
                started_at=started, finished_at=now_iso(), trigger=trigger.value,
                status=BackupStatus.FAILED.value,
                error="Já existe um backup em andamento. Aguarde ele terminar.",
            )
        try:
            record = self._run_locked(items, settings, trigger, progress, started)
        except Exception as exc:  # noqa: BLE001 - queremos registrar qualquer falha
            log.exception("Backup falhou")
            record = BackupRecord(
                started_at=started, finished_at=now_iso(), trigger=trigger.value,
                status=BackupStatus.FAILED.value, error=friendly_error(exc),
            )
        finally:
            lock.release()

        self.history.append(record)
        log.info("Backup %s: %s %s", record.status, record.file_name, record.error)
        return record

    # ------------------------------------------------------------------
    def _run_locked(self, items, settings, trigger, progress, started) -> BackupRecord:
        warnings: list[str] = []
        entries, manifest_items, open_files = self._collect(items, warnings)
        for name in sorted(open_files):
            warnings.append(f"“{name}” estava aberto: entrou a última versão salva.")

        local_dir = self.paths.backups
        local_dir.mkdir(parents=True, exist_ok=True)
        base = BACKUP_PREFIX + datetime.now().strftime("%Y-%m-%d_%Hh%M")
        zip_name = _unique_name(local_dir, base)
        final = local_dir / zip_name
        part = local_dir / (zip_name + ".part")

        try:
            file_count = self._write_zip(part, entries, manifest_items, warnings, progress)
            with zipfile.ZipFile(part) as zf:
                bad = zf.testzip()
            if bad:
                raise OSError(f"O backup ficou corrompido no arquivo {bad}.")
            os.replace(part, final)
        finally:
            part.unlink(missing_ok=True)

        cloud_path = ""
        destination = settings.backup_destination.strip()
        if destination:
            try:
                cloud_path = str(self._copy_to_cloud(final, Path(destination)))
            except CloudUnavailable as exc:
                warnings.append(str(exc))
        else:
            warnings.append(
                "Nenhuma pasta na nuvem foi escolhida: o backup ficou só neste computador."
            )

        apply_retention(local_dir, settings.backup_keep)
        if cloud_path:
            apply_retention(Path(destination), settings.backup_keep)

        return BackupRecord(
            started_at=started,
            finished_at=now_iso(),
            trigger=trigger.value,
            status=(BackupStatus.WARNING if warnings else BackupStatus.OK).value,
            file_name=final.name,
            size_bytes=final.stat().st_size,
            file_count=file_count,
            local_path=str(final),
            cloud_path=cloud_path,
            warnings=warnings,
        )

    # ------------------------------------------------------------------ coleta
    def _collect(self, items: list[Item], warnings: list[str]):
        entries: list[_Entry] = []
        manifest: list[dict] = []
        open_files: set[str] = set()
        by_target = {name_key(i.target): i for i in items if i.kind is ItemKind.MANAGED}

        files_dir = self.paths.files
        if files_dir.is_dir():
            for top in sorted(files_dir.iterdir(), key=lambda p: p.name.lower()):
                if is_ignored(top):
                    continue
                item = by_target.get(name_key(top.name))
                if item and not item.include_in_backup:
                    continue
                arc = f"Arquivos/{top.name}"
                self._add_tree(top, arc, entries)
                manifest.append({
                    "nome": item.name if item else top.name,
                    "tipo": ItemKind.MANAGED.value,
                    "origem": str(top),
                    "no_backup": arc,
                })
            open_files |= find_open_files(files_dir)

        used: set[str] = set()
        for item in items:
            if item.kind is not ItemKind.LINKED or not item.include_in_backup:
                continue
            src = Path(item.target)
            if not src.exists():
                warnings.append(f"“{item.name}” não foi encontrado em {src} e ficou fora do backup.")
                continue
            arc = f"Vinculados/{src.name}"
            n = 2
            while arc.lower() in used:
                arc = f"Vinculados/{src.stem} ({n}){src.suffix}" if src.is_file() \
                    else f"Vinculados/{src.name} ({n})"
                n += 1
            used.add(arc.lower())
            self._add_tree(src, arc, entries)
            manifest.append({
                "nome": item.name, "tipo": ItemKind.LINKED.value,
                "origem": str(src), "no_backup": arc,
            })
            if src.is_dir():
                open_files |= find_open_files(src)
            else:
                open_files |= {n for n in find_open_files(src.parent, recursive=False) if n == src.name}

        for item in items:
            if item.kind is ItemKind.LINK:
                manifest.append({"nome": item.name, "tipo": ItemKind.LINK.value, "origem": item.target})

        if self.paths.config_file.exists():
            self._add_tree(self.paths.config_file, "Sistema/config.json", entries)
        if self.paths.images.is_dir():
            self._add_tree(self.paths.images, "Sistema/imagens", entries)

        return entries, manifest, open_files

    @staticmethod
    def _add_tree(path: Path, arc: str, entries: list[_Entry]) -> None:
        if path.is_file():
            entries.append(_Entry(path, arc, path.stat().st_size))
            return
        if not path.is_dir():
            return
        entries.append(_Entry(path, arc.rstrip("/") + "/", 0, is_dir=True))
        for dirpath, dirnames, filenames in os.walk(path):
            rel = Path(dirpath).relative_to(path)
            base = arc if str(rel) == "." else f"{arc}/{rel.as_posix()}"
            dirnames[:] = [d for d in dirnames if not is_ignored(Path(dirpath, d))]
            for d in dirnames:
                entries.append(_Entry(Path(dirpath, d), f"{base}/{d}/", 0, is_dir=True))
            for f in filenames:
                full = Path(dirpath, f)
                if is_ignored(full):
                    continue
                try:
                    entries.append(_Entry(full, f"{base}/{f}", full.stat().st_size))
                except OSError:
                    continue

    # ------------------------------------------------------------------ zip
    def _write_zip(self, part: Path, entries, manifest_items, warnings, progress) -> int:
        total = sum(e.size for e in entries) or 1
        done = 0
        count = 0
        with zipfile.ZipFile(part, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for entry in entries:
                if entry.is_dir:
                    zf.writestr(zipfile.ZipInfo(entry.arcname), b"")
                    continue
                if progress:
                    progress(done, total, entry.arcname)
                try:
                    src = _open_with_retry(entry.source)
                    info = _zip_info(entry.source, entry.arcname)
                except OSError:
                    warnings.append(f"“{entry.arcname}” não pôde ser lido e ficou fora do backup.")
                    done += entry.size
                    continue
                with src, zf.open(info, "w", force_zip64=entry.size > 2**31) as dst:
                    while chunk := src.read(_CHUNK):
                        dst.write(chunk)
                        done += len(chunk)
                        if progress:
                            progress(min(done, total), total, entry.arcname)
                if not entry.arcname.startswith("Sistema/"):   # conta só os arquivos do usuário
                    count += 1

            created = datetime.now()
            zf.writestr("manifesto.json", json.dumps({
                "programa": APP_NAME,
                "versao_programa": __version__,
                "criado_em": created.isoformat(timespec="seconds"),
                "itens": manifest_items,
                "avisos": warnings,
            }, ensure_ascii=False, indent=2))
            zf.writestr("LEIA-ME.txt", self._readme(created, manifest_items))
        if progress:
            progress(total, total, "")
        return count

    @staticmethod
    def _readme(created: datetime, manifest_items: list[dict]) -> str:
        lines = [
            f"Backup do {APP_NAME}",
            f"Feito em {created:%d/%m/%Y} às {created:%H:%M}",
            "",
            "Arquivos/    arquivos que ficam dentro do painel",
            "Vinculados/  arquivos de outros lugares do computador que estão no painel",
            "Sistema/     configuração do painel (nomes, fotos e ordem dos cartões)",
            "",
            "Para recuperar um arquivo, abra este .zip e copie o arquivo para fora dele.",
            "",
            "Conteúdo:",
        ]
        for it in manifest_items:
            where = it.get("no_backup") or it.get("origem", "")
            lines.append(f"  - {it['nome']}  ->  {where}")
        return "\r\n".join(lines) + "\r\n"

    # ------------------------------------------------------------------ nuvem
    @staticmethod
    def _copy_to_cloud(source: Path, destination: Path) -> Path:
        unavailable = CloudUnavailable(
            f"A pasta da nuvem ({destination}) não está acessível agora: o backup ficou "
            "só neste computador. Confira se o Google Drive/OneDrive está aberto e conectado."
        )
        try:
            if not destination.exists():
                if not destination.parent.exists():
                    raise unavailable
                destination.mkdir()
            name = _unique_name(destination, source.name[:-4])
            target = destination / name
            part = destination / (name + ".part")
            shutil.copyfile(source, part)
            os.replace(part, target)
            if target.stat().st_size != source.stat().st_size:
                raise OSError("tamanho diferente após a cópia")
            return target
        except CloudUnavailable:
            raise
        except OSError as exc:
            log.exception("Falha ao copiar para a nuvem")
            raise CloudUnavailable(
                f"Não foi possível copiar o backup para {destination} ({friendly_error(exc)}). "
                "Ele ficou salvo só neste computador."
            ) from exc
