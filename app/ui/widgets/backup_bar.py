"""Barra de backup no rodapé: como foi o último backup, para onde foi,
quando é o próximo e o botão para fazer agora."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import theme
from app.ui.theme import C


class BackupBar(ctk.CTkFrame):
    def __init__(self, master, *, on_backup: Callable[[], None], on_view: Callable[[], None]):
        super().__init__(master, corner_radius=0, fg_color=C["surface"])

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=26, pady=16)
        body.grid_columnconfigure(1, weight=1)

        self.dot = ctk.CTkFrame(body, width=12, height=12, corner_radius=6, fg_color=C["muted"])
        self.dot.grid(row=0, column=0, padx=(0, 12), pady=(4, 0), sticky="n")

        info = ctk.CTkFrame(body, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew")
        self.line1 = ctk.CTkLabel(info, text="", font=theme.font(13, "bold"), anchor="w", justify="left",
                                  height=20)
        self.line1.pack(anchor="w")
        self.detail = ctk.CTkFrame(info, fg_color="transparent")
        self.detail.pack(anchor="w", fill="x")
        self.line2 = ctk.CTkLabel(self.detail, text="", font=theme.font(12), text_color=C["muted"],
                                  anchor="w", justify="left", wraplength=640, height=18)
        self.line2.pack(side="left")
        self.action = theme.link_button(self.detail, "", lambda: None)
        self.progress = ctk.CTkProgressBar(info, height=6, width=360)
        self.progress.set(0)

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=0, column=2, padx=(16, 0), sticky="e")
        self.view_button = theme.secondary_button(buttons, "Ver backups", on_view, width=110)
        self.view_button.pack(side="left", padx=(0, 8))
        self.backup_button = theme.primary_button(buttons, "Fazer backup agora", on_backup, width=168)
        self.backup_button.pack(side="left")

        self.bind("<Configure>", self._wrap)

    def _wrap(self, event) -> None:
        # sobra para o texto: largura menos os botões, a bolinha e as margens
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        room = event.width / scale - 400
        self.line2.configure(wraplength=max(260, room))

    def show_status(
        self,
        dot: tuple[str, str] | str,
        line1: str,
        line2: str,
        *,
        line2_color: tuple[str, str] | str | None = None,
        action: tuple[str, Callable[[], None]] | None = None,
    ) -> None:
        self.progress.pack_forget()
        self.detail.pack(anchor="w", fill="x")
        self.dot.configure(fg_color=dot)
        self.line1.configure(text=line1)
        self.line2.configure(text=line2, text_color=line2_color or C["muted"])
        if action:
            self.action.configure(text=action[0], command=action[1],
                                  text_color=line2_color or C["text"])
            self.action.pack(side="left", padx=(8, 0))
        else:
            self.action.pack_forget()

    def show_progress(self, fraction: float, text: str) -> None:
        if not self.progress.winfo_ismapped():
            self.detail.pack_forget()
            self.progress.pack(anchor="w", pady=(6, 2))
        self.dot.configure(fg_color=C["accent"])
        self.line1.configure(text=text)
        self.progress.set(max(0.0, min(1.0, fraction)))

    def set_busy(self, busy: bool) -> None:
        self.backup_button.configure(
            state="disabled" if busy else "normal",
            text="Fazendo backup..." if busy else "Fazer backup agora",
        )
