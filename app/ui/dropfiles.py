"""Receber arquivos arrastados do Windows Explorer para a janela (Windows).

O Tk não sabe receber arquivos soltos. Aqui a janela pede ao Windows para
aceitar (DragAcceptFiles) e intercepta a mensagem WM_DROPFILES, que traz a
lista de caminhos. Em outros sistemas, não faz nada.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

_WM_DROPFILES = 0x0233
_WM_COPYDATA = 0x004A
_WM_COPYGLOBALDATA = 0x0049
_GWLP_WNDPROC = -4
_MSGFLT_ALLOW = 1

# referências vivas enquanto a janela existir (senão o Python apaga a função e o Windows trava)
_keep: list[object] = []


def enable(window, on_drop: Callable[[list[Path]], None]) -> bool:
    """Liga o soltar arquivos na janela. Devolve False se não deu (fora do Windows, etc.)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        lresult = ctypes.c_ssize_t
        wndproc_t = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM]
        user32.CallWindowProcW.restype = lresult
        shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [wintypes.HANDLE]

        window.update_idletasks()
        hwnd = user32.GetParent(window.winfo_id())        # a moldura da janela, não o miolo do Tk

        def read_paths(hdrop) -> list[Path]:
            count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            paths = []
            for i in range(count):
                size = shell32.DragQueryFileW(hdrop, i, None, 0) + 1
                buf = ctypes.create_unicode_buffer(size)
                shell32.DragQueryFileW(hdrop, i, buf, size)
                paths.append(Path(buf.value))
            shell32.DragFinish(hdrop)
            return paths

        old_proc = None

        def proc(h, msg, wparam, lparam):
            if msg == _WM_DROPFILES:
                paths = read_paths(wparam)
                window.after(0, lambda: on_drop(paths))       # trata fora da mensagem do Windows
                return 0
            return user32.CallWindowProcW(old_proc, h, msg, wparam, lparam)

        callback = wndproc_t(proc)
        old_proc = user32.SetWindowLongPtrW(hwnd, _GWLP_WNDPROC, ctypes.cast(callback, ctypes.c_void_p))
        _keep.append(callback)
        shell32.DragAcceptFiles(hwnd, True)
        # se o painel estiver "como administrador", o Explorer só consegue soltar com isto
        for msg in (_WM_DROPFILES, _WM_COPYDATA, _WM_COPYGLOBALDATA):
            user32.ChangeWindowMessageFilterEx(hwnd, msg, _MSGFLT_ALLOW, None)
        return True
    except Exception:  # noqa: BLE001  (sem soltar arquivos o resto funciona igual)
        return False
