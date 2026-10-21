"""Menu flutuante do painel (três pontinhos, botão direito e "Adicionar").

Substitui o menu nativo do Windows, que é cinza, quadrado e não segue o tema.
Cantos arredondados, título opcional, linhas que acendem com o mouse, ação
perigosa em vermelho, aparece com um esmaecer rápido e funciona pelo teclado
(setas, Enter e Esc). Fecha ao clicar fora.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Callable

import customtkinter as ctk

from app.ui import theme
from app.ui.theme import C

_KEY = "#010203"          # cor "furada" da janela: deixa os cantos arredondados transparentes


@dataclass
class MenuItem:
    label: str
    command: Callable[[], None]
    danger: bool = False


SEPARATOR = None          # use no lugar de um MenuItem para separar grupos (vira um espaço)


class PopupMenu(ctk.CTkToplevel):
    def __init__(self, master, items: list[MenuItem | None], *, title: str | None = None,
                 width: int = 240):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        if sys.platform == "win32":
            self.configure(fg_color=_KEY)
            self.attributes("-transparentcolor", _KEY)
        else:
            self.configure(fg_color=C["surface"])
        self._rows: list[tuple[ctk.CTkFrame, ctk.CTkLabel, MenuItem]] = []
        self._active = -1
        self._closed = False
        self._owner = master.winfo_toplevel()
        self._click_binds: list[tuple[str, str]] = []

        box = ctk.CTkFrame(self, corner_radius=theme.RADIUS_MENU, fg_color=C["surface"],
                           border_width=1, border_color=C["chip_hover"], width=width)
        box.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=6, pady=6)

        if title:
            ctk.CTkLabel(inner, text=title, font=theme.font(12, "bold"), text_color=C["muted"],
                         anchor="w", height=26, width=width - 28).pack(fill="x", padx=10, pady=(2, 2))
        for item in items:
            if item is SEPARATOR:
                ctk.CTkFrame(inner, height=6, fg_color="transparent").pack(fill="x")
                continue
            self._add_row(inner, item, width)

        self._keys = (("<Escape>", lambda _e: self.close()),
                      ("<Down>", lambda _e: self._move(1)), ("<Up>", lambda _e: self._move(-1)),
                      ("<Return>", lambda _e: self._run(self._active)))
        for seq, fn in self._keys:
            self.bind(seq, fn)
        self.bind("<FocusOut>", self._on_focus_out)

    def _add_row(self, parent, item: MenuItem, width: int) -> None:
        index = len(self._rows)
        row = ctk.CTkFrame(parent, corner_radius=8, fg_color="transparent", height=34, cursor="hand2")
        row.pack(fill="x")
        label = ctk.CTkLabel(row, text=item.label, font=theme.font(13), anchor="w", height=34,
                             text_color=C["danger"] if item.danger else C["text"], cursor="hand2",
                             width=width - 28)
        label.pack(fill="x", padx=12)
        for w in (row, label):
            w.bind("<Enter>", lambda _e, i=index: self._highlight(i))
            w.bind("<ButtonRelease-1>", lambda _e, i=index: self._run(i))
        self._rows.append((row, label, item))

    # ------------------------------------------------------------------ mostrar e fechar
    def popup(self, x: int, y: int) -> None:
        """Mostra o menu com o canto de cima à esquerda em (x, y), dentro da tela."""
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(4, min(x, sw - w - 8))
        if y + h > sh - 48:                  # sem espaço embaixo: abre para cima
            y = max(4, y - h)
        self.geometry(f"+{x}+{y}")
        try:
            self.attributes("-alpha", 0.0)
        except Exception:  # noqa: BLE001
            pass
        self.deiconify()
        self.lift()
        self.focus_force()
        # clique em qualquer lugar do painel (fora do menu) fecha o menu; as teclas
        # funcionam mesmo se o foco voltar para o painel
        for seq in ("<Button-1>", "<Button-3>"):
            self._click_binds.append((seq, self._owner.bind(seq, self._on_owner_click, add="+")))
        for seq, fn in self._keys:
            self._click_binds.append((seq, self._owner.bind(seq, fn, add="+")))
        self._click_binds.append(("<FocusOut>", self._owner.bind("<FocusOut>", self._on_focus_out, add="+")))
        self._fade(time.perf_counter())

    def _fade(self, start: float) -> None:
        if self._closed:
            return
        t = min(1.0, (time.perf_counter() - start) * 1000 / theme.MENU_FADE_MS)
        try:
            self.attributes("-alpha", 1 - (1 - t) ** 2)
        except Exception:  # noqa: BLE001
            return
        if t < 1.0:
            self.after(theme.ANIM_FRAME_MS, lambda: self._fade(start))

    def _on_owner_click(self, e) -> None:
        if not self._closed and e.widget.winfo_toplevel() is not self:
            self.close()

    def _on_focus_out(self, _e=None) -> None:
        # o foco pula entre o menu e o painel; só fecha se foi para outro programa
        if not self._closed:
            self.after(120, self._close_if_app_left)

    def _close_if_app_left(self) -> None:
        if not self._closed and self.focus_get() is None:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for seq, func_id in self._click_binds:
            try:
                self._owner.unbind(seq, func_id)
            except Exception:  # noqa: BLE001  (janela fechando)
                pass
        self.destroy()

    # ------------------------------------------------------------------ escolha
    def _highlight(self, index: int) -> None:
        self._active = index
        for i, (row, _label, _item) in enumerate(self._rows):
            row.configure(fg_color=C["chip"] if i == index else "transparent")

    def _move(self, step: int) -> None:
        if self._rows:
            self._highlight((self._active + step) % len(self._rows))

    def _run(self, index: int) -> None:
        if not 0 <= index < len(self._rows):
            return
        command = self._rows[index][2].command
        self.close()
        # roda depois de fechar, para diálogos abertos pela ação não brigarem com o menu
        self.master.after(10, command)
