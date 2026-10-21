"""Janela de diálogo padrão do painel e as mensagens prontas (avisar e
confirmar), para todas as janelinhas terem o mesmo jeito."""

from __future__ import annotations

import sys
import tkinter
from typing import Any, Callable

import customtkinter as ctk

from app.core.paths import asset_path
from app.ui import theme
from app.ui.theme import C


def set_window_icon(window: tkinter.Misc) -> None:
    if sys.platform == "win32":
        ico = asset_path("icone.ico")
        if ico.exists():
            try:
                window.iconbitmap(str(ico))
            except tkinter.TclError:
                pass


def style_titlebar(window: tkinter.Misc) -> None:
    """Pinta a barra de título da janela com a cor do cabeçalho (Windows 11).

    Sem isso o Windows usa a cor de destaque do sistema, que pode ser
    qualquer uma. No Windows 10 o pedido é ignorado e nada muda."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        def colorref(hex_color: str) -> ctypes.c_int:
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
            return ctypes.c_int(r | g << 8 | b << 16)

        # 20 = modo escuro (cor dos botões minimizar/fechar), sem esconder a janela
        dark = ctypes.c_int(1 if ctk.get_appearance_mode() == "Dark" else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
        # 34 = borda, 35 = fundo da barra, 36 = texto do título
        for attribute, color in ((34, C["chip_hover"]), (35, C["surface"]), (36, C["text"])):
            value = colorref(theme.pick(color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value),
                                                       ctypes.sizeof(value))
    except (AttributeError, OSError, tkinter.TclError):
        pass


class Dialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, *, heading: str | None = None, width: int = 460):
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.owner = master.winfo_toplevel()
        self.transient(self.owner)
        self.result: Any = None
        self.width = width
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda _e: self.cancel())

        self.content = ctk.CTkFrame(self, fg_color="transparent", width=width)
        self.content.pack(fill="both", expand=True, padx=28, pady=(24, 0))
        if heading:
            ctk.CTkLabel(
                self.content, text=heading, font=theme.font(19, "bold"),
                anchor="w", justify="left", wraplength=width,
            ).pack(anchor="w", fill="x", pady=(0, 8))
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", padx=28, pady=(18, 24))
        # o CustomTkinter troca o ícone das janelas 200 ms depois de criar
        self.after(260, lambda: (set_window_icon(self), style_titlebar(self)))

    # ------------------------------------------------------------------ montagem
    def paragraph(self, text: str, *, muted: bool = True, size: int = 13, pady=(0, 8)) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            self.content, text=text, font=theme.font(size), justify="left", anchor="w",
            text_color=C["muted"] if muted else C["text"], wraplength=self.width,
        )
        label.pack(anchor="w", fill="x", pady=pady)
        return label

    def add_buttons(
        self,
        ok_text: str,
        on_ok: Callable[[], None],
        *,
        cancel_text: str | None = "Cancelar",
        danger: bool = False,
    ) -> ctk.CTkButton:
        make = theme.danger_button if danger else theme.primary_button
        ok = make(self.footer, ok_text, on_ok, width=max(120, 9 * len(ok_text) + 32))
        ok.pack(side="right")
        if cancel_text:
            theme.secondary_button(self.footer, cancel_text, self.cancel, width=110).pack(
                side="right", padx=(0, 8)
            )
        self.bind("<Return>", lambda _e: on_ok())
        return ok

    # ------------------------------------------------------------------ ciclo de vida
    def show(self) -> Any:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        ox, oy = self.owner.winfo_rootx(), self.owner.winfo_rooty()
        ow, oh = self.owner.winfo_width(), self.owner.winfo_height()
        x = max(0, ox + (ow - w) // 2)
        y = max(0, oy + (oh - h) // 3)
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        style_titlebar(self)
        self.lift()
        self.focus_force()
        self.after(10, self._grab)
        self.wait_window()
        return self.result

    def _grab(self) -> None:
        try:
            self.grab_set()
        except tkinter.TclError:
            self.after(50, self._grab)

    def close(self, result: Any = None) -> None:
        self.result = result
        try:
            self.grab_release()
        except tkinter.TclError:
            pass
        self.destroy()

    def cancel(self) -> None:
        self.close(None)


# --------------------------------------------------------------------------- mensagens prontas
def message(master, title: str, text: str, *, button: str = "Entendi") -> None:
    d = Dialog(master, title, heading=title)
    d.paragraph(text, muted=False)
    d.add_buttons(button, lambda: d.close(True), cancel_text=None)
    d.show()


def confirm(
    master, title: str, text: str, *, ok: str, cancel: str = "Cancelar", danger: bool = False
) -> bool:
    d = Dialog(master, title, heading=title)
    d.paragraph(text, muted=False)
    d.add_buttons(ok, lambda: d.close(True), cancel_text=cancel, danger=danger)
    return bool(d.show())
