"""Aviso rápido que aparece no canto da janela e some sozinho."""

from __future__ import annotations

import customtkinter as ctk

from app.ui import theme
from app.ui.theme import C

_KIND_COLORS = {"ok": C["ok"], "warn": C["warn"], "error": C["danger"]}


class Toast:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.frame: ctk.CTkFrame | None = None
        self._job: str | None = None

    def show(self, text: str, kind: str = "ok", duration_ms: int = 5000) -> None:
        self.hide()
        f = ctk.CTkFrame(self.root, corner_radius=12, fg_color=C["toast"], border_width=0)
        bar = ctk.CTkFrame(f, width=6, height=1, corner_radius=3, fg_color=_KIND_COLORS.get(kind, C["ok"]))
        bar.pack(side="left", fill="y", padx=(12, 0), pady=12)
        label = ctk.CTkLabel(f, text=text, font=theme.font(13), text_color=C["on_toast"],
                             justify="left", wraplength=360)
        label.pack(side="left", padx=(12, 18), pady=12)
        f.place(relx=1.0, rely=1.0, x=-26, y=-104, anchor="se")
        f.lift()
        for w in (f, label):
            w.bind("<Button-1>", lambda _e: self.hide())
        self.frame = f
        self._job = self.root.after(duration_ms, self.hide)

    def hide(self) -> None:
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None
