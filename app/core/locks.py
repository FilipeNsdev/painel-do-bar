"""Trava simples por arquivo, para dois backups nunca rodarem ao mesmo tempo
(por exemplo, o semanal automático e um manual pelo painel)."""

from __future__ import annotations

import os
import time
from pathlib import Path


class LockBusy(Exception):
    pass


class FileLock:
    def __init__(self, path: Path, stale_after_s: float = 2 * 60 * 60):
        self.path = path
        self.stale_after_s = stale_after_s
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self._is_stale():
                    self.path.unlink(missing_ok=True)   # sobra de um processo que travou
                    continue
                raise LockBusy(str(self.path)) from None
            with os.fdopen(fd, "w") as fh:
                fh.write(f"{os.getpid()} {time.time():.0f}")
            self._held = True
            return
        raise LockBusy(str(self.path))

    def release(self) -> None:
        if self._held:
            self.path.unlink(missing_ok=True)
            self._held = False

    def _is_stale(self) -> bool:
        try:
            return time.time() - self.path.stat().st_mtime > self.stale_after_s
        except OSError:
            return True

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()
