import pytest

from app.core.panel import Panel
from app.core.paths import AppPaths


@pytest.fixture
def panel(tmp_path):
    return Panel(AppPaths(tmp_path / "Dados").ensure())


@pytest.fixture
def outside(tmp_path):
    """Uma pasta qualquer do computador, fora do painel."""
    folder = tmp_path / "Documentos"
    folder.mkdir()
    return folder
