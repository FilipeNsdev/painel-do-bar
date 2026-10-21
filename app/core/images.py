"""Preparo das fotos dos cartões.

A foto escolhida é cortada no formato do cartão (5:3), reduzida e salva como
JPEG em Dados/Sistema/imagens. A original do usuário nunca é alterada.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

PHOTO_SIZE = (960, 576)          # proporção 5:3, igual à capa do cartão
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff")


class ImageError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


def load_photo(source: Path) -> Image.Image:
    try:
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)      # respeita a rotação do celular
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.getchannel("A"))
                return bg
            return im.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageError(
            "Não consegui abrir essa imagem. Use uma foto em JPG, PNG ou WEBP."
        ) from exc


def prepare_photo(source: Path) -> bytes:
    """Lê, corta no formato do cartão e devolve os bytes do JPEG final."""
    im = load_photo(source)
    fitted = ImageOps.fit(im, PHOTO_SIZE, Image.Resampling.LANCZOS, centering=(0.5, 0.45))
    buf = BytesIO()
    fitted.save(buf, "JPEG", quality=88, optimize=True)
    return buf.getvalue()
