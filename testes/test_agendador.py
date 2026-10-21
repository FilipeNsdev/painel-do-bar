from datetime import datetime
from xml.etree import ElementTree as ET

import pytest

from app.core.scheduler import SchedulerError, build_task_xml, next_run

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def test_proxima_execucao():
    quarta = datetime(2026, 10, 21, 10, 0)
    assert next_run(6, "22:00", quarta) == datetime(2026, 10, 25, 22, 0)   # domingo
    assert next_run(2, "22:00", quarta) == datetime(2026, 10, 21, 22, 0)   # hoje mais tarde
    assert next_run(2, "09:00", quarta) == datetime(2026, 10, 28, 9, 0)    # hoje já passou


def test_horario_invalido():
    with pytest.raises(SchedulerError):
        next_run(0, "25:00")


def test_xml_da_tarefa():
    xml = build_task_xml(
        r"C:\Painel & Cia\PainelDoBar.exe", "--backup", 6, "22:00",
        working_dir=r"C:\Painel & Cia", user="BAR\\filipe",
        now=datetime(2026, 10, 21, 10, 0),
    )
    root = ET.fromstring(xml.split("\n", 1)[1])     # tira a linha <?xml?> (UTF-16)
    assert root.find(".//t:DaysOfWeek/t:Sunday", NS) is not None
    assert root.find(".//t:StartBoundary", NS).text == "2026-10-25T22:00:00"
    assert root.find(".//t:StartWhenAvailable", NS).text == "true"
    assert root.find(".//t:Command", NS).text == r"C:\Painel & Cia\PainelDoBar.exe"
    assert root.find(".//t:Arguments", NS).text == "--backup"
    assert root.find(".//t:UserId", NS).text == "BAR\\filipe"


def test_agendamento_recusado_desliga_a_opcao(panel, monkeypatch):
    from app.core import scheduler
    from app.core.models import Settings

    def recusa(*_a, **_k):
        raise SchedulerError("negado")

    monkeypatch.setattr(scheduler, "is_supported", lambda: True)
    monkeypatch.setattr(scheduler, "install", recusa)
    novo = Settings.from_dict(panel.settings.to_dict())
    novo.weekly_enabled = True
    with pytest.raises(SchedulerError):
        panel.save_settings(novo)
    assert panel.settings.weekly_enabled is False
    from app.core.panel import Panel
    assert Panel(panel.paths).settings.weekly_enabled is False
