"""Gera assets/icone.ico e assets/icone.png a partir da logo do Bar do Sabão
(assets/logo.png), recortada em círculo.

Só precisa rodar de novo se trocar a logo:  python empacotamento/gerar_icone.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ui.art import logo  # noqa: E402


def main() -> None:
    assets = ROOT / "assets"
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    images = [logo(s) for s in sizes]
    images[-1].save(assets / "icone.ico", sizes=[(s, s) for s in sizes], append_images=images[:-1])
    logo(512).save(assets / "icone.png")
    print("Ícones gerados em", assets)


if __name__ == "__main__":
    main()
