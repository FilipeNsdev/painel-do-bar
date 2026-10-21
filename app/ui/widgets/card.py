"""Cartão de um item do painel: foto (ou capa colorida), nome e detalhes.

Clique abre o arquivo. Botão direito (ou o botão "···") abre o menu.
Arrastar muda a ordem: quem cuida disso é a grade (CardGrid), o cartão só
avisa que foi pressionado, arrastado ou solto.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import customtkinter as ctk

from app.ui import theme
from app.ui.theme import C


@dataclass
class CardData:
    """Tudo que o cartão precisa mostrar, já calculado pela janela."""

    item_id: str
    title: str
    line1: str
    line2: str
    image_for: Callable[[tuple[int, int]], ctk.CTkImage]   # imagem da capa no tamanho pedido


class Card(ctk.CTkFrame):
    def __init__(
        self,
        master,
        data: CardData,
        width: int,
        *,
        on_press: Callable[["Card", object], None],
        on_drag: Callable[["Card", object], None],
        on_release: Callable[["Card", object], None],
        on_menu: Callable[["Card", object], None],
    ):
        super().__init__(
            master,
            corner_radius=theme.RADIUS_CARD,
            border_width=2,
            border_color=C["surface"],      # contorno invisível: só aparece no realce
            fg_color=C["surface"],
            cursor="hand2",
        )
        self.data = data
        self.item_id = data.item_id
        self.card_width = 0
        self._highlight = False

        p = theme.CARD_PAD
        self.cover = ctk.CTkLabel(self, text="", cursor="hand2")
        self.cover.grid(row=0, column=0, columnspan=2, padx=p, pady=(p, 8), sticky="w")

        self.title_label = ctk.CTkLabel(
            self, text=data.title, font=theme.font(15, "bold"), text_color=C["text"],
            anchor="w", justify="left", height=22, cursor="hand2",
        )
        self.title_label.grid(row=1, column=0, padx=(p + 2, 0), sticky="nw")

        self.more = ctk.CTkButton(
            self, text="···", width=32, height=26, font=theme.font(15, "bold"),
            fg_color="transparent", hover_color=C["chip"], text_color=C["muted"],
            command=lambda: on_menu(self, None),
        )
        self.more.grid(row=1, column=1, padx=(0, p - 2), sticky="ne")

        self.meta1 = ctk.CTkLabel(
            self, text=data.line1, font=theme.font(12), text_color=C["muted"], anchor="w",
            justify="left", height=18, cursor="hand2",
        )
        self.meta1.grid(row=2, column=0, columnspan=2, padx=(p + 2, p), pady=(4, 0), sticky="w")
        self.meta2 = ctk.CTkLabel(
            self, text=data.line2, font=theme.font(12), text_color=C["muted"], anchor="w",
            height=18, cursor="hand2",
        )
        self.meta2.grid(row=3, column=0, columnspan=2, padx=(p + 2, p), pady=(0, p + 4), sticky="w")
        self.grid_columnconfigure(0, weight=1)
        self.set_width(width)

        for w in (self, self.cover, self.title_label, self.meta1, self.meta2):
            w.bind("<ButtonPress-1>", lambda e: on_press(self, e))
            w.bind("<B1-Motion>", lambda e: on_drag(self, e))
            w.bind("<ButtonRelease-1>", lambda e: on_release(self, e))
            w.bind("<Button-3>", lambda e: on_menu(self, e))
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def set_width(self, width: int) -> None:
        """Ajusta o cartão à largura da coluna (a grade chama ao redimensionar)."""
        if width == self.card_width:
            return
        self.card_width = width
        self.cover.configure(image=self.data.image_for(theme.cover_size(width)))
        inner = width - 2 * theme.CARD_PAD
        self.title_label.configure(wraplength=inner - 34)
        self.meta1.configure(wraplength=inner)

    # ------------------------------------------------------------------ realce
    def _on_enter(self, _e=None) -> None:
        if not self._highlight:
            self.configure(border_color=C["text"])

    def _on_leave(self, _e=None) -> None:
        if self._highlight:
            return
        # o <Leave> também dispara ao passar para um filho: confere se o mouse saiu mesmo
        x, y = self.winfo_pointerxy()
        inside = (self.winfo_rootx() <= x < self.winfo_rootx() + self.winfo_width()
                  and self.winfo_rooty() <= y < self.winfo_rooty() + self.winfo_height())
        if not inside:
            self.configure(border_color=C["surface"])

    def set_drop_target(self, on: bool) -> None:
        """Realce de 'solte aqui' durante o arrasto."""
        self._highlight = on
        self.configure(border_color=C["accent"] if on else C["surface"])

    def set_dragging(self, on: bool) -> None:
        self.configure(fg_color=C["chip"] if on else C["surface"],
                       border_color=C["chip"] if on else C["surface"])
