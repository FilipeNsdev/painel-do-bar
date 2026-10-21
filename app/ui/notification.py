"""Aviso no canto da tela quando o backup automático termina.

Usado só no modo silencioso (--backup), em que não existe janela do painel.
"""

from __future__ import annotations

import customtkinter as ctk

from app.core.models import BackupRecord, BackupStatus
from app.ui import art, text, theme
from app.ui.theme import C

WIDTH, HEIGHT = 380, 104


def _work_area(root: ctk.CTk) -> tuple[int, int, int, int]:
    """Área útil da tela (sem a barra de tarefas)."""
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # type: ignore[attr-defined]
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:  # noqa: BLE001
        return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight() - 48


def show_backup_notification(record: BackupRecord, panel_name: str) -> None:
    theme.apply_theme("auto")
    root = ctk.CTk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(fg_color=C["surface"])

    if record.status == BackupStatus.FAILED.value:
        title, body, accent, ms = ("O backup automático não deu certo",
                                   "Abra o painel para ver o motivo.", C["danger"], 20000)
    elif record.cloud_path:
        title = "Backup da semana feito"
        body = (f"{text.plural(record.file_count, 'arquivo copiado', 'arquivos copiados')} "
                f"para a nuvem ({text.size(record.size_bytes)}).")
        accent, ms = C["ok"], 9000
    else:
        title = "Backup feito só neste computador"
        body = record.warnings[0] if record.warnings else "A cópia na nuvem não foi feita."
        accent, ms = C["warn"], 15000

    frame = ctk.CTkFrame(root, corner_radius=0, fg_color=C["surface"], border_width=1,
                         border_color=C["border"])
    frame.pack(fill="both", expand=True)
    ctk.CTkFrame(frame, width=6, height=1, corner_radius=0, fg_color=accent).pack(side="left", fill="y")
    ctk.CTkLabel(frame, text="", image=art.logo_image(34)).pack(side="left", padx=(14, 10), pady=12, anchor="n")
    box = ctk.CTkFrame(frame, fg_color="transparent")
    box.pack(side="left", fill="both", expand=True, pady=12, padx=(0, 14))
    ctk.CTkLabel(box, text=panel_name, font=theme.font(11), text_color=C["muted"], anchor="w").pack(anchor="w")
    ctk.CTkLabel(box, text=title, font=theme.font(14, "bold"), anchor="w").pack(anchor="w")
    ctk.CTkLabel(box, text=text.shorten(body, 140), font=theme.font(12), text_color=C["muted"],
                 anchor="w", justify="left", wraplength=WIDTH - 90).pack(anchor="w")

    left, top, right, bottom = _work_area(root)
    scale = ctk.ScalingTracker.get_window_scaling(root)     # zoom do Windows (125%, 150%...)
    x = int(right - (WIDTH + 16) * scale)
    y = int(bottom - (HEIGHT + 16) * scale)
    root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")
    for w in (root, frame, box):
        w.bind("<Button-1>", lambda _e: root.destroy())
    root.after(ms, root.destroy)
    root.mainloop()
