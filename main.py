"""Painel do Bar.

    PainelDoBar.exe            abre o painel
    PainelDoBar.exe --backup   faz o backup sem abrir janela (usado pelo backup semanal)
"""

import sys


def main() -> int:
    from app.core.scheduler import SILENT_ARG

    if SILENT_ARG in sys.argv[1:]:
        from app.silent import run_scheduled_backup

        return run_scheduled_backup()

    from app.ui.main_window import run_app

    run_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
