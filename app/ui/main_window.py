"""Janela principal do painel.

Monta cabeçalho, filtros, grade de cartões e barra de backup, e liga cada
botão à ação certa no núcleo (app.core.panel.Panel). As regras ficam no
núcleo; aqui só tem tela e conversa com o usuário.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from urllib.parse import urlparse

import customtkinter as ctk

from app import APP_ID
from app.core import opener
from app.core.excel import ExcelError
from app.core.updater import UpdateError
from app.core.file_types import CATEGORIES, FILTER_ORDER, FileCategory, badge_for, category_for
from app.core.library import AddMode, LibraryError, is_ignored
from app.core.models import BackupRecord, BackupStatus, BackupTrigger, Item, ItemKind
from app.core.panel import Panel
from app.ui import art, dropfiles, text, theme
from app.ui.dialogs.add_items import AddLinkDialog, AddModeDialog
from app.ui.dialogs.base import confirm, message, set_window_icon, style_titlebar
from app.ui.dialogs.edit_item import EditItemDialog
from app.ui.dialogs.settings import SettingsDialog
from app.ui.theme import C
from app.ui.widgets.backup_bar import BackupBar
from app.ui.widgets.card import CardData
from app.ui.widgets.card_grid import CardGrid
from app.ui.widgets.filters import ALL, FilterBar
from app.ui.widgets.header import Header
from app.ui.widgets.popup_menu import SEPARATOR, MenuItem, PopupMenu
from app.ui.widgets.toast import Toast
from app.ui.widgets.update_bar import UpdateBar

log = logging.getLogger(__name__)

POLL_MS = 2000           # de quanto em quanto tempo confere a pasta
DEFAULT_SIZE = (1180, 760)


class MainWindow(ctk.CTk):
    def __init__(self, panel: Panel):
        super().__init__()
        self.panel = panel
        self.lib = panel.library
        self.search_text = ""
        self._fingerprint: tuple | None = None
        self._history_mtime = 0.0
        self._images: dict[tuple, ctk.CTkImage] = {}
        self._backup_thread: threading.Thread | None = None
        self._queue: queue.Queue = queue.Queue()
        self._excel_summary = ""   # "Salvei e fechei 2 planilhas..." para o aviso final

        self.title(panel.settings.panel_name)
        set_window_icon(self)
        self.after(50, lambda: style_titlebar(self))
        self.minsize(760, 540)
        self._restore_geometry()
        self.configure(fg_color=C["bg"])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.header = Header(
            self, on_search=self._on_search, on_add=self._show_add_menu,
            on_settings=lambda: self.open_settings(), on_open_folder=self._open_files_folder,
        )
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.set_title(panel.settings.panel_name)

        self.filters = FilterBar(self, on_change=lambda _k: self.refresh(sync=False))
        self.update_bar = UpdateBar(self, on_update=self._install_update,
                                    on_later=lambda: self.update_bar.grid_remove())
        self._update_info = None
        self.filters.grid(row=2, column=0, sticky="ew", padx=26, pady=(16, 0))

        self.cards = CardGrid(self, on_open=self.open_item, on_menu=self._show_item_menu,
                              on_reorder=self._save_order)
        self.cards.grid(row=3, column=0, sticky="nsew")

        self.backup_bar = BackupBar(self, on_backup=lambda: self.start_backup(),
                                    on_view=self._view_backups)
        self.backup_bar.grid(row=4, column=0, sticky="ew")
        self.toast = Toast(self)

        self.bind("<Control-f>", lambda _e: self.header.focus_search())
        self.bind("<F5>", lambda _e: self.refresh())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.refresh()
        self.after(POLL_MS, self._poll)
        self.after(1500, self._startup_tasks)
        self.after(300, lambda: dropfiles.enable(self, self._on_files_dropped))

    # ================================================================== tela
    def refresh(self, *, sync: bool = True) -> None:
        """Relê a pasta (se sync) e redesenha os cartões e a barra de backup."""
        if sync:
            self.lib.sync()
        self._fingerprint = self.lib.fingerprint()
        items = self.lib.visible_items()
        open_ids = self.lib.open_item_ids()

        entries = [(item, self._category(item)) for item in items]
        counts = Counter(cat.key for _, cat in entries)
        self.filters.set_options([(k, CATEGORIES[k].plural, counts[k]) for k in FILTER_ORDER if counts[k]])
        chosen = self.filters.selected
        shown = [
            (item, cat) for item, cat in entries
            if (chosen == ALL or cat.key == chosen) and self._matches(item)
        ]
        reorder = not self.search_text and chosen == ALL

        self.header.set_count(f"{text.plural(len(items), 'item', 'itens')} no painel")
        if not items:
            self.cards.show_empty(
                "Seu painel está vazio",
                "Arraste arquivos para esta janela ou use o botão Adicionar. "
                "Planilhas, PDFs, documentos, fotos, pastas e até sites: tudo vira um cartão.",
                [("Adicionar arquivos", self._add_files, True),
                 ("Abrir a pasta do painel", self._open_files_folder, False)],
            )
        elif not shown:
            self.cards.show_empty(
                "Nada encontrado",
                f"Nenhum cartão combina com “{self.search_text}”." if self.search_text
                else "Nenhum cartão deste tipo.",
                [("Limpar a busca", self.header.clear_search, False)],
            )
        else:
            self.cards.show([self._card_data(i, c, open_ids) for i, c in shown], reorder_enabled=reorder)
        self.filters.set_hint_visible(reorder and len(shown) > 1)
        self.refresh_backup_bar()
        if len(self._images) > 300:
            self._images.clear()

    def _category(self, item: Item) -> FileCategory:
        path = self.lib.path_of(item)
        return category_for(item.target, is_dir=bool(path and path.is_dir()),
                            is_link=item.kind is ItemKind.LINK)

    def _matches(self, item: Item) -> bool:
        if not self.search_text:
            return True
        hay = text.fold(" ".join((item.name, item.description, Path(item.target).name)))
        return all(part in hay for part in text.fold(self.search_text).split())

    def _card_data(self, item: Item, cat: FileCategory, open_ids: set[str]) -> CardData:
        path = self.lib.path_of(item)
        is_link = item.kind is ItemKind.LINK
        exists = is_link or bool(path and path.exists())
        is_dir = bool(path and exists and path.is_dir())

        badges: list[tuple[str, str]] = []
        if item.id in open_ids:
            badges.append(("open", "Aberto agora"))
        if not exists:
            badges.append(("missing", "Não encontrado"))
        elif item.kind is ItemKind.LINKED:
            badges.append(("linked", "Atalho"))

        photo_path = self.lib.image_path(item)
        try:
            photo_mtime = photo_path.stat().st_mtime if photo_path else 0.0
        except OSError:
            photo_mtime = 0.0
        badge = badge_for(item.target, is_dir=is_dir, is_link=is_link)
        state = (item.id, item.image, photo_mtime, item.color, cat.key, badge, tuple(badges), exists)

        def image_for(size: tuple[int, int]) -> ctk.CTkImage:
            key = (*state, size)
            image = self._images.get(key)
            if image is None:
                base = art.photo(photo_path, size) if photo_path else None
                if base is None:
                    base = art.cover(item.color or cat.color, badge, size)
                image = art.card_image(base, size, badges=tuple(badges), dimmed=not exists)
                self._images[key] = image
            return image

        if is_link:
            line1 = item.description or "Site"
            line2 = urlparse(item.target).netloc
        else:
            line1 = item.description or cat.label
            line2 = self._file_detail(path, exists, is_dir)
        return CardData(item.id, text.shorten(item.name, 48), text.shorten(line1, 60), line2, image_for)

    def _file_detail(self, path: Path | None, exists: bool, is_dir: bool) -> str:
        if path is None:
            return ""
        if not exists:
            return text.shorten(f"Procurado em {path.parent}", 44)
        try:
            if is_dir:
                n = sum(1 for p in path.iterdir() if not is_ignored(p))
                return f"Pasta com {text.plural(n, 'item', 'itens')}"
            return f"Última edição {text.when(datetime.fromtimestamp(path.stat().st_mtime))}"
        except OSError:
            return ""

    # ------------------------------------------------------------------ barra de backup
    def refresh_backup_bar(self) -> None:
        if self._backup_running():
            return
        self._history_mtime = self.panel.history.mtime()
        s = self.panel.settings
        last = self.panel.history.last()
        nxt = self.panel.next_scheduled_backup()
        schedule = (f"Próximo automático {text.when_next(nxt)}." if nxt
                    else "Backup automático desligado.")
        action = None
        color = None

        if last is None:
            dot, line1, line2 = C["muted"], "Nenhum backup feito ainda", schedule
        elif last.status == BackupStatus.FAILED.value:
            dot = C["danger"]
            line1 = f"O último backup não deu certo ({text.when(datetime.fromisoformat(last.started_at))})"
            line2, color = last.error, C["danger"]
        else:
            started = datetime.fromisoformat(last.started_at)
            line1 = (f"Último backup {text.when(started)}: "
                     f"{text.plural(last.file_count, 'arquivo', 'arquivos')}, {text.size(last.size_bytes)}")
            if last.cloud_path:
                dot = C["ok"]
                line2 = f"Cópia na nuvem em {text.path_tail(Path(last.cloud_path).parent)}. {schedule}"
            else:
                dot = C["warn"]
                line2 = (last.warnings[0] if last.warnings else "Ficou só neste computador.")
                color = C["warn"]

        if not s.backup_destination:
            line2 = "Os backups estão ficando só neste computador."
            color = C["warn"]
            action = ("Escolher uma pasta na nuvem", lambda: self.open_settings("Backup"))
        elif last is not None and last.status == BackupStatus.FAILED.value:
            action = ("Ver configurações", lambda: self.open_settings("Backup"))
        self.backup_bar.show_status(dot, line1, line2, line2_color=color, action=action)

    # ================================================================== ações nos cartões
    def _item(self, item_id: str) -> Item | None:
        item = self.lib.get(item_id)
        if item is None:
            self.refresh()
        return item

    def open_item(self, item_id: str) -> None:
        item = self._item(item_id)
        if item is None:
            return
        try:
            if item.kind is ItemKind.LINK:
                opener.open_url(item.target)
            else:
                path = self.lib.path_of(item)
                if path is None or not path.exists():
                    message(self, "Arquivo não encontrado",
                            f"Não encontrei “{item.name}” em {path}.\n\n"
                            "Se ele mudou de lugar, use Editar no menu do cartão para mostrar onde está.")
                    return
                opener.open_path(path)
                self.toast.show(f"Abrindo “{item.name}”...", duration_ms=2500)
        except opener.OpenError as exc:
            message(self, "Não deu para abrir", str(exc))

    def _show_item_menu(self, item_id: str, event, anchor) -> None:
        item = self._item(item_id)
        if item is None:
            return
        items: list[MenuItem | None] = [MenuItem("Abrir", lambda: self.open_item(item_id))]
        if item.kind is not ItemKind.LINK:
            items.append(MenuItem("Mostrar na pasta", lambda: self._reveal(item)))
        items.append(MenuItem("Editar nome, foto e cor", lambda: self.edit_item(item_id)))
        if not self.search_text and self.filters.selected == ALL:
            items += [SEPARATOR,
                      MenuItem("Mover para o começo", lambda: self._reorder(item_id, 0)),
                      MenuItem("Mover para o fim",
                               lambda: self._reorder(item_id, len(self.lib.visible_items())))]
        items += [SEPARATOR, MenuItem("Remover do painel", lambda: self.remove_item(item_id), danger=True)]
        if event is not None and getattr(event, "x_root", None) is not None:
            x, y = event.x_root, event.y_root
        else:                                    # pelos três pontinhos: logo abaixo deles
            x, y = anchor.winfo_rootx() - 8, anchor.winfo_rooty() + anchor.winfo_height() + 4
        PopupMenu(self, items, title=text.shorten(item.name, 32)).popup(x, y)

    def edit_item(self, item_id: str) -> None:
        item = self._item(item_id)
        if item and EditItemDialog(self, self.panel, item).show():
            self.refresh(sync=False)
            self.toast.show("Cartão atualizado.")

    def remove_item(self, item_id: str) -> None:
        item = self._item(item_id)
        if item is None:
            return
        if item.kind is ItemKind.MANAGED:
            detail = ("O arquivo não é apagado: ele vai para a pasta Removidos, dentro da pasta "
                      "de dados do painel. Para trazer de volta, é só movê-lo de novo para a pasta Arquivos.")
        elif item.kind is ItemKind.LINKED:
            detail = "O arquivo original continua onde está. Só o atalho sai do painel."
        else:
            detail = "O site sai do painel."
        if not confirm(self, f"Remover “{item.name}”?", detail, ok="Remover do painel", danger=True):
            return
        try:
            self.lib.remove(item_id)
        except LibraryError as exc:
            message(self, "Não deu para remover", str(exc))
            return
        self.refresh()
        self.toast.show(f"“{text.shorten(item.name, 40)}” saiu do painel.")

    def _reorder(self, item_id: str, index: int) -> None:
        self.lib.move(item_id, index)
        self.refresh(sync=False)

    def _save_order(self, item_id: str, index: int) -> None:
        """Depois de arrastar: a grade já mostra a ordem nova, só falta gravar."""
        self.lib.move(item_id, index)

    def _reveal(self, item: Item) -> None:
        path = self.lib.path_of(item)
        if path is None:
            return
        try:
            opener.reveal(path)
        except opener.OpenError as exc:
            message(self, "Não deu para abrir a pasta", str(exc))

    # ================================================================== adicionar
    def _show_add_menu(self, button: ctk.CTkButton) -> None:
        PopupMenu(self, [MenuItem("Arquivos", self._add_files),
                         MenuItem("Uma pasta inteira", self._add_folder),
                         MenuItem("Um site", self._add_link)], width=200).popup(
            button.winfo_rootx(), button.winfo_rooty() + button.winfo_height() + 6)

    def _add_files(self) -> None:
        chosen = filedialog.askopenfilenames(parent=self, title="Escolha os arquivos para o painel")
        if chosen:
            self._add_paths([Path(p) for p in self.tk.splitlist(chosen)])

    def _add_folder(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title="Escolha a pasta para o painel", mustexist=True)
        if chosen:
            self._add_paths([Path(chosen)])

    def _add_paths(self, paths: list[Path]) -> None:
        files_dir = self.panel.paths.files.resolve()
        outside = [p for p in paths if p.resolve().parent != files_dir]
        mode = AddMode.MOVE
        if outside:
            mode = AddModeDialog(self, outside).show()
            if mode is None:
                return
        result = self.lib.add_paths(paths, mode=mode)
        self.refresh()
        if result.added:
            n = len(result.added)
            self.toast.show(f"{text.plural(n, 'item adicionado', 'itens adicionados')} ao painel.")
        if result.skipped:
            lines = "\n".join(f"• {name}: {why}" for name, why in result.skipped)
            message(self, "Alguns itens ficaram de fora", lines)

    def _on_files_dropped(self, paths: list[Path]) -> None:
        """Arquivos soltos do Explorer: copia para a pasta do painel e vira cartão."""
        files_dir = self.panel.paths.files.resolve()
        new = [p for p in paths
               if p.exists() and p.resolve() != files_dir and files_dir not in p.resolve().parents]
        if not new:
            self.toast.show("Esses arquivos já estão no painel.", "warn")
            return
        result = self.lib.add_paths(new, mode=AddMode.COPY)
        self.refresh()
        if result.added:
            n = len(result.added)
            self.toast.show(f"{text.plural(n, 'item copiado', 'itens copiados')} para a pasta do painel.")
        if result.skipped:
            lines = "\n".join(f"• {name}: {why}" for name, why in result.skipped)
            message(self, "Alguns itens ficaram de fora", lines)

    def _add_link(self) -> None:
        name = url = error = ""
        while True:
            answer = AddLinkDialog(self, name=name, url=url, error=error).show()
            if not answer:
                return
            name, url = answer
            try:
                self.lib.add_link(name, url)
            except LibraryError as exc:
                error = str(exc)
                continue
            break
        self.refresh(sync=False)
        self.toast.show("Site adicionado ao painel.")

    # ================================================================== backup
    def _backup_running(self) -> bool:
        return self._backup_thread is not None and self._backup_thread.is_alive()

    def start_backup(self, trigger: BackupTrigger = BackupTrigger.MANUAL, *, ask_open: bool = True) -> None:
        if self._backup_running():
            return
        self.lib.sync()
        if not any(i.kind is not ItemKind.LINK for i in self.lib.visible_items()):
            self.toast.show("O painel ainda não tem arquivos para copiar.", "warn")
            return
        self._excel_summary = ""
        # pelo botão: antes de copiar, salva e fecha no Excel as planilhas do painel
        if ask_open and trigger is BackupTrigger.MANUAL and self.panel.open_spreadsheets():
            self._save_spreadsheets_then_backup(trigger)
            return
        self._backup_after_checks(trigger, ask_open)

    def _save_spreadsheets_then_backup(self, trigger: BackupTrigger) -> None:
        self.backup_bar.set_busy(True)
        self.backup_bar.show_progress(0, "Salvando e fechando as planilhas no Excel...")

        def work() -> None:
            try:
                self._queue.put(("excel", self.panel.save_and_close_spreadsheets()))
            except ExcelError as exc:
                self._queue.put(("excel_error", str(exc)))

        self._backup_thread = threading.Thread(target=work, name="excel", daemon=True)
        self._backup_thread.start()

        def wait() -> None:
            try:
                kind, result = self._queue.get_nowait()
            except queue.Empty:
                self.after(150, wait)
                return
            self._backup_thread = None
            self.backup_bar.set_busy(False)
            if kind == "excel_error":
                self.refresh_backup_bar()
                message(self, "Não deu para salvar as planilhas", result)
                return
            if result.saved:
                self._excel_summary = (
                    f"Salvei e fechei {text.plural(len(result.saved), 'planilha', 'planilhas')} no Excel."
                )
            self.lib.sync()
            self._backup_after_checks(trigger, ask_open=True)

        self.after(150, wait)

    def _backup_after_checks(self, trigger: BackupTrigger, ask_open: bool) -> None:
        if ask_open:
            open_ids = self.lib.open_item_ids()
            if open_ids:
                names = [i.name for i in self.lib.items if i.id in open_ids]
                first = (f"“{names[0]}” está aberto." if len(names) == 1
                         else "Estes itens estão abertos: " + ", ".join(f"“{n}”" for n in names) + ".")
                if not confirm(
                    self, "Tem arquivo aberto",
                    f"{first} O backup vai levar a última versão salva. "
                    "Se você mudou alguma coisa, salve antes de continuar.",
                    ok="Fazer backup mesmo assim",
                ):
                    self.refresh_backup_bar()
                    return

        items = self.panel.snapshot_items()
        self.backup_bar.set_busy(True)
        self.backup_bar.show_progress(0, "Preparando o backup...")

        def work() -> None:
            def progress(done: int, total: int, name: str) -> None:
                self._queue.put(("progress", done / max(total, 1), name))
            record = self.panel.run_backup(trigger, progress, items=items)
            self._queue.put(("done", record))

        self._backup_thread = threading.Thread(target=work, name="backup", daemon=True)
        self._backup_thread.start()
        self.after(100, self._pump_backup)

    def _pump_backup(self) -> None:
        last_progress = None
        try:
            while True:
                msg = self._queue.get_nowait()
                if msg[0] == "progress":
                    last_progress = msg
                else:
                    self._backup_thread = None
                    self.backup_bar.set_busy(False)
                    self._after_backup(msg[1])
                    return
        except queue.Empty:
            pass
        if last_progress:
            _, frac, name = last_progress
            label = f"Copiando {Path(name).name}" if name else "Conferindo o backup..."
            self.backup_bar.show_progress(frac, text.shorten(label, 70))
        self.after(100, self._pump_backup)

    def _after_backup(self, rec: BackupRecord) -> None:
        self.refresh_backup_bar()
        if rec.status == BackupStatus.OK.value:
            done = "Backup feito e copiado para a nuvem." if rec.cloud_path else "Backup feito."
            self.toast.show(f"{self._excel_summary} {done}".strip())
        elif rec.status == BackupStatus.WARNING.value:
            warning = rec.warnings[0] if rec.warnings else "Backup feito, com avisos."
            self.toast.show(f"{self._excel_summary} {warning}".strip(), "warn", duration_ms=9000)
        else:
            message(self, "O backup não deu certo",
                    f"{rec.error}\n\nNenhum arquivo seu foi alterado. Tente de novo em instantes.")

    def _view_backups(self) -> None:
        dest = self.panel.settings.backup_destination
        folder = Path(dest) if dest and Path(dest).is_dir() else self.panel.paths.backups
        try:
            opener.open_path(folder)
        except opener.OpenError as exc:
            message(self, "Não deu para abrir", str(exc))

    # ================================================================== outros
    def open_settings(self, tab: str = "Backup") -> None:
        if SettingsDialog(self, self.panel, tab=tab).show():
            s = self.panel.settings
            ctk.set_appearance_mode(theme.APPEARANCE.get(s.theme, "system"))
            style_titlebar(self)
            self.title(s.panel_name)
            self.header.set_title(s.panel_name)
            self.refresh(sync=False)
            self.toast.show("Configurações salvas.")

    def _open_files_folder(self) -> None:
        try:
            opener.open_path(self.panel.paths.files)
        except opener.OpenError as exc:
            message(self, "Não deu para abrir", str(exc))

    def _on_search(self, value: str) -> None:
        value = value.strip()
        if value != self.search_text:
            self.search_text = value
            self.refresh(sync=False)

    def _poll(self) -> None:
        """Confere de tempos em tempos se algo mudou na pasta ou nos backups."""
        try:
            if self.cards._drag is None:
                if self.lib.fingerprint() != self._fingerprint:
                    self.refresh()
                elif self.panel.history.mtime() != self._history_mtime:
                    self.refresh_backup_bar()     # o backup automático rodou por fora
        except Exception:  # noqa: BLE001
            log.exception("Falha ao conferir a pasta")
        finally:
            self.after(POLL_MS, self._poll)

    def _startup_tasks(self) -> None:
        threading.Thread(target=self.panel.refresh_schedule_quietly, daemon=True).start()
        threading.Thread(target=self._check_update, name="atualizacao", daemon=True).start()
        if self.panel.backup_is_overdue() and self.lib.visible_items():
            self.toast.show("Fazendo o backup da semana...", duration_ms=4000)
            self.start_backup(BackupTrigger.ON_OPEN, ask_open=False)

    # ------------------------------------------------------------------ atualização
    def _check_update(self) -> None:
        """Roda em segundo plano: pergunta ao GitHub se tem versão nova."""
        try:
            info = self.panel.check_update()
        except Exception:  # noqa: BLE001  (sem atualização não é problema)
            log.exception("Falha ao procurar atualização")
            return
        if info:
            self.after(0, lambda: self._offer_update(info))

    def _offer_update(self, info) -> None:
        self._update_info = info
        self.update_bar.show_version(info.version, info.notes)
        self.update_bar.grid(row=1, column=0, sticky="ew")

    def _install_update(self) -> None:
        info = self._update_info
        if info is None:
            return
        if self._backup_running():
            self.toast.show("Espere o backup terminar para atualizar.", "warn")
            return
        if not confirm(self, "Atualizar o painel",
                       f"O painel vai baixar a versão {info.version}, fechar e abrir de novo sozinho. "
                       "Seus arquivos e configurações continuam iguais.", ok="Atualizar"):
            return
        self.update_bar.set_busy(True)
        progress_q: queue.Queue = queue.Queue()

        def work() -> None:
            try:
                path = self.panel.download_update(info, lambda f: progress_q.put(("progress", f)))
                progress_q.put(("done", path))
            except UpdateError as exc:
                progress_q.put(("error", str(exc)))

        threading.Thread(target=work, name="baixar", daemon=True).start()

        def pump() -> None:
            try:
                while True:
                    kind, value = progress_q.get_nowait()
                    if kind == "progress":
                        self.update_bar.show_progress(value)
                    elif kind == "error":
                        self.update_bar.show_version(info.version, info.notes)
                        message(self, "Não deu para atualizar", value)
                        return
                    else:
                        self._finish_update(value)
                        return
            except queue.Empty:
                pass
            self.after(100, pump)

        self.after(100, pump)

    def _finish_update(self, new_exe: Path) -> None:
        try:
            self.panel.install_update(new_exe)
        except UpdateError as exc:
            self.update_bar.show_version(self._update_info.version, self._update_info.notes)
            message(self, "Não deu para atualizar", str(exc))
            return
        log.info("Atualizando para a versão %s", self._update_info.version)
        self._on_close()

    # ------------------------------------------------------------------ janela
    def _restore_geometry(self) -> None:
        geo = self.panel.settings.window_geometry
        w, h = DEFAULT_SIZE
        if geo:
            try:
                size, _, pos = geo.partition("+")
                w, h = (int(v) for v in size.split("x"))
                x, y = (int(v) for v in pos.split("+"))
                if 0 <= x < self.winfo_screenwidth() - 100 and 0 <= y < self.winfo_screenheight() - 100:
                    self.geometry(f"{w}x{h}+{x}+{y}")
                    return
            except ValueError:
                pass
        self.geometry(f"{w}x{h}")

    def _on_close(self) -> None:
        if self._backup_running():
            self.toast.show("Espere o backup terminar para fechar o painel.", "warn")
            return
        try:
            self.panel.save_window_geometry(self.geometry())
        except Exception:  # noqa: BLE001
            log.exception("Não foi possível guardar o tamanho da janela")
        self.destroy()

    def report_callback_exception(self, exc, val, tb) -> None:  # noqa: D401
        log.error("Erro na tela", exc_info=(exc, val, tb))
        try:
            message(self, "Algo deu errado",
                    f"{val}\n\nO detalhe foi salvo nos registros do painel "
                    "(Configurações > Painel > Abrir os registros).")
        except Exception:  # noqa: BLE001
            pass


def run_app(panel: Panel | None = None) -> None:
    from app import single_instance
    from app.logging_setup import setup_logging

    panel = panel or Panel()
    setup_logging(panel.paths.logs)
    if single_instance.already_running(str(panel.paths.root)):
        single_instance.bring_to_front(panel.settings.panel_name)
        return
    if os.name == "nt":
        try:   # faz a barra de tarefas mostrar o ícone do painel
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    theme.apply_theme(panel.settings.theme)
    log.info("Painel aberto (dados em %s)", panel.paths.root)
    MainWindow(panel).mainloop()
