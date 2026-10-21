"""Salva e fecha no Excel as planilhas do painel, antes do backup pelo botão.

Conversa com o Excel que já está aberto (via PowerShell e COM, o mesmo
caminho do atalho na Área de Trabalho). Só mexe nas pastas de trabalho que
são do painel: o que for de fora fica aberto do jeito que está. O Excel só
é fechado de vez se não sobrar nenhuma outra planilha aberta nele.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000
_TIMEOUT_S = 120


class ExcelError(Exception):
    """Erro com mensagem pronta para mostrar ao usuário."""


@dataclass
class ExcelResult:
    saved: list[str] = field(default_factory=list)       # salvas e fechadas
    read_only: list[str] = field(default_factory=list)   # abertas só para leitura: ficam abertas
    failed: list[str] = field(default_factory=list)      # não deu para salvar: continuam abertas
    excel_closed: bool = False                           # o Excel foi fechado de vez


# O script roda no PowerShell 5.1 do Windows. Recebe as pastas e arquivos do
# painel em JSON (base64, para os acentos chegarem certos) e devolve JSON.
_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$cfg = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:PAINEL_EXCEL)) | ConvertFrom-Json
$folders = @($cfg.folders | ForEach-Object { $_.TrimEnd('\') + '\' })
$files = @($cfg.files)
$out = @{ saved = @(); read_only = @(); failed = @(); excel_closed = $false; status = 'ok' }

function Is-Panel([string]$p) {
    foreach ($f in $files) { if ($p -ieq $f) { return $true } }
    foreach ($d in $folders) { if ($p.StartsWith($d, [StringComparison]::OrdinalIgnoreCase)) { return $true } }
    return $false
}

for ($round = 0; $round -lt 5; $round++) {
    try { $xl = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application') }
    catch { $out.status = if ($round -eq 0) { 'no_excel' } else { 'ok' }; break }
    try { $ready = $xl.Ready } catch { $ready = $false }
    if (-not $ready) { $out.status = 'busy'; break }
    $xl.DisplayAlerts = $false
    $closed = 0
    foreach ($wb in @($xl.Workbooks)) {
        $path = $wb.FullName
        if (-not (Is-Panel $path)) { continue }
        try {
            if ($wb.ReadOnly) { $out.read_only += $wb.Name; continue }   # não dá para salvar: não mexe
            $wb.Save()
            $out.saved += $wb.Name
            $wb.Close($false)
            $closed++
        } catch { $out.failed += $wb.Name }
    }
    # a pasta de macros pessoal (PERSONAL.XLSB) fica escondida e não conta
    $visible = @($xl.Workbooks | Where-Object { $_.Windows.Count -gt 0 -and $_.Windows.Item(1).Visible })
    if ($visible.Count -eq 0) { $xl.Quit(); $out.excel_closed = $true }
    else { $xl.DisplayAlerts = $true }
    # solta todas as referências, senão o processo do Excel fica vivo escondido
    $wb = $null; $visible = $null
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($xl)
    $xl = $null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect()
    if ($closed -eq 0 -or -not $out.excel_closed) { break }   # outro Excel aberto? tenta de novo
    Start-Sleep -Milliseconds 800
}
$out | ConvertTo-Json -Compress
"""


def is_spreadsheet(path: Path) -> bool:
    return path.suffix.lower() in {".xlsx", ".xlsm", ".xlsb", ".xls", ".xltx", ".xltm", ".csv"}


def parse_result(stdout: str) -> ExcelResult:
    """Lê o JSON devolvido pelo script e transforma em resultado ou erro."""
    try:
        data = json.loads(stdout.strip().splitlines()[-1])
    except (IndexError, ValueError) as exc:
        raise ExcelError("Não consegui falar com o Excel para salvar as planilhas.") from exc
    if data.get("status") == "busy":
        raise ExcelError(
            "O Excel está ocupado, provavelmente com uma célula sendo editada. "
            "Aperte Enter ou Esc no Excel e clique em fazer backup de novo."
        )

    def names(key: str) -> list[str]:
        value = data.get(key) or []
        return [value] if isinstance(value, str) else list(value)   # PowerShell manda 1 item sem lista

    return ExcelResult(saved=names("saved"), read_only=names("read_only"),
                       failed=names("failed"), excel_closed=bool(data.get("excel_closed")))


def save_and_close(folders: list[Path], files: list[Path]) -> ExcelResult:
    """Salva e fecha as planilhas abertas que estão nessas pastas ou são esses arquivos."""
    if os.name != "nt":
        return ExcelResult()
    cfg = json.dumps({"folders": [str(f) for f in folders], "files": [str(f) for f in files]})
    env = dict(os.environ, PAINEL_EXCEL=base64.b64encode(cfg.encode("utf-8")).decode("ascii"))
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT],
            capture_output=True, env=env, timeout=_TIMEOUT_S,
            creationflags=_CREATE_NO_WINDOW, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExcelError("O Excel demorou demais para responder. Salve e feche as planilhas "
                         "e tente de novo.") from exc
    return parse_result(proc.stdout.decode("utf-8", errors="replace"))
