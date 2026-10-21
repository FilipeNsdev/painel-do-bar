from app.core import excel
from app.core.excel import ExcelError, parse_result
from app.core.library import AddMode

import pytest


def test_le_resultado_do_excel():
    r = parse_result('{"saved":["Contas.xlsx","Estoque.xlsx"],"read_only":[],"failed":[],'
                     '"excel_closed":true,"status":"ok"}')
    assert r.saved == ["Contas.xlsx", "Estoque.xlsx"]
    assert r.excel_closed


def test_powershell_manda_um_item_so_sem_lista():
    r = parse_result('{"saved":"Contas.xlsx","read_only":"Velha.xls","failed":null,"status":"ok"}')
    assert r.saved == ["Contas.xlsx"]
    assert r.read_only == ["Velha.xls"]
    assert r.failed == []
    assert not r.excel_closed


def test_excel_sem_planilhas_abertas_nao_e_erro():
    assert parse_result('{"saved":[],"status":"no_excel"}').saved == []


def test_excel_ocupado_vira_mensagem_pronta():
    with pytest.raises(ExcelError, match="Enter ou Esc"):
        parse_result('{"status":"busy"}')


def test_resposta_estranha_vira_mensagem_pronta():
    with pytest.raises(ExcelError):
        parse_result("")


def test_so_planilhas_abertas_contam(panel):
    for name in ("Contas.xlsx", "Cardápio.pdf", "Fechada.xlsx"):
        (panel.paths.files / name).write_bytes(b"x")
    (panel.paths.files / "~$Contas.xlsx").write_bytes(b"lock")
    (panel.paths.files / "~$Cardápio.pdf").write_bytes(b"lock")
    panel.library.sync()
    assert [i.target for i in panel.open_spreadsheets()] == ["Contas.xlsx"]


def test_manda_pasta_do_painel_e_atalhos_para_o_excel(panel, outside, monkeypatch):
    planilha = outside / "Banco.xlsx"
    planilha.write_bytes(b"x")
    pasta = outside / "Notas"
    pasta.mkdir()
    panel.library.add_paths([planilha, pasta], mode=AddMode.LINK)
    seen = {}
    monkeypatch.setattr(excel, "save_and_close",
                        lambda folders, files: seen.update(folders=folders, files=files) or excel.ExcelResult())
    panel.save_and_close_spreadsheets()
    assert seen["folders"] == [panel.paths.files, pasta]
    assert seen["files"] == [planilha]
