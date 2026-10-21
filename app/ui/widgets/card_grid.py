"""Grade de cartões com rolagem, que se ajusta à largura da janela e deixa
mudar a ordem arrastando um cartão para cima de outro."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import art, theme
from app.ui.theme import C
from app.ui.widgets.card import Card, CardData

DRAG_THRESHOLD = 8   # pixels que o mouse precisa andar para virar arrasto
MARGIN = 26          # mesmo recuo do cabeçalho


class CardGrid(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master,
        *,
        on_open: Callable[[str], None],
        on_menu: Callable[[str, object, ctk.CTkBaseClass], None],
        on_reorder: Callable[[str, int], None],
    ):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.on_open = on_open
        self.on_menu = on_menu
        self.on_reorder = on_reorder
        self.reorder_enabled = True
        self.cards: list[Card] = []
        self._columns = 0
        self._card_width = theme.CARD_MIN_WIDTH
        self._resize_job: str | None = None
        self._drag: dict | None = None
        self._empty: ctk.CTkFrame | None = None
        self._parent_canvas.bind("<Configure>", self._on_resize, add="+")

    # ------------------------------------------------------------------ conteúdo
    def show(self, items: list[CardData], *, reorder_enabled: bool) -> None:
        self.reorder_enabled = reorder_enabled
        self._clear_empty()
        for card in self.cards:
            card.destroy()
        width = self._parent_canvas.winfo_width()
        if width > 1:
            self._columns, self._card_width = self._metrics(width)
        self.cards = [
            Card(self, data, self._card_width, on_press=self._press, on_drag=self._motion,
                 on_release=self._release, on_menu=self._menu)
            for data in items
        ]
        self._layout()

    def show_empty(self, title: str, text: str, actions: list[tuple[str, Callable[[], None], bool]]) -> None:
        """Tela vazia com orientação do que fazer. actions: (texto, comando, principal?)."""
        for card in self.cards:
            card.destroy()
        self.cards = []
        self._clear_empty()
        # a logo grande, o título e o que fazer, tudo centralizado
        box = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(box, text="", image=art.logo_image(84)).pack(pady=(0, 18))
        ctk.CTkLabel(box, text=title, font=theme.title_font(26), text_color=C["text"]).pack()
        ctk.CTkLabel(box, text=text, font=theme.font(14), text_color=C["muted"], justify="center",
                     wraplength=460).pack(pady=(8, 22))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack()
        for i, (label, cmd, primary) in enumerate(actions):
            make = theme.primary_button if primary else theme.secondary_button
            make(row, label, cmd).pack(side="left", padx=(8 if i else 0, 0))
        self.grid_columnconfigure(0, weight=1)
        box.grid(row=0, column=0, columnspan=99, padx=MARGIN, pady=(72, 48))
        self._empty = box
        self.after_idle(self._sync_scrollbar)

    def _clear_empty(self) -> None:
        if self._empty is not None:
            self._empty.destroy()
            self._empty = None
            self.grid_columnconfigure(0, weight=0)

    def _sync_scrollbar(self) -> None:
        """Mostra a barra de rolagem só quando tem o que rolar."""
        try:
            self.update_idletasks()
            needed = self.winfo_reqheight() > self._parent_canvas.winfo_height() + 2
        except Exception:  # noqa: BLE001  (janela fechando)
            return
        if needed and not self._scrollbar.winfo_ismapped():
            self._scrollbar.grid()
        elif not needed and self._scrollbar.winfo_ismapped():
            self._scrollbar.grid_remove()
            self._parent_canvas.yview_moveto(0)

    # ------------------------------------------------------------------ layout
    def _scale(self) -> float:
        return ctk.ScalingTracker.get_widget_scaling(self)

    def _metrics(self, canvas_width: int) -> tuple[int, int]:
        """Quantas colunas cabem e a largura de cada cartão para preencher a linha."""
        avail = canvas_width / self._scale() - 2 * MARGIN
        gap = theme.CARD_GAP
        cols = max(1, int((avail + gap) // (theme.CARD_MIN_WIDTH + gap)))
        width = int((avail - (cols - 1) * gap) / cols)
        return cols, max(180, min(theme.CARD_MAX_WIDTH, width))

    def _on_resize(self, _event=None) -> None:
        # espera o usuário parar de arrastar a borda da janela
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(120, self._apply_metrics)

    def _apply_metrics(self) -> None:
        self._resize_job = None
        cols, width = self._metrics(self._parent_canvas.winfo_width())
        if width != self._card_width:
            self._card_width = width
            for card in self.cards:
                card.set_width(width)
        if cols != self._columns:
            self._columns = cols
            self._layout()
        self._sync_scrollbar()

    def _layout(self) -> None:
        if not self.cards:
            return
        cols = self._columns or 1
        gap = theme.CARD_GAP
        for i, card in enumerate(self.cards):
            r, c = divmod(i, cols)
            card.grid(
                row=r, column=c, sticky="nw",
                padx=(MARGIN if c == 0 else 0, gap),
                pady=(MARGIN - 6 if r == 0 else 0, gap),
            )
        self.after_idle(self._sync_scrollbar)

    # ------------------------------------------------------------------ clique e arrasto
    def _card_at(self, x: int, y: int) -> Card | None:
        try:
            w = self.winfo_containing(x, y)
        except (KeyError, RuntimeError):
            return None
        while w is not None:
            if isinstance(w, Card):
                return w
            w = getattr(w, "master", None)
        return None

    def _press(self, card: Card, e) -> None:
        self._drag = {"card": card, "x": e.x_root, "y": e.y_root, "active": False, "target": None}

    def _motion(self, card: Card, e) -> None:
        d = self._drag
        if not d or d["card"] is not card:
            return
        if not d["active"]:
            moved = abs(e.x_root - d["x"]) + abs(e.y_root - d["y"])
            if moved < DRAG_THRESHOLD or not self.reorder_enabled:
                return
            d["active"] = True
            card.set_dragging(True)
        target = self._card_at(e.x_root, e.y_root)
        if target is card:
            target = None
        if target is not d["target"]:
            if d["target"] is not None:
                d["target"].set_drop_target(False)
            if target is not None:
                target.set_drop_target(True)
            d["target"] = target
        self._autoscroll(e.y_root)

    def _autoscroll(self, y_root: int) -> None:
        canvas = self._parent_canvas
        top = canvas.winfo_rooty()
        bottom = top + canvas.winfo_height()
        if y_root < top + 40:
            canvas.yview_scroll(-1, "units")
        elif y_root > bottom - 40:
            canvas.yview_scroll(1, "units")

    def _release(self, card: Card, e) -> None:
        d, self._drag = self._drag, None
        if not d or d["card"] is not card:
            return
        if d["active"]:
            card.set_dragging(False)
            target = d["target"]
            if target is not None:
                target.set_drop_target(False)
                self.on_reorder(card.item_id, self.cards.index(target))
        elif self._card_at(e.x_root, e.y_root) is card:
            self.on_open(card.item_id)

    def _menu(self, card: Card, e) -> None:
        self.on_menu(card.item_id, e, card.more)
