# -*- mode: python ; coding: utf-8 -*-
# Receita do PyInstaller para gerar o PainelDoBar.exe (um arquivo só, sem janela preta).
# Quem usa este arquivo é o gerar_exe.bat; não precisa rodar à mão.

import os
import sys

from PyInstaller.utils.hooks import collect_data_files

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "assets"), "assets")]
datas += collect_data_files("customtkinter")      # temas e ícones do CustomTkinter

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=["darkdetect", "PIL._tkinter_finder", "PIL.ImageTk"],   # o PyInstaller não acha sozinho
    excludes=["pytest", "unittest", "pydoc", "test"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PainelDoBar",
    console=False,
    debug=False,
    strip=False,
    upx=False,                       # UPX costuma assustar antivírus
    icon=os.path.join(ROOT, "assets", "icone.ico"),
    version=os.path.join(SPECPATH, "versao_windows.txt") if sys.platform == "win32" else None,
)
