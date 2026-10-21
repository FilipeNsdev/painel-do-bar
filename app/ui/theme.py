"""Visual do painel: cores, fontes e medidas, tudo num lugar só.

Identidade do Bar do Sabão, a mesma do Conciliador: branco limpo, texto
quase preto e uma cor só, o vermelho da camisa do Sabão (o da logo), nos
botões principais e na faixa do topo. O resto é neutro.

Regras da casa: superfícies separadas por um degrau de tom (sem linhas
nem sombras), botões e campos sempre redondos (formato de pílula) e o
vermelho só onde há ação.

Cada cor é um par (modo claro, modo escuro). Para mudar o visual do painel
inteiro, basta mexer aqui.
"""

from __future__ import annotations

import sys

import customtkinter as ctk

# --------------------------------------------------------------------------- cores
C = {
    "bg":            ("#ECEEF1", "#111113"),
    "surface":       ("#FFFFFF", "#1A1A1D"),
    "surface_hover": ("#F7F8F9", "#202024"),
    "field":         ("#F1F2F4", "#232327"),
    "chip":          ("#DFE1E5", "#26262A"),
    "chip_hover":    ("#D3D6DB", "#303035"),
    "border":        ("#C9CBD1", "#36363C"),     # só em campos de texto
    "knob":          ("#FFFFFF", "#D9D9DE"),     # bolinha das chaves liga/desliga
    "text":          ("#0B0B0D", "#EDEDF0"),
    "muted":         ("#55555D", "#A0A0A8"),
    # destaque: o vermelho da camisa
    "accent":        ("#C8102E", "#E0344C"),
    "accent_hover":  ("#A90D26", "#EF4A61"),
    "on_accent":     ("#FFFFFF", "#FFFFFF"),
    # estados
    "danger":        ("#9B1C1C", "#FF6B6B"),
    "danger_hover":  ("#7F1717", "#FF8585"),
    "on_danger":     ("#FFFFFF", "#2A0E07"),
    "ok":            ("#1A7F45", "#4CC38A"),
    "warn":          ("#9A5B00", "#F0B54A"),
    # aviso rápido (toast): tinta escura no claro, clara no escuro
    "toast":         ("#0B0B0D", "#EDEDF0"),
    "on_toast":      ("#FFFFFF", "#111113"),
}

# Texto e bolhas de sabão sobre as capas coloridas.
FOAM = "#FFFFFF"

# Cores para quem quiser pintar a capa de um cartão (sem foto).
CARD_COLORS = [
    "#22604A", "#2D5887", "#A3402F", "#B0612A",
    "#5F4E86", "#226D7A", "#8A6C33", "#3A3A40",
]

# --------------------------------------------------------------------------- medidas
CARD_MIN_WIDTH = 230     # os cartões esticam entre esses dois tamanhos
CARD_MAX_WIDTH = 300     # para preencher a largura da janela
CARD_PAD = 10
CARD_GAP = 16
COVER_RATIO = 0.6        # capa e foto na proporção 5:3
RADIUS_CARD = 16
ANIM_MS = 240            # duração das animações dos cartões
ANIM_FRAME_MS = 12       # um quadro a cada 12 ms (cerca de 80 por segundo)
MENU_FADE_MS = 120       # o menu dos três pontinhos aparece esmaecendo
RADIUS_MENU = 12
RADIUS_COVER = 10
CONTROL_HEIGHT = 36
RADIUS_CONTROL = CONTROL_HEIGHT // 2   # pílula: metade da altura


def cover_size(card_width: int) -> tuple[int, int]:
    w = card_width - 2 * CARD_PAD
    return w, round(w * COVER_RATIO)

# --------------------------------------------------------------------------- fontes
UI_FAMILY = "Segoe UI" if sys.platform == "win32" else "Inter"   # uma família só


def title_font(size: int = 26) -> ctk.CTkFont:
    """Nome do painel e títulos grandes."""
    return ctk.CTkFont(family=UI_FAMILY, size=size, weight="bold")


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=UI_FAMILY, size=size, weight=weight)


# --------------------------------------------------------------------------- tema do CustomTkinter
APPEARANCE = {"auto": "system", "claro": "light", "escuro": "dark"}


