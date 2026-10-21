"""Abre o painel com dados de exemplo e salva uma imagem de cada tela.

Serve para revisar o visual depois de mexer no código (ou para uma IA
conferir o design olhando as imagens).

    python ferramentas/capturar_telas.py                  -> todas as telas, claro e escuro
    python ferramentas/capturar_telas.py --tema escuro
    python ferramentas/capturar_telas.py --cenas principal editar

As imagens vão para a pasta "capturas" do projeto. Os dados reais do bar
nunca são usados: tudo roda numa pasta de exemplo temporária.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CENAS = [
    "principal", "estreita", "busca", "editar", "configuracoes",
    "adicionar", "remover", "backup", "aviso", "vazio",
]


# --------------------------------------------------------------------------- uma cena
def _capturar(janela, arquivo: Path) -> None:
    import time

    from PIL import ImageGrab

    # No Windows, uma janela nova não consegue vir para a frente sozinha.
    # "topmost" põe o painel e os diálogos por cima de tudo só para a foto.
    janelas = [janela] + [c for c in janela.winfo_children() if c.winfo_class() == "Toplevel"]
    for j in janelas:
        j.attributes("-topmost", True)
        j.lift()
    janela.update()
    time.sleep(0.25)
    janela.update()
    x, y = janela.winfo_rootx(), janela.winfo_rooty()
    w, h = janela.winfo_width(), janela.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=sys.platform == "win32").save(arquivo)
    print("  salvo:", arquivo.name)


def rodar_cena(cena: str, tema: str, saida: Path) -> None:
    from app.core.panel import Panel
    from app.ui import theme
    from app.ui.dialogs import add_items, edit_item, settings
    from app.ui.main_window import MainWindow

    panel = Panel()
    panel.settings.theme = tema
    panel.settings.backup_on_open_if_overdue = False
    theme.apply_theme(tema)
    w = MainWindow(panel)
    w.geometry("1180x760+30+30")

    def foto(nome: str) -> None:
        _capturar(w, saida / f"{nome}-{tema}.png")

    def depois(ms: int, fn) -> None:
        w.after(ms, fn)

    def abrir_dialogo(d, nome: str, extra=None) -> None:
        def tirar():
            d.update()
            foto(nome)
            if extra:
                extra()
            else:
                d.cancel()
                w.after(200, w.destroy)
        d.after(900, tirar)
        d.show()

    item = lambda alvo: next(i for i in panel.library.items if i.target == alvo)  # noqa: E731

    if cena in ("principal", "vazio"):
        depois(1800, lambda: (foto(cena), w.destroy()))
    elif cena == "estreita":
        w.geometry("820x700+30+30")
        depois(1800, lambda: (foto(cena), w.destroy()))
    elif cena == "busca":
        def buscar():
            w.header.search.insert(0, "contas")
            w._on_search("contas")
            w.after(700, lambda: (foto(cena), w.destroy()))
        depois(1200, buscar)
    elif cena == "editar":
        depois(1200, lambda: abrir_dialogo(
            edit_item.EditItemDialog(w, panel, item("controle_precos.xlsx")), cena))
    elif cena == "configuracoes":
        def abrir():
            d = settings.SettingsDialog(w, panel)

            def aba_painel():
                d._show_tab("Painel")
                d.after(500, lambda: (foto("configuracoes-painel"), d.cancel(), w.after(200, w.destroy)))
            abrir_dialogo(d, "configuracoes-backup", extra=aba_painel)
        depois(1200, abrir)
    elif cena == "adicionar":
        depois(1200, lambda: abrir_dialogo(
            add_items.AddModeDialog(w, [Path("Estoque.xlsx"), Path("Notas.pdf")]), cena))
    elif cena == "remover":
        def remover():
            w.after(900, lambda: foto(cena))
            w.after(1200, w.destroy)
            w.remove_item(item("Cardápio.pdf").id)
        depois(1200, remover)
    elif cena == "backup":
        def fazer():
            w.start_backup(ask_open=False)
            w.after(80, lambda: foto("backup-rodando"))
            w.after(3000, lambda: (foto("backup-terminado"), w.destroy()))
        depois(1200, fazer)
    elif cena == "aviso":
        depois(1200, lambda: w.toast.show("Backup feito e copiado para a nuvem."))
        depois(1800, lambda: (foto(cena), w.destroy()))
    w.mainloop()


# --------------------------------------------------------------------------- todas
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tema", choices=["claro", "escuro", "ambos"], default="ambos")
    ap.add_argument("--cenas", nargs="*", choices=CENAS, default=CENAS)
    ap.add_argument("--saida", default=str(ROOT / "capturas"))
    ap.add_argument("--_uma", nargs=2, help=argparse.SUPPRESS)   # uso interno: cena tema
    args = ap.parse_args()
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    if args._uma:                       # processo filho: roda uma cena só
        rodar_cena(args._uma[0], args._uma[1], saida)
        return

    from ferramentas.dados_exemplo import criar  # noqa: E402

    temas = ["claro", "escuro"] if args.tema == "ambos" else [args.tema]
    for cena in args.cenas:
        for tema in temas:
            print(f"{cena} ({tema})")
            dados = criar() if cena != "vazio" else _pasta_vazia()
            env = dict(os.environ, PAINEL_DADOS=str(dados))
            subprocess.run([sys.executable, __file__, "--saida", str(saida), "--_uma", cena, tema],
                           env=env, cwd=ROOT, timeout=90, check=False)
    print("Pronto. Imagens em:", saida)


def _pasta_vazia() -> Path:
    import shutil
    import tempfile

    pasta = Path(tempfile.gettempdir()) / "PainelDoBar_vazio" / "Dados"
    shutil.rmtree(pasta.parent, ignore_errors=True)
    return pasta


if __name__ == "__main__":
    main()
