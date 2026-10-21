"""Filtros por tipo ("Tudo", "Planilhas", "PDFs"...) logo abaixo do cabeçalho.

Só aparecem os tipos que existem no painel, cada um com a quantidade.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import theme
from app.ui.theme import C

ALL = "tudo"


class FilterBar(ctk.CTkFrame):
    def __init__(self, master, *, on_change: Callable[[str], None]):
        super().__init__(master, fg_color="transparent")
        self._on_change = on_change
        self._selected = ALL
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._current_options: list[tuple[str, str, int]] = []

        self.chips = ctk.CTkFrame(self, fg_color="transparent")
        self.chips.pack(side="left")
        self.hint = ctk.CTkLabel(
            self, text="Arraste um cartão para mudar a ordem.",
            font=theme.font(12), text_color=C["muted"],
        )
        self.hint.pack(side="right")
        self._hint_wanted = True
        self.bind("<Configure>", lambda _e: self.after_idle(self._fit_hint), add="+")

    @property
    def selected(self) -> str:
        return self._selected

    def set_options(self, options: list[tuple[str, str, int]]) -> None:
        """options: (chave, rótulo, quantidade). Recria os botões só se mudou."""
        keys = {k for k, _, _ in options}
        if self._selected != ALL and self._selected not in keys:
            self._selected = ALL
        if options == self._current_options:
            self._paint()
            return
        self._current_options = options
        for b in self._buttons.values():
            b.destroy()
        self._buttons.clear()
        if len(options) < 2:     # um tipo só: filtro não ajuda em nada
            return
        total = sum(n for _, _, n in options)
        for key, label, n in [(ALL, "Tudo", total), *options]:
            b = ctk.CTkButton(
                self.chips, text=f"{label}  {n}", height=32, width=0, corner_radius=16,
                font=theme.font(12), border_spacing=10,
                command=lambda k=key: self._select(k),
            )
            b.pack(side="left", padx=(0, 6))
            self._buttons[key] = b
        self._paint()

    def set_hint_visible(self, visible: bool) -> None:
        self._hint_wanted = visible
        self._fit_hint()

    def _fit_hint(self) -> None:
        """Mostra a dica só se ela couber ao lado dos filtros."""
        room = self.winfo_width() - self.chips.winfo_reqwidth() - 24
        show = self._hint_wanted and self.hint.winfo_reqwidth() <= room
        if show and not self.hint.winfo_ismapped():
            self.hint.pack(side="right")
        elif not show and self.hint.winfo_ismapped():
            self.hint.pack_forget()

    def _select(self, key: str) -> None:
        self._selected = key
        self._paint()
        self._on_change(key)

    def _paint(self) -> None:
        for key, b in self._buttons.items():
            on = key == self._selected
            b.configure(
                fg_color=C["text"] if on else C["chip"],
                hover_color=C["text"] if on else C["chip_hover"],
                text_color=C["surface"] if on else C["text"],
            )
