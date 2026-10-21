"""Configurações: para onde vai o backup, backup automático e o painel em si."""

from __future__ import annotations

import os
from tkinter import filedialog

import customtkinter as ctk

from app import APP_NAME, __version__
from app.core import opener, scheduler, shortcuts
from app.core.cloud import detect_cloud_folders
from app.core.models import WEEKDAYS, Settings
from app.core.panel import Panel
from app.ui import theme
from app.ui.dialogs.base import Dialog, message, style_titlebar
from app.ui.theme import C

KEEP_OPTIONS = ["5", "10", "15", "20", "30", "52"]
HOURS = [f"{h:02d}" for h in range(24)]
MINUTES = ["00", "15", "30", "45"]
APPEARANCE = {"Automática": "auto", "Clara": "claro", "Escura": "escuro"}


class SettingsDialog(Dialog):
    """Devolve True se algo foi salvo."""

    def __init__(self, master, panel: Panel, *, tab: str = "Backup"):
        super().__init__(master, "Configurações", width=540)
        self.panel = panel
        self.s = Settings.from_dict(panel.settings.to_dict())     # cópia para editar
        self.destination = self.s.backup_destination

        # abas simples: botões em cima, um quadro para cada aba
        bar = ctk.CTkFrame(self.content, fg_color="transparent")
        bar.pack(anchor="w", pady=(0, 10))
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.tab_buttons: dict[str, ctk.CTkButton] = {}
        for name, build in (("Backup", self._build_backup), ("Painel", self._build_panel)):
            b = ctk.CTkButton(bar, text=name, height=32, width=96, corner_radius=16,
                              font=theme.font(13), command=lambda n=name: self._show_tab(n))
            b.pack(side="left", padx=(0, 6))
            self.tab_buttons[name] = b
            page = ctk.CTkFrame(self.content, corner_radius=theme.RADIUS_CARD, fg_color=C["surface"],
                                border_width=0, width=self.width, height=476)
            page.pack_propagate(False)
            build(page)
            self.pages[name] = page
        self._show_tab(tab)
        self.add_buttons("Salvar", self._save)

    def _show_tab(self, name: str) -> None:
        for n, page in self.pages.items():
            page.pack_forget()
            on = n == name
            self.tab_buttons[n].configure(
                fg_color=C["text"] if on else C["chip"],
                hover_color=C["text"] if on else C["chip_hover"],
                text_color=C["surface"] if on else C["text"],
            )
        self.pages[name].pack(fill="both", expand=True)

    # ------------------------------------------------------------------ helpers de layout
    @staticmethod
    def _heading(parent, text: str, top: int = 6) -> None:
        ctk.CTkLabel(parent, text=text, font=theme.font(15, "bold"), anchor="w").pack(
            anchor="w", padx=18, pady=(top + 10, 2))

    def _note(self, parent, text: str, color=None, pady=(0, 8)) -> ctk.CTkLabel:
        label = ctk.CTkLabel(parent, text=text, font=theme.font(12), text_color=color or C["muted"],
                             justify="left", anchor="w", wraplength=self.width - 60)
        label.pack(anchor="w", padx=18, pady=pady)
        return label

    # ------------------------------------------------------------------ aba Backup
    def _build_backup(self, tab) -> None:
        self._heading(tab, "Pasta na nuvem")
        self._note(tab, "Cada backup é copiado para esta pasta. O app do Google Drive "
                        "(ou OneDrive) se encarrega de enviar para a nuvem.")

        box = ctk.CTkFrame(tab, fg_color=C["field"], corner_radius=theme.RADIUS_CONTROL, border_width=0)
        box.pack(fill="x", padx=18, pady=(0, 6))
        self.dest_label = ctk.CTkLabel(box, text="", font=theme.font(12), anchor="w", justify="left",
                                       wraplength=self.width - 190)
        self.dest_label.pack(side="left", fill="x", expand=True, padx=12, pady=9)
        theme.secondary_button(box, "Escolher pasta...", self._choose_destination, width=130,
                               height=30).pack(side="right", padx=6, pady=6)

        clouds = detect_cloud_folders()
        quick = ctk.CTkFrame(tab, fg_color="transparent")
        quick.pack(fill="x", padx=18, pady=(0, 4))
        if clouds:
            ctk.CTkLabel(quick, text="Encontrei neste computador:", font=theme.font(12),
                         text_color=C["muted"]).pack(side="left", padx=(0, 6))
            for cloud in clouds[:3]:
                theme.link_button(quick, f"Usar {cloud.label}",
                                  lambda p=cloud.suggested_destination: self._set_destination(str(p))
                                  ).pack(side="left", padx=(0, 10))
        else:
            ctk.CTkLabel(quick, text="Não encontrei Google Drive nem OneDrive neste computador. "
                                     "Instale o Google Drive para computador e entre na sua conta.",
                         font=theme.font(12), text_color=C["muted"], justify="left",
                         wraplength=self.width - 60).pack(anchor="w")
        self._refresh_destination()

        keep = ctk.CTkFrame(tab, fg_color="transparent")
        keep.pack(fill="x", padx=18, pady=(8, 2))
        ctk.CTkLabel(keep, text="Guardar os últimos", font=theme.font(13)).pack(side="left")
        values = sorted(set(KEEP_OPTIONS) | {str(self.s.backup_keep)}, key=int)
        self.keep_var = ctk.StringVar(value=str(self.s.backup_keep))
        ctk.CTkOptionMenu(keep, values=values, variable=self.keep_var, width=70, height=30,
                          font=theme.font(13)).pack(side="left", padx=8)
        ctk.CTkLabel(keep, text="backups (os mais antigos são apagados)", font=theme.font(13)).pack(side="left")

        ctk.CTkFrame(tab, height=1, fg_color=C["border"]).pack(fill="x", padx=18, pady=(16, 10))
        self._heading(tab, "Backup automático", top=0)

        supported = scheduler.is_supported()
        self.weekly_var = ctk.BooleanVar(value=self.s.weekly_enabled)
        theme.switch(tab, text="Fazer backup toda semana", variable=self.weekly_var,
                      font=theme.font(13), state="normal" if supported else "disabled",
                      command=self._paint_weekly).pack(anchor="w", padx=18, pady=(4, 6))

        when = ctk.CTkFrame(tab, fg_color="transparent")
        when.pack(anchor="w", padx=18)
        self.day_var = ctk.StringVar(value=WEEKDAYS[self.s.weekly_day])
        hh, mm = (self.s.weekly_time.split(":") + ["00"])[:2]
        self.hour_var = ctk.StringVar(value=hh.zfill(2))
        self.min_var = ctk.StringVar(value=mm if mm in MINUTES else "00")
        self.day_menu = ctk.CTkOptionMenu(when, values=WEEKDAYS, variable=self.day_var, width=120,
                                          height=30, font=theme.font(13))
        self.day_menu.pack(side="left")
        ctk.CTkLabel(when, text="às", font=theme.font(13)).pack(side="left", padx=8)
        self.hour_menu = ctk.CTkOptionMenu(when, values=HOURS, variable=self.hour_var, width=64,
                                           height=30, font=theme.font(13))
        self.hour_menu.pack(side="left")
        ctk.CTkLabel(when, text=":", font=theme.font(13)).pack(side="left", padx=3)
        self.min_menu = ctk.CTkOptionMenu(when, values=MINUTES, variable=self.min_var, width=64,
                                          height=30, font=theme.font(13))
        self.min_menu.pack(side="left")

        if supported:
            self._note(tab, "Se o computador estiver desligado nesse horário, o backup roda "
                            "assim que ele for ligado.", pady=(6, 6))
        else:
            self._note(tab, "O backup automático só funciona no Windows.", pady=(6, 6))

        self.overdue_var = ctk.BooleanVar(value=self.s.backup_on_open_if_overdue)
        theme.switch(tab, text=f"Ao abrir o painel, fazer backup se o último tiver mais de "
                                f"{self.s.backup_overdue_days} dias",
                      variable=self.overdue_var, font=theme.font(13)).pack(anchor="w", padx=18, pady=(2, 6))
        self.notify_var = ctk.BooleanVar(value=self.s.notify_after_auto_backup)
        theme.switch(tab, text="Mostrar um aviso quando o backup automático terminar",
                      variable=self.notify_var, font=theme.font(13)).pack(anchor="w", padx=18, pady=(0, 6))
        self._paint_weekly()

    def _paint_weekly(self) -> None:
        state = "normal" if self.weekly_var.get() and scheduler.is_supported() else "disabled"
        for menu in (self.day_menu, self.hour_menu, self.min_menu):
            menu.configure(state=state)

    def _refresh_destination(self) -> None:
        if self.destination:
            self.dest_label.configure(text=self.destination, text_color=C["text"])
        else:
            self.dest_label.configure(text="Nenhuma escolhida: os backups ficam só neste computador.",
                                      text_color=C["warn"])

    def _set_destination(self, path: str) -> None:
        self.destination = path
        self._refresh_destination()

    def _choose_destination(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title="Escolha a pasta da nuvem para os backups",
                                         initialdir=self.destination or None, mustexist=True)
        if chosen:
            self._set_destination(chosen)

    # ------------------------------------------------------------------ aba Painel
    def _build_panel(self, tab) -> None:
        self._heading(tab, "Nome do painel")
        self.name_entry = ctk.CTkEntry(tab, height=36, font=theme.font(13))
        self.name_entry.insert(0, self.s.panel_name)
        self.name_entry.pack(fill="x", padx=18, pady=(2, 12))

        self._heading(tab, "Aparência")
        reverse = {v: k for k, v in APPEARANCE.items()}
        self.appearance = ctk.CTkSegmentedButton(tab, values=list(APPEARANCE), font=theme.font(13),
                                                 height=32, command=self._change_theme)
        self.appearance.set(reverse.get(self.s.theme, "Automática"))
        self.appearance.pack(anchor="w", padx=18, pady=(4, 2))
        self._note(tab, "Muda na hora, sem precisar salvar.", pady=(0, 12))

        self._heading(tab, "Atalhos e pastas")
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(4, 4))
        if os.name == "nt":
            theme.secondary_button(row, "Criar atalho na Área de Trabalho", self._shortcut,
                                   width=240).pack(anchor="w", pady=(0, 10))
        paths = self.panel.paths
        for text, folder in (
            ("Abrir a pasta dos arquivos", paths.files),
            ("Abrir a pasta dos backups neste computador", paths.backups),
            ("Abrir a pasta Removidos", paths.removed),
            ("Abrir os registros (para suporte)", paths.logs),
        ):
            theme.link_button(row, text, lambda f=folder: self._open(f)).pack(anchor="w", pady=2)

        self._note(tab, f"{APP_NAME} {__version__}. Os dados ficam em {paths.root}", pady=(16, 0))

    def _change_theme(self, label: str) -> None:
        """Aplica e guarda a aparência assim que é escolhida (não espera o Salvar)."""
        value = APPEARANCE.get(label, "auto")
        self.s.theme = value                       # o Salvar depois não desfaz a escolha
        self.panel.set_theme(value)
        ctk.set_appearance_mode(theme.APPEARANCE[value])
        style_titlebar(self)
        style_titlebar(self.owner)

    def _shortcut(self) -> None:
        try:
            shortcuts.create_desktop_shortcut(self.name_entry.get().strip() or APP_NAME)
            message(self, "Atalho criado", "O atalho do painel está na sua Área de Trabalho.")
        except shortcuts.ShortcutError as exc:
            message(self, "Atalho não criado", str(exc))

    def _open(self, folder) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        try:
            opener.open_path(folder)
        except opener.OpenError as exc:
            message(self, "Não abriu", str(exc))

    # ------------------------------------------------------------------ salvar
    def _save(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            message(self, "Falta o nome", "Dê um nome ao painel. Ex.: Bar do Sabão.")
            return
        s = self.s
        s.panel_name = name
        s.theme = APPEARANCE.get(self.appearance.get(), "auto")
        s.backup_destination = self.destination
        s.backup_keep = int(self.keep_var.get())
        s.weekly_enabled = bool(self.weekly_var.get()) and scheduler.is_supported()
        s.weekly_day = WEEKDAYS.index(self.day_var.get())
        s.weekly_time = f"{self.hour_var.get()}:{self.min_var.get()}"
        s.backup_on_open_if_overdue = bool(self.overdue_var.get())
        s.notify_after_auto_backup = bool(self.notify_var.get())
        try:
            self.panel.save_settings(s)
        except scheduler.SchedulerError as exc:
            message(self, "Backup automático não ligado",
                    f"As outras configurações foram salvas, mas o Windows não aceitou "
                    f"agendar o backup.\n\n{exc}")
        self.close(True)
