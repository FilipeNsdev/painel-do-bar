"""Biblioteca de itens do painel: adicionar, remover, renomear, trocar foto e
manter tudo em sincronia com a pasta Dados/Arquivos.

Regras principais
-----------------
* Arquivo colocado na pasta Arquivos aparece no painel sozinho.
* Arquivo apagado/movido para fora da pasta Arquivos some do painel. O nome e a
  foto personalizados ficam guardados por 30 dias: se o arquivo voltar
  (inclusive no "salvar" do Excel, que apaga e recria o arquivo), o cartão
  volta igual.
* Nome, descrição, foto e cor só existem no painel. O arquivo real nunca é
  renomeado.
* Remover um item gerenciado move o arquivo para a pasta Removidos (nunca
  apaga de verdade). Remover um item vinculado ou link só tira o atalho.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from app.core.models import Item, ItemKind, new_id, now_iso
from app.core.office import open_names_in
from app.core.paths import AppPaths
from app.core.storage import ConfigStore

log = logging.getLogger(__name__)

MISSING_GRACE_DAYS = 30

_IGNORED_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
_IGNORED_SUFFIXES = (".tmp", ".part", ".crdownload", ".partial", ".bak")
_OFFICE_TEMP = re.compile(r"^[0-9A-F]{8}$")      # temporário do Excel ao salvar
_UNSET = object()


class LibraryError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


class AddMode(str, Enum):
    MOVE = "mover"     # o arquivo sai de onde está e passa a morar na pasta do painel
    COPY = "copiar"    # o painel guarda uma cópia; o original fica onde estava
    LINK = "atalho"    # o arquivo fica onde está; o painel só aponta para ele


@dataclass
class AddResult:
    added: list[Item] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (nome, motivo)


# --------------------------------------------------------------------------- utilidades

def name_key(name: str) -> str:
    """Compara nomes como o Windows: sem diferenciar maiúsculas."""
    return name.casefold() if os.name == "nt" else name


def _path_key(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def is_ignored(path: Path) -> bool:
    """Arquivos temporários/ocultos que não devem virar cartão."""
    name = path.name
    lower = name.lower()
    if lower in _IGNORED_NAMES or lower.endswith(_IGNORED_SUFFIXES):
        return True
    if name.startswith(("~$", ".~lock", ".")) or _OFFICE_TEMP.match(name):
        return True
    if os.name == "nt":
        try:
            attrs = path.stat().st_file_attributes  # type: ignore[attr-defined]
            if attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM):
                return True
        except OSError:
            return True
    return False


def pretty_name(filename: str, *, is_dir: bool = False) -> str:
    """Nome inicial do cartão: 'controle_precos.xlsx' -> 'Controle precos'."""
    stem = filename if is_dir else Path(filename).stem
    text = re.sub(r"\s+", " ", stem.replace("_", " ")).strip()
    if text and text == text.lower():
        text = text[0].upper() + text[1:]
    return text or filename


def _listdir(folder: Path) -> list[str]:
    try:
        return os.listdir(folder)
    except OSError:
        return []


def unique_path(path: Path) -> Path:
    """'Preços.xlsx' -> 'Preços (2).xlsx' se já existir."""
    if not path.exists():
        return path
    stem, suffix = (path.name, "") if path.is_dir() else (path.stem, path.suffix)
    n = 2
    while True:
        candidate = path.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise LibraryError("Informe o endereço do site.")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    host = urlparse(url).netloc
    if not host or ("." not in host and not host.startswith("localhost")):
        raise LibraryError("Esse endereço não parece um site válido.")
    return url


def _move_error(exc: OSError) -> str:
    if isinstance(exc, PermissionError):
        return "está aberto em outro programa (feche e tente de novo)"
    return f"não pôde ser movido ({exc.strerror or exc})"


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------- biblioteca

class Library:
    def __init__(self, paths: AppPaths, store: ConfigStore):
        self.paths = paths
        self.store = store

    # ------------------------------------------------------------------ consulta
    @property
    def items(self) -> list[Item]:
        return self.store.items

    def visible_items(self) -> list[Item]:
        """Itens que aparecem na tela, na ordem escolhida pelo usuário."""
        shown = [i for i in self.items if not (i.kind is ItemKind.MANAGED and i.is_missing)]
        return sorted(shown, key=lambda i: i.position)

    def get(self, item_id: str) -> Item | None:
        return next((i for i in self.items if i.id == item_id), None)

    def require(self, item_id: str) -> Item:
        item = self.get(item_id)
        if item is None:
            raise LibraryError("Esse item não existe mais no painel.")
        return item

    def path_of(self, item: Item) -> Path | None:
        if item.kind is ItemKind.MANAGED:
            return self.paths.files / item.target
        if item.kind is ItemKind.LINKED:
            return Path(item.target)
        return None

    def open_item_ids(self) -> set[str]:
        """Itens cujo arquivo está aberto agora (Excel, Word, LibreOffice)."""
        listings: dict[Path, set[str]] = {}

        def opened(folder: Path) -> set[str]:
            if folder not in listings:
                try:
                    listings[folder] = {name_key(n) for n in open_names_in(os.listdir(folder))}
                except OSError:
                    listings[folder] = set()
            return listings[folder]

        ids: set[str] = set()
        for item in self.items:
            path = self.path_of(item)
            if path is not None and name_key(path.name) in opened(path.parent):
                ids.add(item.id)
        return ids

    def fingerprint(self) -> tuple:
        """Resumo barato do estado da pasta e dos vínculos.

        A tela compara com o resumo anterior para saber se precisa se
        atualizar (arquivo novo, apagado, salvo, aberto ou fechado).
        """
        parts: list[tuple] = []
        try:
            with os.scandir(self.paths.files) as entries:
                for e in entries:
                    try:
                        st = e.stat()
                        parts.append((e.name, st.st_mtime_ns, st.st_size))
                    except OSError:
                        parts.append((e.name, 0, 0))
        except OSError:
            pass
        for item in self.items:
            if item.kind is ItemKind.LINKED:
                target = Path(item.target)
                try:
                    st = target.stat()
                    parts.append((item.target, st.st_mtime_ns, st.st_size))
                except OSError:
                    parts.append((item.target, -1, -1))
                parts.append(tuple(sorted(open_names_in(_listdir(target.parent)))))
        return tuple(sorted(parts, key=repr))

    def image_path(self, item: Item) -> Path | None:
        if not item.image:
            return None
        path = self.paths.images / item.image
        return path if path.exists() else None

    # ------------------------------------------------------------------ sincronização
    def sync(self) -> bool:
        """Confere a pasta Arquivos e os vínculos. Devolve True se algo mudou."""
        changed = False
        now = now_iso()

        present: dict[str, Path] = {}
        try:
            for entry in self.paths.files.iterdir():
                if not is_ignored(entry):
                    present[name_key(entry.name)] = entry
        except OSError:
            log.exception("Não foi possível ler a pasta Arquivos")
            return False

        known = {name_key(i.target): i for i in self.items if i.kind is ItemKind.MANAGED}

        for key, item in known.items():
            entry = present.get(key)
            if entry is not None:
                if item.is_missing:
                    item.missing_since = None
                    changed = True
                if item.target != entry.name:           # mudou só maiúscula/minúscula
                    item.target = entry.name
                    changed = True
            elif not item.is_missing:
                item.missing_since = now
                changed = True

        for key, entry in sorted(present.items()):
            if key not in known:
                self._append(Item(
                    kind=ItemKind.MANAGED,
                    target=entry.name,
                    name=pretty_name(entry.name, is_dir=entry.is_dir()),
                ))
                changed = True

        for item in self.items:
            if item.kind is ItemKind.LINKED:
                exists = Path(item.target).exists()
                if exists and item.is_missing:
                    item.missing_since = None
                    changed = True
                elif not exists and not item.is_missing:
                    item.missing_since = now
                    changed = True

        changed |= self._prune_long_missing()

        if changed:
            self.store.save()
        return changed

    def _prune_long_missing(self) -> bool:
        limit = datetime.now() - timedelta(days=MISSING_GRACE_DAYS)
        stale = [
            i for i in self.items
            if i.kind is ItemKind.MANAGED and i.missing_since
            and datetime.fromisoformat(i.missing_since) < limit
        ]
        for item in stale:
            self._delete_image(item)
            self.items.remove(item)
        return bool(stale)

    # ------------------------------------------------------------------ adicionar
    def add_paths(self, paths: Iterable[str | Path], *, mode: AddMode) -> AddResult:
        """Adiciona arquivos/pastas ao painel (veja AddMode)."""
        result = AddResult()
        files_dir = self.paths.files

        for raw in paths:
            src = Path(raw)
            label = src.name or str(src)
            if not src.exists():
                result.skipped.append((label, "não foi encontrado"))
                continue
            if is_ignored(src):
                result.skipped.append((label, "é um arquivo temporário ou oculto"))
                continue
            if _is_inside(files_dir, src):
                result.skipped.append((label, "é a pasta do próprio painel"))
                continue

            if src.resolve().parent == files_dir.resolve():
                existing = self._find_managed(src.name)
                if existing:
                    result.skipped.append((label, "já está no painel"))
                else:
                    result.added.append(self._append(Item(
                        kind=ItemKind.MANAGED, target=src.name,
                        name=pretty_name(src.name, is_dir=src.is_dir()),
                    )))
                continue
            if _is_inside(src, files_dir):
                result.skipped.append((label, "está dentro de uma pasta que já faz parte do painel"))
                continue

            if mode is AddMode.MOVE:
                dest = unique_path(files_dir / src.name)
                try:
                    shutil.move(str(src), str(dest))
                except OSError as exc:
                    log.exception("Falha ao mover %s", src)
                    result.skipped.append((label, _move_error(exc)))
                    continue
                item = Item(kind=ItemKind.MANAGED, target=dest.name,
                            name=pretty_name(src.name, is_dir=dest.is_dir()))
            elif mode is AddMode.COPY:
                dest = unique_path(files_dir / src.name)
                try:
                    if src.is_dir():
                        shutil.copytree(src, dest)
                    else:
                        shutil.copy2(src, dest)
                except OSError as exc:
                    log.exception("Falha ao copiar %s", src)
                    if dest.is_dir():
                        shutil.rmtree(dest, ignore_errors=True)
                    else:
                        dest.unlink(missing_ok=True)
                    result.skipped.append((label, f"não pôde ser copiado ({exc.strerror or exc})"))
                    continue
                item = Item(kind=ItemKind.MANAGED, target=dest.name,
                            name=pretty_name(src.name, is_dir=src.is_dir()))
            else:
                if self._find_linked(src):
                    result.skipped.append((label, "já está no painel"))
                    continue
                item = Item(kind=ItemKind.LINKED, target=str(src.resolve()),
                            name=pretty_name(src.name, is_dir=src.is_dir()))
            result.added.append(self._append(item))

        if result.added:
            self.store.save()
        return result

    def add_link(self, name: str, url: str) -> Item:
        url = normalize_url(url)
        name = name.strip() or urlparse(url).netloc
        item = self._append(Item(kind=ItemKind.LINK, target=url, name=name, include_in_backup=False))
        self.store.save()
        return item

    # ------------------------------------------------------------------ editar
    def update(
        self,
        item_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        color: object = _UNSET,
        include_in_backup: bool | None = None,
        target: str | None = None,
    ) -> Item:
        item = self.require(item_id)
        if name is not None:
            name = name.strip()
            if not name:
                raise LibraryError("O nome não pode ficar vazio.")
            item.name = name
        if description is not None:
            item.description = description.strip()
        if color is not _UNSET:
            item.color = color or None  # type: ignore[assignment]
        if include_in_backup is not None:
            item.include_in_backup = include_in_backup
        if target is not None:
            if item.kind is ItemKind.LINK:
                item.target = normalize_url(target)
            elif item.kind is ItemKind.LINKED:
                item.target = str(Path(target).resolve())
                item.missing_since = None if Path(target).exists() else item.missing_since
        self.store.save()
        return item

    def relink(self, item_id: str, new_path: str | Path) -> Item:
        """Aponta um item vinculado para um novo local (quando o arquivo mudou de lugar)."""
        item = self.require(item_id)
        if item.kind is not ItemKind.LINKED:
            raise LibraryError("Só itens vinculados podem ser apontados para outro local.")
        new_path = Path(new_path)
        if not new_path.exists():
            raise LibraryError("O arquivo escolhido não foi encontrado.")
        item.target = str(new_path.resolve())
        item.missing_since = None
        self.store.save()
        return item

    def set_image(self, item_id: str, data: bytes, ext: str = "png") -> Item:
        item = self.require(item_id)
        self.paths.images.mkdir(parents=True, exist_ok=True)
        filename = f"{item.id}-{new_id()[:6]}.{ext.lstrip('.').lower()}"
        (self.paths.images / filename).write_bytes(data)
        self._delete_image(item)
        item.image = filename
        self.store.save()
        return item

    def clear_image(self, item_id: str) -> Item:
        item = self.require(item_id)
        self._delete_image(item)
        item.image = None
        self.store.save()
        return item

    def move(self, item_id: str, new_index: int) -> None:
        """Reordena: coloca o item na posição `new_index` entre os visíveis."""
        order = self.visible_items()
        item = self.require(item_id)
        if item not in order:
            return
        order.remove(item)
        order.insert(max(0, min(new_index, len(order))), item)
        hidden = [i for i in self.items if i not in order]
        for pos, it in enumerate(order + hidden):
            it.position = pos
        self.store.save()

    # ------------------------------------------------------------------ remover
    def remove(self, item_id: str) -> Path | None:
        """Tira o item do painel. Para itens gerenciados, move o arquivo para
        a pasta Removidos e devolve o novo caminho."""
        item = self.require(item_id)
        moved_to: Path | None = None

        if item.kind is ItemKind.MANAGED:
            src = self.paths.files / item.target
            if src.exists():
                stamp = datetime.now().strftime("%Y-%m-%d %Hh%M")
                self.paths.removed.mkdir(parents=True, exist_ok=True)
                moved_to = unique_path(self.paths.removed / f"{stamp} - {src.name}")
                try:
                    shutil.move(str(src), str(moved_to))
                except OSError as exc:
                    raise LibraryError(
                        "Não foi possível tirar o arquivo da pasta do painel. "
                        "Se ele estiver aberto (no Excel, por exemplo), feche e tente de novo."
                    ) from exc

        self._delete_image(item)
        self.items.remove(item)
        self.store.save()
        return moved_to

    # ------------------------------------------------------------------ internos
    def _append(self, item: Item) -> Item:
        item.position = max((i.position for i in self.items), default=-1) + 1
        self.items.append(item)
        return item

    def _find_managed(self, filename: str) -> Item | None:
        key = name_key(filename)
        return next(
            (i for i in self.items if i.kind is ItemKind.MANAGED and name_key(i.target) == key), None
        )

    def _find_linked(self, path: Path) -> Item | None:
        key = _path_key(path.resolve())
        return next(
            (i for i in self.items if i.kind is ItemKind.LINKED and _path_key(i.target) == key), None
        )

    def _delete_image(self, item: Item) -> None:
        if item.image:
            try:
                (self.paths.images / item.image).unlink(missing_ok=True)
            except OSError:
                log.warning("Não foi possível apagar a imagem %s", item.image)
