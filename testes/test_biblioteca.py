from app.core.library import AddMode, LibraryError, pretty_name
from app.core.models import ItemKind

import pytest


def test_arquivo_colocado_na_pasta_aparece_sozinho(panel):
    (panel.paths.files / "controle_precos.xlsx").write_bytes(b"x")
    assert panel.library.sync() is True
    [item] = panel.library.visible_items()
    assert item.kind is ItemKind.MANAGED
    assert item.name == "Controle precos"


def test_ignora_temporarios_e_travas(panel):
    files = panel.paths.files
    for name in ("~$Contas.xlsx", ".~lock.Contas.xlsx#", "A1B2C3D4", "desktop.ini", "x.tmp"):
        (files / name).write_bytes(b"x")
    panel.library.sync()
    assert panel.library.visible_items() == []


def test_renomear_no_painel_nao_mexe_no_arquivo(panel):
    real = panel.paths.files / "Contas a Pagar.xlsm"
    real.write_bytes(b"x")
    panel.library.sync()
    item = panel.library.visible_items()[0]
    panel.library.update(item.id, name="Contas do mês", description="Lançar toda segunda")
    assert real.exists()
    assert panel.library.get(item.id).name == "Contas do mês"


def test_nome_vazio_nao_e_aceito(panel):
    (panel.paths.files / "a.xlsx").write_bytes(b"x")
    panel.library.sync()
    item = panel.library.visible_items()[0]
    with pytest.raises(LibraryError):
        panel.library.update(item.id, name="   ")


def test_arquivo_que_some_e_volta_mantem_nome_e_foto(panel):
    real = panel.paths.files / "Preços.xlsx"
    real.write_bytes(b"x")
    panel.library.sync()
    item = panel.library.visible_items()[0]
    panel.library.update(item.id, name="Tabela de preços")
    real.unlink()
    panel.library.sync()
    assert panel.library.visible_items() == []
    real.write_bytes(b"y")          # o Excel apaga e recria ao salvar
    panel.library.sync()
    [back] = panel.library.visible_items()
    assert back.id == item.id and back.name == "Tabela de preços"


def test_adicionar_movendo(panel, outside):
    src = outside / "Estoque.xlsx"
    src.write_bytes(b"x")
    res = panel.library.add_paths([src], mode=AddMode.MOVE)
    assert len(res.added) == 1 and not src.exists()
    assert (panel.paths.files / "Estoque.xlsx").exists()


def test_adicionar_copiando_mantem_original(panel, outside):
    src = outside / "Estoque.xlsx"
    src.write_bytes(b"x")
    panel.library.add_paths([src], mode=AddMode.COPY)
    assert src.exists() and (panel.paths.files / "Estoque.xlsx").exists()


def test_copia_com_mesmo_nome_ganha_numero(panel, outside):
    (panel.paths.files / "Estoque.xlsx").write_bytes(b"velho")
    panel.library.sync()
    src = outside / "Estoque.xlsx"
    src.write_bytes(b"novo")
    panel.library.add_paths([src], mode=AddMode.COPY)
    assert (panel.paths.files / "Estoque (2).xlsx").read_bytes() == b"novo"


def test_atalho_nao_duplica(panel, outside):
    src = outside / "NF.pdf"
    src.write_bytes(b"x")
    panel.library.add_paths([src], mode=AddMode.LINK)
    res = panel.library.add_paths([src], mode=AddMode.LINK)
    assert res.added == [] and res.skipped
    [item] = panel.library.visible_items()
    assert item.kind is ItemKind.LINKED


def test_remover_move_para_removidos(panel):
    real = panel.paths.files / "Velha.xlsx"
    real.write_bytes(b"x")
    panel.library.sync()
    item = panel.library.visible_items()[0]
    moved = panel.library.remove(item.id)
    assert not real.exists() and moved.exists()
    assert moved.parent == panel.paths.removed
    panel.library.sync()
    assert panel.library.visible_items() == []


def test_remover_atalho_nao_apaga_original(panel, outside):
    src = outside / "NF.pdf"
    src.write_bytes(b"x")
    panel.library.add_paths([src], mode=AddMode.LINK)
    item = panel.library.visible_items()[0]
    panel.library.remove(item.id)
    assert src.exists() and panel.library.visible_items() == []


def test_reordenar(panel):
    for n in ("a.xlsx", "b.xlsx", "c.xlsx"):
        (panel.paths.files / n).write_bytes(b"x")
    panel.library.sync()
    a, b, c = panel.library.visible_items()
    panel.library.move(c.id, 0)
    assert [i.id for i in panel.library.visible_items()] == [c.id, a.id, b.id]


def test_detecta_arquivo_aberto(panel):
    (panel.paths.files / "Contas a Pagar.xlsm").write_bytes(b"x")
    panel.library.sync()
    item = panel.library.visible_items()[0]
    assert panel.library.open_item_ids() == set()
    (panel.paths.files / "~$Contas a Pagar.xlsm").write_bytes(b"lock")
    assert panel.library.open_item_ids() == {item.id}


def test_impressao_digital_muda_quando_arquivo_muda(panel):
    before = panel.library.fingerprint()
    (panel.paths.files / "novo.pdf").write_bytes(b"x")
    assert panel.library.fingerprint() != before


def test_site(panel):
    item = panel.library.add_link("", "ifood.com.br")
    assert item.target == "https://ifood.com.br"
    with pytest.raises(LibraryError):
        panel.library.add_link("x", "nao é site")


def test_configuracao_sobrevive_a_reabrir(panel):
    (panel.paths.files / "a.xlsx").write_bytes(b"x")
    panel.library.sync()
    item = panel.library.visible_items()[0]
    panel.library.update(item.id, name="Planilha A")
    from app.core.panel import Panel
    again = Panel(panel.paths)
    assert again.library.get(item.id).name == "Planilha A"


def test_nome_bonito():
    assert pretty_name("controle_precos.xlsx") == "Controle precos"
    assert pretty_name("Contas a Pagar.xlsm") == "Contas a Pagar"


def test_aparencia_fica_guardada_na_hora(panel):
    panel.set_theme("escuro")
    from app.core.panel import Panel
    assert Panel(panel.paths).settings.theme == "escuro"      # abre de novo e continua escura
    with pytest.raises(ValueError):
        panel.set_theme("roxo")
