"""Faixa logo abaixo do cabeçalho que avisa quando tem versão nova do painel."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import text, theme
from app.ui.theme import C


class UpdateBar(ctk.CTkFrame):
    def __init__(self, master, *, on_update: Callable[[], None], on_later: Callable[[], None]):
        super().__init__(master, corner_radius=0, fg_color=C["toast"])
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=26, pady=10)
        body.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(body, text="", font=theme.font(13), text_color=C["on_toast"],
                                  anchor="w", justify="left", height=20)
        self.label.grid(row=0, column=0, sticky="w")
        self.later = theme.link_button(body, "Depois", on_later, color=C["on_toast"])
        self.later.grid(row=0, column=1, padx=(16, 14))
        self.button = theme.primary_button(body, "Atualizar agora", on_update, width=150)
        self.button.grid(row=0, column=2)

    def show_version(self, version: str, notes: str) -> None:
        line = f"Versão {version} disponível."
        if notes:
            line += f" {text.shorten(notes, 110)}"
        self.label.configure(text=line)
        self.set_busy(False)

    def show_progress(self, fraction: float) -> None:
        self.label.configure(text=f"Baixando a versão nova... {round(fraction * 100)}%")

    def set_busy(self, busy: bool) -> None:
        self.button.configure(state="disabled" if busy else "normal",
                              text="Atualizando..." if busy else "Atualizar agora")
        if busy:
            self.later.grid_remove()
        else:
            self.later.grid()
