"""Backup semanal pelo Agendador de Tarefas do Windows.

O painel registra uma tarefa que abre o próprio programa com o argumento
--backup no dia e hora escolhidos. Nesse modo ele faz o backup sem abrir
janela e mostra só um aviso no canto da tela.

A tarefa é criada a partir de um XML porque é a única forma de ligar a opção
"executar assim que possível se um horário for perdido": se o computador
estiver desligado no horário, o backup roda quando ele for ligado.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from app import APP_ID
from app.core.paths import install_dir, is_frozen

TASK_NAME = f"{APP_ID} - Backup semanal"
SILENT_ARG = "--backup"

_XML_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_CREATE_NO_WINDOW = 0x08000000


class SchedulerError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


def is_supported() -> bool:
    return os.name == "nt"


def parse_time(hhmm: str) -> tuple[int, int]:
    m = _TIME_RE.match(hhmm.strip())
    if not m:
        raise SchedulerError("Horário inválido. Use o formato 22:00.")
    return int(m.group(1)), int(m.group(2))


def next_run(day: int, hhmm: str, now: datetime | None = None) -> datetime:
    """Próxima data/hora em que o backup semanal vai rodar (0 = segunda)."""
    now = now or datetime.now()
    hour, minute = parse_time(hhmm)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    candidate += timedelta(days=(day - now.weekday()) % 7)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def launch_command(*args: str) -> tuple[str, str]:
    """(programa, argumentos) para abrir o próprio painel."""
    if is_frozen():
        return sys.executable, subprocess.list2cmdline(list(args))
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    program = str(pythonw if pythonw.exists() else sys.executable)
    script = str(install_dir() / "main.py")
    return program, subprocess.list2cmdline([script, *args])


def _current_user() -> str | None:
    user = os.environ.get("USERNAME")
    domain = os.environ.get("USERDOMAIN")
    if user and domain:
        return f"{domain}\\{user}"
    return user


def build_task_xml(
    program: str,
    arguments: str,
    day: int,
    hhmm: str,
    *,
    working_dir: str,
    user: str | None = None,
    now: datetime | None = None,
) -> str:
    start = next_run(day, hhmm, now)
    user_xml = f"\n      <UserId>{escape(user)}</UserId>" if user else ""
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Backup semanal dos arquivos do Painel do Bar.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start:%Y-%m-%dT%H:%M:%S}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
          <{_XML_DAYS[day]} />
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">{user_xml}
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(program)}</Command>
      <Arguments>{escape(arguments)}</Arguments>
      <WorkingDirectory>{escape(working_dir)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def _oem_encoding() -> str:
    try:
        import ctypes

        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return "cp850"


def _schtasks(*args: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["schtasks", *args],
        capture_output=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )
    enc = _oem_encoding()
    proc.stdout = proc.stdout.decode(enc, errors="replace") if proc.stdout else ""
    proc.stderr = proc.stderr.decode(enc, errors="replace") if proc.stderr else ""
    return proc


def install(day: int, hhmm: str) -> None:
    """Cria ou atualiza a tarefa semanal (sobrescreve se já existir)."""
    if not is_supported():
        raise SchedulerError("O backup automático só funciona no Windows.")
    program, arguments = launch_command(SILENT_ARG)
    xml = build_task_xml(
        program, arguments, day, hhmm,
        working_dir=str(Path(program).parent if is_frozen() else install_dir()),
        user=_current_user(),
    )
    fd, tmp = tempfile.mkstemp(suffix=".xml", prefix="painel_tarefa_")
    os.close(fd)
    try:
        Path(tmp).write_text(xml, encoding="utf-16")
        proc = _schtasks("/Create", "/TN", TASK_NAME, "/XML", tmp, "/F")
    finally:
        Path(tmp).unlink(missing_ok=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise SchedulerError(
            "O Windows não aceitou criar o backup automático."
            + (f"\n\nDetalhe: {detail}" if detail else "")
        )


def uninstall() -> None:
    if not is_supported() or not is_installed():
        return
    proc = _schtasks("/Delete", "/TN", TASK_NAME, "/F")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise SchedulerError(
            "Não consegui desligar o backup automático."
            + (f"\n\nDetalhe: {detail}" if detail else "")
        )


def is_installed() -> bool:
    if not is_supported():
        return False
    return _schtasks("/Query", "/TN", TASK_NAME).returncode == 0
