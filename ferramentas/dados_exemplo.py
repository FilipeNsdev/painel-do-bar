"""Cria uma pasta de dados de EXEMPLO para testar o painel sem mexer nos dados reais.

    python ferramentas/dados_exemplo.py                 -> cria em %TEMP%/PainelDoBar_exemplo
    python ferramentas/dados_exemplo.py C:/algum/lugar  -> cria onde você mandar

Depois, para abrir o painel com esses dados:
    set PAINEL_DADOS=<pasta>/Dados      (Windows, no cmd)
    python main.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT = Path(tempfile.gettempdir()) / "PainelDoBar_exemplo"

ARQUIVOS = [
    "Contas a Pagar 2026.xlsm", "controle_precos.xlsx", "Estoque semanal.xlsx",
    "Cardápio.pdf", "Escala de funcionários.docx", "Fechamento de caixa.xlsx",
]


def _foto_exemplo(destino: Path) -> Path:
    """Desenha uma 'foto' simples (três copos de chopp) para um cartão."""
    from PIL import Image, ImageDraw, ImageFilter

    im = Image.new("RGB", (960, 576), "#3b2a1a")
    d = ImageDraw.Draw(im)
    for i in range(0, 576, 4):
        d.line([(0, i), (960, i)], fill=(int(60 + i / 9), int(40 + i / 14), 20))
    for cx in (300, 520, 720):
        d.rounded_rectangle([cx - 70, 150, cx + 70, 520], radius=24, fill="#e8a33a")
        d.rounded_rectangle([cx - 70, 110, cx + 70, 190], radius=30, fill="#f6efe0")
    im = im.filter(ImageFilter.GaussianBlur(2))
    im.save(destino)
    return destino


def criar(base: Path = DEFAULT) -> Path:
    """Recria a pasta de exemplo do zero e devolve o caminho da pasta Dados."""
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    os.environ["PAINEL_DADOS"] = str(base / "Dados")

    from app.core.images import prepare_photo
    from app.core.library import AddMode
    from app.core.models import BackupTrigger
    from app.core.panel import Panel

    p = Panel()
    files = p.paths.files
    for nome in ARQUIVOS:
        (files / nome).write_bytes(os.urandom(20_000))
    notas = files / "Notas fiscais"
    notas.mkdir()
    for i in range(14):
        (notas / f"nf{i}.xml").write_text("<nf/>", encoding="utf-8")

    fora = base / "OutroLugar"
    fora.mkdir()
    (fora / "Contrato aluguel.pdf").write_bytes(b"x" * 5000)
    p.library.sync()
    p.library.add_paths([fora / "Contrato aluguel.pdf"], mode=AddMode.LINK)
    p.library.add_link("Portal da NF-e", "www.nfe.fazenda.gov.br")

    itens = {i.target: i for i in p.library.items}
    foto = _foto_exemplo(base / "chopp.jpg")
    p.library.set_image(itens["Fechamento de caixa.xlsx"].id, prepare_photo(foto), "jpg")
    p.library.update(itens["Contas a Pagar 2026.xlsm"].id, name="Contas a Pagar",
                     description="Lançar os boletos toda segunda")
    p.library.update(itens["controle_precos.xlsx"].id, name="Controle de preços")
    p.library.update(itens["Fechamento de caixa.xlsx"].id, name="Fechamento de caixa",
                     description="Conferir no fim de cada noite")

    nuvem = base / "GoogleDrive_de_mentira" / "Meu Drive"
    nuvem.mkdir(parents=True)
    p.settings.backup_destination = str(nuvem / "Backups Painel do Bar")
    p.settings.panel_name = "Bar do Sabão"
    p.store.save()
    p.run_backup(BackupTrigger.MANUAL)

    # simula a planilha de contas aberta no Excel (selo "Aberto agora")
    (files / "~$Contas a Pagar 2026.xlsm").write_bytes(b"lock")
    return p.paths.root


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    print("Dados de exemplo em:", criar(destino))
