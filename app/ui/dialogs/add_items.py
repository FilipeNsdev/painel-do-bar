"""Perguntas ao adicionar coisas no painel: como trazer arquivos de fora
(mover, copiar ou só criar um atalho) e os dados de um site."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from app.core.library import AddMode
from app.ui import theme
from app.ui.dialogs.base import Dialog
from app.ui.theme import C

MODES = [
    (AddMode.MOVE, "Mover para o painel",
     "O arquivo sai de onde está e passa a ficar na pasta do painel. "
     "Bom para juntar tudo num lugar só."),
    (AddMode.COPY, "Copiar para o painel",
     "O painel guarda uma cópia. O original continua onde estava, "
     "mas o que você mudar pelo painel vale só para a cópia."),
    (AddMode.LINK, "Deixar onde está",
     "O painel só cria um atalho. O arquivo continua no mesmo lugar "
     "e entra no backup do mesmo jeito."),
]


class AddModeDialog(Dialog):
    """Devolve o AddMode escolhido, ou None se cancelar."""

    def __init__(self, master, paths: list[Path]):
        if len(paths) == 1:
            kind = "a pasta" if paths[0].is_dir() else ""
            heading = f"Adicionar {kind} “{paths[0].name}”".replace("  ", " ")
        else:
            heading = f"Adicionar {len(paths)} itens"
        super().__init__(master, "Adicionar ao painel", heading=heading, width=470)
        self.paragraph("Como o painel deve guardar?", muted=False, pady=(0, 12))

        self.choice = ctk.StringVar(value=AddMode.MOVE.value)
        self.rows: dict[str, ctk.CTkFrame] = {}
        for mode, title, text in MODES:
            row = ctk.CTkFrame(self.content, corner_radius=12, border_width=2,
                               border_color=C["surface"], fg_color=C["surface"])
            row.pack(fill="x", pady=(0, 8))
            radio = ctk.CTkRadioButton(row, text=title, value=mode.value, variable=self.choice,
                                       font=theme.font(13, "bold"), command=self._paint)
            radio.pack(anchor="w", padx=14, pady=(12, 2))
            desc = ctk.CTkLabel(row, text=text, font=theme.font(12), text_color=C["muted"],
                                justify="left", anchor="w", wraplength=self.width - 70)
            desc.pack(anchor="w", padx=(44, 14), pady=(0, 12))
            for w in (row, desc):
                w.bind("<Button-1>", lambda _e, m=mode: self._pick(m))
            self.rows[mode.value] = row
        self._paint()
        self.add_buttons("Adicionar", lambda: self.close(AddMode(self.choice.get())))

    def _pick(self, mode: AddMode) -> None:
        self.choice.set(mode.value)
        self._paint()

    def _paint(self) -> None:
        for value, row in self.rows.items():
            on = value == self.choice.get()
            row.configure(border_color=C["accent"] if on else C["surface"])


class AddLinkDialog(Dialog):
    """Devolve (nome, endereço) ou None. A validação fica com quem chamou,
    que pode chamar show_error() e mostrar de novo."""

    def __init__(self, master, *, name: str = "", url: str = "", error: str = ""):
        super().__init__(master, "Adicionar site", heading="Adicionar um site", width=440)
        self.paragraph("Para abrir direto do painel: portal da nota fiscal, banco, "
                       "fornecedor, cardápio on-line...", pady=(0, 12))
        ctk.CTkLabel(self.content, text="Endereço", font=theme.font(12), text_color=C["muted"]).pack(anchor="w")
        self.url = ctk.CTkEntry(self.content, height=36, font=theme.font(13),
                                placeholder_text="Ex.: www.nfe.fazenda.gov.br")
        self.url.pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(self.content, text="Nome no painel", font=theme.font(12), text_color=C["muted"]).pack(anchor="w")
        self.name = ctk.CTkEntry(self.content, height=36, font=theme.font(13),
                                 placeholder_text="Opcional. Ex.: Portal da NF-e")
        self.name.pack(fill="x", pady=(2, 4))
        if url:
            self.url.insert(0, url)
        if name:
            self.name.insert(0, name)
        self.error = ctk.CTkLabel(self.content, text=error, font=theme.font(12),
                                  text_color=C["danger"], anchor="w")
        if error:
            self.error.pack(anchor="w", pady=(4, 0))
        self.add_buttons("Adicionar site", lambda: self.close((self.name.get(), self.url.get())))
        self.after(50, self.url.focus_set)
