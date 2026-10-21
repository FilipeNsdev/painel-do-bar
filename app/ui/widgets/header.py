"""Cabeçalho do painel: faixa vermelha em cima, a logo do bar, o nome, a
busca e os botões de adicionar e de configurações."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import art, theme
from app.ui.theme import C


class Header(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        on_search: Callable[[str], None],
        on_add: Callable[[ctk.CTkButton], None],
        on_settings: Callable[[], None],
        on_open_folder: Callable[[], None],
    ):
        super().__init__(master, corner_radius=0, fg_color=C["surface"])
        self._on_search = on_search
        self._search_job: str | None = None

        self.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(self, height=3, corner_radius=0, fg_color=C["accent"]).grid(
            row=0, column=0, columnspan=3, sticky="ew")

        logo = ctk.CTkLabel(self, text="", image=art.logo_image(56))
        logo.grid(row=1, column=0, rowspan=2, padx=(26, 14), pady=(14, 16), sticky="w")

        self.title_label = ctk.CTkLabel(
            self, text="", font=theme.title_font(26), text_color=C["text"], anchor="w", height=34
        )
        self.title_label.grid(row=1, column=1, sticky="sw", pady=(14, 0))

        sub = ctk.CTkFrame(self, fg_color="transparent")
        sub.grid(row=2, column=1, sticky="nw", pady=(0, 16))
        self.count = ctk.CTkLabel(sub, text="", font=theme.font(13), text_color=C["muted"], height=20)
        self.count.pack(side="left")
        theme.link_button(sub, "Abrir a pasta do painel", on_open_folder,
                          color=C["muted"]).pack(side="left", padx=(12, 0))

        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.grid(row=1, column=2, rowspan=2, padx=(12, 26), sticky="e")

        self.search = ctk.CTkEntry(
            tools, placeholder_text="Buscar no painel",
            width=230, height=theme.CONTROL_HEIGHT, font=theme.font(13), border_width=0,
            fg_color=C["field"], text_color=C["text"], placeholder_text_color=C["muted"],
        )
        self.search.pack(side="left", padx=(0, 10))
        self.search.bind("<KeyRelease>", lambda _e: self._debounce())
        self.search.bind("<Escape>", lambda _e: self.clear_search())

        self.add_button = theme.primary_button(tools, "Adicionar", lambda: on_add(self.add_button), width=112)
        self.add_button.pack(side="left", padx=(0, 8))
        theme.secondary_button(tools, "Configurações", on_settings, width=124).pack(side="left")
        self.bind("<Configure>", self._fit, add="+")

    def _fit(self, event) -> None:
        """Encolhe a busca em janelas estreitas para o nome e o link caberem."""
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        width = int(max(130, min(260, event.width / scale - 640)))
        if int(self.search.cget("width")) != width:
            self.search.configure(width=width)

    def _debounce(self) -> None:
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(160, lambda: self._on_search(self.search.get()))

    def set_title(self, text: str) -> None:
        self.title_label.configure(text=text)

    def set_count(self, text: str) -> None:
        self.count.configure(text=text)

    def focus_search(self) -> None:
        self.search.focus_set()

    def clear_search(self) -> None:
        self.search.delete(0, "end")
        self.focus_set()              # tira o foco para o texto de exemplo voltar
        self._on_search("")
