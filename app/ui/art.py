"""Desenhos feitos pelo próprio painel (com Pillow): capas dos cartões sem
foto (cor lisa com bolhas de sabão), fotos com cantos arredondados, selos
("Aberto agora") e a logo do Bar do Sabão recortada em círculo.

Tudo é desenhado em dobro do tamanho para ficar nítido em telas com zoom.
"""

from __future__ import annotations

import random
import sys
from functools import lru_cache
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from app.core.paths import asset_path
from app.ui import theme

SS = 2   # super-amostragem


# --------------------------------------------------------------------------- cores
def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# --------------------------------------------------------------------------- fontes
@lru_cache(maxsize=None)
def _ui_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if sys.platform == "win32":
        files = {"black": "seguibl.ttf", "bold": "segoeuib.ttf", "normal": "segoeui.ttf"}
        candidates = [rf"C:\Windows\Fonts\{files[weight]}", r"C:\Windows\Fonts\segoeuib.ttf"]
    else:
        candidates = [
            "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


# --------------------------------------------------------------------------- capa sem foto
def _foam(img: Image.Image, seed: str) -> None:
    """Bolhas de sabão (o nome do bar): círculos cheios, um pouco mais claros
    que a capa, subindo do canto de baixo à direita.
    A semente faz cada tipo de arquivo ter sempre as mesmas bolhas."""
    w, h = img.size
    rnd = random.Random(seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    foam = _rgb(theme.FOAM)
    for _ in range(14):
        # mais bolhas (e maiores) perto do canto; nenhuma chega no texto à esquerda
        t = rnd.random() ** 1.4
        x = w - t * w * 0.62 + rnd.uniform(-0.04, 0.04) * w
        y = h - rnd.random() ** 1.2 * h * (1.1 - 0.6 * t)
        r = h * (0.22 - 0.16 * t) * rnd.uniform(0.6, 1.1)
        alpha = int(255 * rnd.uniform(0.06, 0.12))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*foam, alpha))
    img.paste(layer, mask=layer)


@lru_cache(maxsize=128)
def cover(color: str, badge: str, size: tuple[int, int]) -> Image.Image:
    w, h = size[0] * SS, size[1] * SS
    img = Image.new("RGB", (w, h), _rgb(color))
    _foam(img, f"{color}{badge}")
    draw = ImageDraw.Draw(img)

    # a extensão em letra bem grossa, no canto de baixo à esquerda
    text = badge.upper()
    f = _ui_font(int(h * (0.24 if len(text) <= 4 else 0.19)), "black")
    bbox = draw.textbbox((0, 0), text, font=f)
    margin = int(h * 0.11)
    draw.text((margin - bbox[0], h - margin - bbox[3]), text, font=f, fill=_rgb(theme.FOAM))
    return img


@lru_cache(maxsize=64)
def _photo(path: str, mtime: float, size: tuple[int, int]) -> Image.Image | None:
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            return ImageOps.fit(im, (size[0] * SS, size[1] * SS), Image.Resampling.LANCZOS)
    except OSError:
        return None


def photo(path: Path, size: tuple[int, int]) -> Image.Image | None:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return _photo(str(path), mtime, size)


# --------------------------------------------------------------------------- selos e cantos
BADGE_STYLES = {
    "open":    (theme.FOAM, theme.C["text"][0]),
    "missing": (theme.C["danger"][0], theme.C["on_danger"][0]),
    "linked":  (theme.C["text"][0], theme.FOAM),
    "site":    (theme.C["text"][0], theme.FOAM),
}


def _draw_badges(img: Image.Image, badges: tuple[tuple[str, str], ...]) -> None:
    draw = ImageDraw.Draw(img)
    f = _ui_font(11 * SS)
    x = 8 * SS
    y = 8 * SS
    for kind, text in badges:
        bg, fg = BADGE_STYLES.get(kind, BADGE_STYLES["linked"])
        bbox = draw.textbbox((0, 0), text, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pw, ph = tw + 16 * SS, th + 10 * SS
        draw.rounded_rectangle([x, y, x + pw, y + ph], radius=ph // 2, fill=_rgb(bg))
        draw.text((x + 8 * SS - bbox[0], y + 5 * SS - bbox[1]), text, font=f, fill=_rgb(fg))
        x += pw + 6 * SS


def _round(img: Image.Image, radius: int, bg: str) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1],
                                           radius=radius * SS, fill=255)
    out = Image.new("RGB", img.size, _rgb(bg))
    out.paste(img, mask=mask)
    return out


def card_image(
    base: Image.Image,
    size: tuple[int, int],
    *,
    badges: tuple[tuple[str, str], ...] = (),
    dimmed: bool = False,
    radius: int = theme.RADIUS_COVER,
    bg: tuple[str, str] = theme.C["surface"],
) -> ctk.CTkImage:
    """Monta a imagem final do cartão para os modos claro e escuro."""
    img = base.copy()
    if dimmed:
        img = ImageEnhance.Brightness(ImageOps.grayscale(img).convert("RGB")).enhance(0.85)
    if badges:
        _draw_badges(img, badges)
    light = _round(img, radius, bg[0])
    dark = _round(img, radius, bg[1])
    return ctk.CTkImage(light_image=light, dark_image=dark, size=size)


# --------------------------------------------------------------------------- logo
@lru_cache(maxsize=16)
def logo(px: int) -> Image.Image:
    """A logo do Bar do Sabão recortada em círculo, com fundo transparente."""
    try:
        with Image.open(asset_path("logo.png")) as im:
            src = im.convert("RGBA")
    except OSError:                                   # sem a logo: um círculo vermelho
        src = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        ImageDraw.Draw(src).ellipse([0, 0, 255, 255], fill=_rgb(theme.C["accent"][0]))
    big = px * 4
    src = src.resize((big, big), Image.Resampling.LANCZOS)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, big - 1, big - 1], fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(src, mask=mask)
    return out.resize((px, px), Image.Resampling.LANCZOS)


def logo_image(size: int) -> ctk.CTkImage:
    big = logo(size * SS)
    return ctk.CTkImage(light_image=big, dark_image=big, size=(size, size))
