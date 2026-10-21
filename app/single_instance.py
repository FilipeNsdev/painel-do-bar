"""Impede abrir duas janelas do painel ao mesmo tempo (Windows).

Duas janelas abertas poderiam gravar a configuração uma por cima da outra.
"""

from __future__ import annotations

import os

_ERROR_ALREADY_EXISTS = 183
_handle = None   # precisa ficar vivo enquanto o programa roda


def already_running(key: str) -> bool:
    global _handle
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        safe = "".join(c if c.isalnum() else "_" for c in key)[-200:]
        _handle = kernel32.CreateMutexW(None, False, f"Local\\PainelDoBar_{safe}")
        return ctypes.get_last_error() == _ERROR_ALREADY_EXISTS
    except Exception:  # noqa: BLE001
        return False


def bring_to_front(title: str) -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            user32.ShowWindow(hwnd, 9)          # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception:  # noqa: BLE001
        pass
