"""Textos do painel: datas por extenso, tamanhos e plurais em português."""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def when(dt: datetime, now: datetime | None = None) -> str:
    """'hoje às 10:32', 'ontem às 18:05', 'sexta às 09:00', '03/09 às 14:10'."""
    now = now or datetime.now()
    days = (now.date() - dt.date()).days
    hour = f"{dt:%H:%M}"
    if days == 0:
        return f"hoje às {hour}"
    if days == 1:
        return f"ontem às {hour}"
    if 1 < days < 7:
        return f"{WEEKDAYS[dt.weekday()]} às {hour}"
    if dt.year == now.year:
        return f"{dt:%d/%m} às {hour}"
    return f"{dt:%d/%m/%Y}"


def when_next(dt: datetime, now: datetime | None = None) -> str:
    """Datas futuras: 'hoje às 22:00', 'amanhã às 22:00', 'domingo às 22:00'."""
    now = now or datetime.now()
    days = (dt.date() - now.date()).days
    hour = f"{dt:%H:%M}"
    if days == 0:
        return f"hoje às {hour}"
    if days == 1:
        return f"amanhã às {hour}"
    if days < 7:
        return f"{WEEKDAYS[dt.weekday()]} às {hour}"
    return f"{dt:%d/%m} às {hour}"


def size(n_bytes: int) -> str:
    value = float(n_bytes)
    for unit in ("bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "bytes":
                return f"{int(value)} bytes"
            return f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024
    return f"{n_bytes} bytes"


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def fold(text: str) -> str:
    """Para buscar sem diferenciar acentos nem maiúsculas: 'Preços' -> 'precos'."""
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c)).casefold()


def shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def path_tail(path: Path | str, parts: int = 2) -> str:
    r"""Só o fim de um caminho longo: 'C:\...\Meu Drive\Backups' -> 'Meu Drive\Backups'."""
    p = Path(path)
    tail = p.parts[-parts:]
    return str(Path(*tail)) if len(p.parts) > parts else str(p)


def ago_days(dt: datetime, now: datetime | None = None) -> int:
    now = now or datetime.now()
    return max(0, (now - dt) // timedelta(days=1))
