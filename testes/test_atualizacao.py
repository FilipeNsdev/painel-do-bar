from pathlib import Path

from app.core import updater
from app.core.updater import is_newer, parse_release, parse_version


def _release(tag="v1.1.0", assets=None, **extra):
    if assets is None:
        assets = [{"name": "PainelDoBar.exe", "size": 123,
                   "browser_download_url": "https://github.com/x/y/releases/download/v1.1.0/PainelDoBar.exe"}]
    return {"tag_name": tag, "body": "Salva as planilhas\nantes do backup.", "assets": assets, **extra}


def test_le_numero_da_versao():
    assert parse_version("v1.2.10") == (1, 2, 10)
    assert parse_version("1.0") == (1, 0)
    assert parse_version("nada") == (0,)


def test_compara_versoes_como_numeros():
    assert is_newer("v1.0.10", "1.0.9")
    assert is_newer("1.1", "1.0.5")
    assert not is_newer("1.0", "1.0.0")
    assert not is_newer("v0.9.9", "1.0.0")
    assert not is_newer("lixo", "1.0.0")


def test_oferece_versao_mais_nova():
    info = parse_release(_release(), current="1.0.0")
    assert info.version == "1.1.0"
    assert info.size == 123
    assert info.notes == "Salva as planilhas antes do backup."


def test_mesma_versao_ou_mais_velha_nao_oferece():
    assert parse_release(_release("v1.0.0"), current="1.0.0") is None
    assert parse_release(_release("v0.9.0"), current="1.0.0") is None


def test_release_sem_o_exe_ou_rascunho_nao_oferece():
    assert parse_release(_release(assets=[]), current="1.0.0") is None
    assert parse_release(_release(draft=True), current="1.0.0") is None
    assert parse_release(_release(prerelease=True), current="1.0.0") is None


def test_sem_internet_nao_e_erro(monkeypatch):
    def offline(*_a, **_k):
        raise OSError("sem rede")
    monkeypatch.setattr(updater.urllib.request, "urlopen", offline)
    assert updater.check(current="1.0.0") is None


def test_rodando_pelo_codigo_nunca_oferece(panel):
    assert panel.check_update() is None


def test_script_de_troca_guarda_o_antigo_e_reabre():
    s = updater.swap_script(Path(r"C:\Painel D'Bar\PainelDoBar.new.exe"),
                            Path(r"C:\Painel D'Bar\PainelDoBar.exe"), [10, 20])
    assert "@(10,20)" in s
    assert r"'C:\Painel D''Bar\PainelDoBar.old.exe'" in s      # aspas escapadas
    assert "Start-Process -FilePath $cur" in s
    assert "PYINSTALLER_RESET_ENVIRONMENT" in s


def test_ambiente_do_ajudante_sem_variaveis_do_exe():
    env = updater.clean_env({"PATH": "x", "_PYI_ARCHIVE_FILE": "a", "_PYI_PARENT_PROCESS_LEVEL": "1",
                             "_MEIPASS2": "b", "PAINEL_DADOS": "d"})
    assert env == {"PATH": "x", "PAINEL_DADOS": "d", "PYINSTALLER_RESET_ENVIRONMENT": "1"}


def test_limpa_sobras_de_atualizacao(tmp_path):
    for name in ("PainelDoBar.old.exe", "PainelDoBar.new.exe", "PainelDoBar.exe"):
        (tmp_path / name).write_bytes(b"MZ")
    updater.cleanup(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["PainelDoBar.exe"]
