"""Grade de cartões com rolagem, que se ajusta à largura da janela e deixa
mudar a ordem arrastando um cartão.

Os cartões ficam em posições calculadas aqui (place), e não no grid do Tk:
assim dá para animar. Ao arrastar, o cartão segue o mouse e os outros
deslizam para abrir espaço; ao soltar, ele desliza para o lugar dele.
"""

from __future__ import annotations

import time
import tkinter
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
        self._pos: dict[Card, tuple[float, float]] = {}       # onde cada cartão está agora
        self._tweens: dict[Card, tuple[float, float, float, float]] = {}
        self._tween_start = 0.0
        self._tween_job: str | None = None
        self._content_height = 0.0
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
        self._pos.clear()
        self._stop_tween()
        self._layout(animate=False)

    def show_empty(self, title: str, text: str, actions: list[tuple[str, Callable[[], None], bool]]) -> None:
        """Tela vazia com orientação do que fazer. actions: (texto, comando, principal?)."""
        for card in self.cards:
            card.destroy()
        self.cards = []
        self._pos.clear()
        self._stop_tween()
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
        changed = width != self._card_width or cols != self._columns
        if width != self._card_width:
            self._card_width = width
            for card in self.cards:
                card.set_width(width)
        self._columns = cols
        if changed and self._drag is None:
            self._layout()                 # os cartões deslizam para as colunas novas
        self._sync_scrollbar()

    def _slots(self) -> list[tuple[float, float]]:
        """Posição (x, y) de cada vaga da grade, em medidas do tema (sem o zoom)."""
        cols = self._columns or 1
        gap = theme.CARD_GAP
        scale = self._scale()
        heights = [c.winfo_reqheight() / scale for c in self.cards]
        slots: list[tuple[float, float]] = []
        y = MARGIN - 6
        for row_start in range(0, len(self.cards), cols):
            for c in range(min(cols, len(self.cards) - row_start)):
                slots.append((MARGIN + c * (self._card_width + gap), y))
            y += max(heights[row_start:row_start + cols]) + gap
        self._content_height = y + 8
        return slots

    def _layout(self, *, animate: bool = True, skip: Card | None = None) -> None:
        """Põe cada cartão na sua vaga. Com animate, desliza até lá."""
        if not self.cards:
            return
        self.update_idletasks()
        slots = self._slots()
        # cartões em "place" não dão altura ao miolo rolável: a altura vem daqui, em pixels reais
        # (o configure do CTkScrollableFrame mudaria a área visível, não o miolo)
        tkinter.Frame.configure(self, height=round(self._content_height * self._scale()))
        targets = {card: slots[i] for i, card in enumerate(self.cards) if card is not skip}
        if animate:
            self._tween_to(targets)
        else:
            for card, (x, y) in targets.items():
                self._put(card, x, y)
        self.after_idle(self._sync_scrollbar)

    def _put(self, card: Card, x: float, y: float) -> None:
        self._pos[card] = (x, y)
        card.place(x=round(x), y=round(y))

    # ------------------------------------------------------------------ animação
    def _tween_to(self, targets: dict[Card, tuple[float, float]]) -> None:
        """Desliza os cartões de onde estão até os alvos (rápido no começo, suave no fim)."""
        for card, (tx, ty) in targets.items():
            fx, fy = self._pos.get(card, (tx, ty))
            if (fx, fy) == (tx, ty):
                self._tweens.pop(card, None)
                self._put(card, tx, ty)
            else:
                self._tweens[card] = (fx, fy, tx, ty)   # quem já andava recomeça de onde está
        self._tween_start = time.perf_counter()
        if self._tween_job is None and self._tweens:
            self._tween_step()

    def _tween_step(self) -> None:
        t = min(1.0, (time.perf_counter() - self._tween_start) * 1000 / theme.ANIM_MS)
        ease = 1 - (1 - t) ** 3
        for card, (fx, fy, tx, ty) in list(self._tweens.items()):
            if not card.winfo_exists():
                self._tweens.pop(card, None)
                continue
            self._put(card, fx + (tx - fx) * ease, fy + (ty - fy) * ease)
        if t >= 1.0:
            self._tweens.clear()
            self._tween_job = None
        else:
            self._tween_job = self.after(theme.ANIM_FRAME_MS, self._tween_step)

    def _stop_tween(self) -> None:
        if self._tween_job is not None:
            self.after_cancel(self._tween_job)
            self._tween_job = None
        self._tweens.clear()

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
        self._drag = {"card": card, "x": e.x_root, "y": e.y_root, "active": False,
                      "start": self.cards.index(card)}

    def _pointer(self, e) -> tuple[float, float]:
        """Posição do mouse dentro da grade, em medidas do tema."""
        scale = self._scale()
        return (e.x_root - self.winfo_rootx()) / scale, (e.y_root - self.winfo_rooty()) / scale

    def _motion(self, card: Card, e) -> None:
        d = self._drag
        if not d or d["card"] is not card:
            return
        mx, my = self._pointer(e)
        if not d["active"]:
            moved = abs(e.x_root - d["x"]) + abs(e.y_root - d["y"])
            if moved < DRAG_THRESHOLD or not self.reorder_enabled:
                return
            d["active"] = True
            x, y = self._pos.get(card, (0, 0))
            d["grab"] = (mx - x, my - y)          # onde o mouse pegou: o cartão não pula
            self._tweens.pop(card, None)
            card.set_dragging(True)
            card.lift()
        self._put(card, mx - d["grab"][0], my - d["grab"][1])
        index = self._slot_at(mx, my)
        if index != self.cards.index(card):
            self.cards.remove(card)
            self.cards.insert(index, card)
            self._layout(skip=card)               # os outros deslizam para abrir espaço
        self._autoscroll(e.y_root)

    def _slot_at(self, x: float, y: float) -> int:
        """Vaga mais perto do mouse."""
        slots = self._slots()
        w = self._card_width
        return min(range(len(slots)),
                   key=lambda i: (slots[i][0] + w / 2 - x) ** 2 + (slots[i][1] + w * 0.45 - y) ** 2)

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
            self._layout()                        # o cartão desliza para a vaga dele
            new_index = self.cards.index(card)
            if new_index != d["start"]:
                self.on_reorder(card.item_id, new_index)
        elif self._card_at(e.x_root, e.y_root) is card:
            self.on_open(card.item_id)

    def _menu(self, card: Card, e) -> None:
        self.on_menu(card.item_id, e, card.more)