def apply_theme(appearance: str) -> None:
    """Aplica a paleta aos componentes padrão do CustomTkinter."""
    # Ao trocar claro/escuro, o CustomTkinter esconde e mostra cada janela para
    # repintar a barra de título. Num diálogo aberto isso some com ele e deixa o
    # painel travado atrás. A barra de título é pintada por style_titlebar.
    ctk.CTk._deactivate_windows_window_header_manipulation = True
    ctk.CTkToplevel._deactivate_windows_window_header_manipulation = True
    ctk.set_appearance_mode(APPEARANCE.get(appearance, "system"))
    ctk.set_default_color_theme("blue")
    t = ctk.ThemeManager.theme
    t["CTk"]["fg_color"] = list(C["bg"])
    t["CTkToplevel"]["fg_color"] = list(C["bg"])
    t["CTkFrame"].update(fg_color=list(C["surface"]), top_fg_color=list(C["surface"]),
                         border_color=list(C["border"]), corner_radius=RADIUS_CARD)
    t["CTkButton"].update(fg_color=list(C["accent"]), hover_color=list(C["accent_hover"]),
                          text_color=list(C["on_accent"]), border_color=list(C["border"]),
                          corner_radius=RADIUS_CONTROL)
    t["CTkLabel"]["text_color"] = list(C["text"])
    t["CTkEntry"].update(fg_color=list(C["field"]), border_color=list(C["border"]),
                         text_color=list(C["text"]), placeholder_text_color=list(C["muted"]),
                         border_width=1, corner_radius=RADIUS_CONTROL)
    for name in ("CTkCheckBox", "CTkRadioButton"):
        t[name].update(fg_color=list(C["accent"]), hover_color=list(C["accent_hover"]),
                       border_color=list(C["muted"]), text_color=list(C["text"]))
    t["CTkCheckBox"]["checkmark_color"] = list(C["on_accent"])
    t["CTkSwitch"].update(progress_color=list(C["accent"]), fg_color=list(C["chip_hover"]),
                          button_color=list(C["knob"]), button_hover_color=list(C["knob"]),
                          text_color=list(C["text"]))
    t["CTkOptionMenu"].update(fg_color=list(C["field"]), button_color=list(C["chip"]),
                              button_hover_color=list(C["chip_hover"]), text_color=list(C["text"]),
                              corner_radius=RADIUS_CONTROL)
    # seletor: a opção escolhida vira uma pílula clara sobre o trilho cinza
    t["CTkSegmentedButton"].update(fg_color=list(C["chip"]), selected_color=list(C["surface"]),
                                   selected_hover_color=list(C["surface"]),
                                   unselected_color=list(C["chip"]),
                                   unselected_hover_color=list(C["chip_hover"]),
                                   text_color=list(C["text"]), corner_radius=RADIUS_CONTROL)
    t["CTkProgressBar"].update(fg_color=list(C["chip"]), progress_color=list(C["accent"]))
    t["CTkScrollbar"].update(button_color=list(C["chip"]), button_hover_color=list(C["chip_hover"]))
    t["DropdownMenu"].update(fg_color=list(C["surface"]), hover_color=list(C["chip"]),
                             text_color=list(C["text"]))


def pick(color: tuple[str, str] | str) -> str:
    """Escolhe a cor do par conforme o modo atual (para widgets do tkinter puro)."""
    if isinstance(color, str):
        return color
    return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]


# --------------------------------------------------------------------------- botões prontos
def primary_button(master, text: str, command, **kw) -> ctk.CTkButton:
    kw.setdefault("height", CONTROL_HEIGHT)
    return ctk.CTkButton(master, text=text, command=command, font=font(13, "bold"), **kw)


def secondary_button(master, text: str, command, **kw) -> ctk.CTkButton:
    kw.setdefault("height", CONTROL_HEIGHT)
    return ctk.CTkButton(
        master, text=text, command=command, font=font(13),
        fg_color=C["chip"], hover_color=C["chip_hover"], text_color=C["text"], **kw,
    )


def danger_button(master, text: str, command, **kw) -> ctk.CTkButton:
    kw.setdefault("height", CONTROL_HEIGHT)
    return ctk.CTkButton(
        master, text=text, command=command, font=font(13, "bold"),
        fg_color=C["danger"], hover_color=C["danger_hover"], text_color=C["on_danger"], **kw,
    )


def switch(master, **kw) -> ctk.CTkSwitch:
    """Chave liga/desliga com um aro na cor do trilho: a bolinha aparece em qualquer fundo."""
    kw.setdefault("border_color", C["chip_hover"])
    return ctk.CTkSwitch(master, **kw)


def link_button(master, text: str, command, color=None, **kw) -> ctk.CTkButton:
    """Botão que parece um link (texto sublinhado, sem fundo)."""
    kw.setdefault("height", 22)
    kw.setdefault("width", 0)
    return ctk.CTkButton(
        master, text=text, command=command, font=ctk.CTkFont(family=UI_FAMILY, size=12, underline=True),
        fg_color="transparent", hover=False, text_color=color or C["text"],
        border_spacing=0, **kw,
    )
