import zipfile

from app.core.backup import apply_retention, backup_files_in
from app.core.library import AddMode
from app.core.models import BackupStatus, BackupTrigger


def _names(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        return set(zf.namelist())


def test_backup_inclui_arquivos_vinculados_e_configuracao(panel, outside, tmp_path):
    (panel.paths.files / "Contas a Pagar.xlsm").write_bytes(b"a" * 1000)
    sub = panel.paths.files / "Notas 2026"
    sub.mkdir()
    (sub / "nf1.xml").write_text("<nf/>", encoding="utf-8")
    linked = outside / "Cardápio.pdf"
    linked.write_bytes(b"pdf")
    panel.library.sync()
    panel.library.add_paths([linked], mode=AddMode.LINK)

    nuvem = tmp_path / "GoogleDrive" / "Backups Painel do Bar"
    nuvem.parent.mkdir()
    panel.settings.backup_destination = str(nuvem)

    rec = panel.run_backup(BackupTrigger.MANUAL)
    assert rec.status == BackupStatus.OK.value, rec.warnings
    assert rec.cloud_path and rec.local_path
    names = _names(rec.local_path)
    assert "Arquivos/Contas a Pagar.xlsm" in names
    assert "Arquivos/Notas 2026/nf1.xml" in names
    assert "Vinculados/Cardápio.pdf" in names
    assert "Sistema/config.json" in names
    assert "manifesto.json" in names and "LEIA-ME.txt" in names
    assert _names(rec.cloud_path) == names


def test_sem_nuvem_fica_local_com_aviso(panel):
    (panel.paths.files / "a.xlsx").write_bytes(b"x")
    panel.library.sync()
    rec = panel.run_backup(BackupTrigger.MANUAL)
    assert rec.status == BackupStatus.WARNING.value
    assert rec.local_path and not rec.cloud_path


def test_nuvem_desconectada_nao_perde_backup(panel, tmp_path):
    (panel.paths.files / "a.xlsx").write_bytes(b"x")
    panel.library.sync()
    panel.settings.backup_destination = str(tmp_path / "G_nao_existe" / "Backups")
    rec = panel.run_backup(BackupTrigger.SCHEDULED)
    assert rec.status == BackupStatus.WARNING.value
    assert rec.produced_zip and not rec.reached_cloud
    assert any("não está acessível" in w for w in rec.warnings)


def test_avisa_arquivo_aberto(panel, tmp_path):
    (panel.paths.files / "Contas.xlsx").write_bytes(b"x")
    (panel.paths.files / "~$Contas.xlsx").write_bytes(b"lock")
    panel.library.sync()
    panel.settings.backup_destination = str(tmp_path)
    rec = panel.run_backup(BackupTrigger.MANUAL)
    assert any("Contas.xlsx" in w and "aberto" in w for w in rec.warnings)
    assert "Arquivos/~$Contas.xlsx" not in _names(rec.local_path)


def test_item_fora_do_backup(panel, tmp_path):
    (panel.paths.files / "grande.zip").write_bytes(b"x")
    (panel.paths.files / "a.xlsx").write_bytes(b"x")
    panel.library.sync()
    big = next(i for i in panel.library.items if i.target == "grande.zip")
    panel.library.update(big.id, include_in_backup=False)
    panel.settings.backup_destination = str(tmp_path)
    rec = panel.run_backup(BackupTrigger.MANUAL)
    names = _names(rec.local_path)
    assert "Arquivos/a.xlsx" in names and "Arquivos/grande.zip" not in names


def test_retencao_mantem_os_mais_novos(tmp_path):
    for day in range(1, 8):
        (tmp_path / f"Backup_PainelDoBar_2026-10-0{day}_22h00.zip").write_bytes(b"z")
    (tmp_path / "outro arquivo.zip").write_bytes(b"nao mexer")
    removed = apply_retention(tmp_path, keep=3)
    assert len(removed) == 4
    left = [p.name for p in backup_files_in(tmp_path)]
    assert left == [f"Backup_PainelDoBar_2026-10-0{d}_22h00.zip" for d in (5, 6, 7)]
    assert (tmp_path / "outro arquivo.zip").exists()


def test_historico_registra(panel, tmp_path):
    (panel.paths.files / "a.xlsx").write_bytes(b"x")
    panel.library.sync()
    panel.settings.backup_destination = str(tmp_path)
    assert panel.history.is_overdue(7)
    panel.run_backup(BackupTrigger.MANUAL)
    assert panel.history.last().file_count == 1
    assert not panel.history.is_overdue(7)
