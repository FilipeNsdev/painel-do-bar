"""Editar um cartão: nome, descrição, foto, cor da capa e, conforme o tipo,
o endereço do site ou o local do arquivo vinculado.

Nada aqui renomeia ou altera o arquivo de verdade.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from app.core.file_types import badge_for, category_for
from app.core.images import PHOTO_EXTENSIONS, ImageError, prepare_photo
from app.core.library import LibraryError
from app.core.models import Item, ItemKind
from app.core.panel import Panel
from app.ui import art, theme
from app.ui.dialogs.base import Dialog, message
from app.ui.theme import C

PREVIEW = (300, 180)


class EditItemDialog(Dialog):
    def __init__(self, master, panel: Panel, item: Item):
        super().__init__(master, "Editar cartão", heading="Editar cartão", width=500)
        self.panel = panel
        self.item = item
        self.lib = panel.library
        self.path = self.lib.path_of(item)
        is_dir = bool(self.path and self.path.is_dir())
        self.category = category_for(item.target, is_dir=is_dir, is_link=item.kind is ItemKind.LINK)
        self.badge = badge_for(item.target, is_dir=is_dir, is_link=item.kind is ItemKind.LINK)

        self.photo_bytes: bytes | None = None
        self.clear_photo = False
        self.color = item.color
        self.new_target: Path | None = None

        self._build()
        self._refresh_preview()

    # ------------------------------------------------------------------ tela
    def _build(self) -> None:
        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill="x", pady=(4, 14))
        self.preview = ctk.CTkLabel(top, text="")
        self.preview.pack(side="left", anchor="n")

        side = ctk.CTkFrame(top, fg_color="transparent")
        side.pack(side="left", fill="y", padx=(16, 0), anchor="n")
        theme.secondary_button(side, "Escolher foto...", self._choose_photo, width=170).pack(anchor="w")
        self.remove_photo_btn = theme.link_button(side, "Tirar a foto e usar a capa", self._remove_photo)
        self.remove_photo_btn.pack(anchor="w", pady=(6, 14))

        ctk.CTkLabel(side, text="Cor da capa", font=theme.font(12), text_color=C["muted"]).pack(anchor="w")
        swatches = ctk.CTkFrame(side, fg_color="transparent")
        swatches.pack(anchor="w", pady=(4, 0))
        self.swatch_buttons: dict[str | None, ctk.CTkButton] = {}
        colors: list[str | None] = [None, *theme.CARD_COLORS]
        for i, color in enumerate(colors):
            fill = color or self.category.color
            b = ctk.CTkButton(
                swatches, text="A" if color is None else "", width=30, height=30, corner_radius=15,
                fg_color=fill, hover_color=fill, border_width=0, font=theme.font(11, "bold"),
                text_color=theme.FOAM, command=lambda c=color: self._set_color(c),
            )
            b.grid(row=i // 5, column=i % 5, padx=(0, 6), pady=(0, 6))
            self.swatch_buttons[color] = b
        ctk.CTkLabel(side, text="A = cor do tipo de arquivo", font=theme.font(11),
                     text_color=C["muted"]).pack(anchor="w")

        self.name_entry = self._field("Nome no painel", self.item.name)
        self.desc_entry = self._field(
            "Descrição", self.item.description,
            placeholder="Opcional. Ex.: lançar as contas toda segunda",
        )

        self.url_entry = None
        if self.item.kind is ItemKind.LINK:
            self.url_entry = self._field("Endereço do site", self.item.target)

        if self.item.kind is ItemKind.LINKED:
            row = ctk.CTkFrame(self.content, fg_color="transparent")
            row.pack(fill="x", pady=(2, 8))
            ctk.CTkLabel(row, text="Onde o arquivo fica", font=theme.font(12),
                         text_color=C["muted"]).pack(anchor="w")
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill="x")
            self.location_label = ctk.CTkLabel(line, text=self.item.target, font=theme.font(12), anchor="w",
                                         justify="left", wraplength=self.width - 110)
            self.location_label.pack(side="left", fill="x", expand=True)
            theme.link_button(line, "Procurar...", self._relink).pack(side="right")

        self.backup_var = ctk.BooleanVar(value=self.item.include_in_backup)
        if self.item.kind is not ItemKind.LINK:
            ctk.CTkSwitch(self.content, text="Incluir no backup", variable=self.backup_var,
                          font=theme.font(13)).pack(anchor="w", pady=(6, 10))

        if self.path is not None:
            self.paragraph(
                f"O arquivo continua se chamando “{self.path.name}”. "
                "Nome, foto e descrição mudam só aqui no painel.",
                size=12, pady=(4, 0),
            )

        self.add_buttons("Salvar alterações", self._save)

    def _field(self, label: str, value: str, placeholder: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(self.content, text=label, font=theme.font(12), text_color=C["muted"]).pack(anchor="w")
        entry = ctk.CTkEntry(self.content, height=36, font=theme.font(13), placeholder_text=placeholder)
        if value:
            entry.insert(0, value)
        entry.pack(fill="x", pady=(2, 10))
        return entry

    # ------------------------------------------------------------------ prévia
    def _current_base(self) -> Image.Image:
        if self.photo_bytes:
            with Image.open(BytesIO(self.photo_bytes)) as im:
                return im.convert("RGB").resize((PREVIEW[0] * art.SS, PREVIEW[1] * art.SS))
        if not self.clear_photo:
            path = self.lib.image_path(self.item)
            if path:
                ph = art.photo(path, PREVIEW)
                if ph is not None:
                    return ph
        return art.cover(self.color or self.category.color, self.badge, PREVIEW)

    def _refresh_preview(self) -> None:
        self._preview_img = art.card_image(self._current_base(), PREVIEW, bg=C["bg"])
        self.preview.configure(image=self._preview_img)
        has_photo = bool(self.photo_bytes) or (not self.clear_photo and self.item.image)
        self.remove_photo_btn.configure(state="normal" if has_photo else "disabled",
                                        text_color=C["text"] if has_photo else C["muted"])
        for color, b in self.swatch_buttons.items():
            selected = color == self.color
            b.configure(border_width=3 if selected else 0, border_color=C["text"])

    # ------------------------------------------------------------------ ações
    def _choose_photo(self) -> None:
        patterns = " ".join(f"*{e}" for e in PHOTO_EXTENSIONS)
        chosen = filedialog.askopenfilename(
            parent=self, title="Escolher foto do cartão",
            filetypes=[("Imagens", patterns), ("Todos os arquivos", "*.*")],
        )
        if not chosen:
            return
        try:
            self.photo_bytes = prepare_photo(Path(chosen))
        except ImageError as exc:
            message(self, "Foto não aceita", str(exc))
            return
        self.clear_photo = False
        self._refresh_preview()

    def _remove_photo(self) -> None:
        self.photo_bytes = None
        self.clear_photo = True
        self._refresh_preview()

    def _set_color(self, color: str | None) -> None:
        self.color = color          # só aparece quando o cartão não tem foto
        self._refresh_preview()

    def _relink(self) -> None:
        path = self.lib.path_of(self.item)
        initial = str(path.parent) if path and path.parent.exists() else None
        chosen = filedialog.askopenfilename(parent=self, title="Onde está o arquivo agora?",
                                            initialdir=initial)
        if chosen:
            self.new_target = Path(chosen)
            self.location_label.configure(text=str(self.new_target))

    def _save(self) -> None:
        try:
            if self.new_target is not None:
                self.lib.relink(self.item.id, self.new_target)
            self.lib.update(
                self.item.id,
                name=self.name_entry.get(),
                description=self.desc_entry.get(),
                color=self.color,
                include_in_backup=self.backup_var.get() if self.item.kind is not ItemKind.LINK else None,
                target=self.url_entry.get() if self.url_entry is not None else None,
            )
            if self.clear_photo and not self.photo_bytes:
                self.lib.clear_image(self.item.id)
            if self.photo_bytes:
                self.lib.set_image(self.item.id, self.photo_bytes, "jpg")
        except LibraryError as exc:
            message(self, "Não deu para salvar", str(exc))
            return
        self.close(True)
