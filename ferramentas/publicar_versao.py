"""Publica uma versão nova do painel no GitHub.

    python ferramentas/publicar_versao.py 1.1.0 "Salva as planilhas antes do backup."

Faz, nesta ordem, e para no primeiro problema:
  1. troca o número da versão em app/__init__.py e empacotamento/versao_windows.txt
  2. roda os testes
  3. gera o dist/PainelDoBar.exe (gerar_exe.bat)
  4. grava no Git (commit + etiqueta v1.1.0) e envia para o GitHub
  5. cria o "release" no GitHub com o PainelDoBar.exe anexado

Os painéis instalados procuram esse release ao abrir e oferecem atualizar.
O login do GitHub é o mesmo que o Git já usa neste computador.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import UPDATE_REPO, __version__  # noqa: E402
from app.core.updater import ASSET_NAME, is_newer  # noqa: E402


class Parar(Exception):
    """Para a publicação com uma mensagem em português."""


def passo(texto: str) -> None:
    print(f"\n== {texto}")


def rodar(*cmd: str, **kw) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=ROOT, **kw)
    if proc.returncode != 0:
        raise Parar(f"O comando falhou: {' '.join(cmd)}")
    return proc


def git(*args: str) -> str:
    return rodar("git", *args, capture_output=True, text=True, encoding="utf-8").stdout.strip()


# --------------------------------------------------------------------------- 1. versão
def trocar_versao(nova: str) -> None:
    init = ROOT / "app" / "__init__.py"
    s = init.read_text(encoding="utf-8")
    init.write_text(re.sub(r'__version__ = "[^"]*"', f'__version__ = "{nova}"', s), encoding="utf-8")

    numeros = ", ".join((nova.split(".") + ["0"] * 4)[:4])
    info = ROOT / "empacotamento" / "versao_windows.txt"
    s = info.read_text(encoding="utf-8")
    s = re.sub(r"(filevers|prodvers)=\([^)]*\)", rf"\1=({numeros})", s)
    s = re.sub(r"StringStruct\('(FileVersion|ProductVersion)', '[^']*'\)", rf"StringStruct('\1', '{nova}')", s)
    info.write_text(s, encoding="utf-8")


# --------------------------------------------------------------------------- 5. GitHub
def token_do_git() -> str:
    """Pega o login que o Git já guardou para o github.com (Gerenciador de Credenciais)."""
    proc = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                          capture_output=True, text=True, cwd=ROOT)
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise Parar("Não achei o login do GitHub. Faça um 'git push' uma vez para o Git pedir o login.")


def api(metodo: str, url: str, token: str, dados: bytes | None = None,
        tipo: str = "application/json") -> dict:
    req = urllib.request.Request(url, data=dados, method=metodo, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "Content-Type": tipo, "User-Agent": "PainelDoBar-publicar",
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise Parar(f"O GitHub recusou ({exc.code}): {exc.read().decode('utf-8', 'replace')[:300]}") from exc


def criar_release(versao: str, notas: str, exe: Path) -> str:
    token = token_do_git()
    rel = api("POST", f"https://api.github.com/repos/{UPDATE_REPO}/releases", token,
              json.dumps({"tag_name": f"v{versao}", "name": f"Versão {versao}", "body": notas}).encode())
    upload = rel["upload_url"].split("{")[0] + f"?name={ASSET_NAME}"
    api("POST", upload, token, exe.read_bytes(), tipo="application/octet-stream")
    return rel["html_url"]


# --------------------------------------------------------------------------- tudo
def publicar(nova: str, notas: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", nova):
        raise Parar("Use o formato 1.2.3 para a versão.")
    if not is_newer(nova, __version__):
        raise Parar(f"A versão nova ({nova}) precisa ser maior que a atual ({__version__}).")
    if not notas.strip():
        raise Parar("Escreva numa frase o que mudou. Ela aparece para quem for atualizar.")
    if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
        raise Parar("Publique a partir do ramo main.")

    passo(f"Versão {__version__} -> {nova}")
    trocar_versao(nova)
    try:
        passo("Rodando os testes")
        rodar(sys.executable, "-m", "pytest", "-q")

        passo("Gerando o PainelDoBar.exe")
        rodar("cmd", "/c", "gerar_exe.bat", stdin=subprocess.DEVNULL)
        exe = ROOT / "dist" / ASSET_NAME
        if not exe.exists():
            raise Parar("O gerar_exe.bat terminou, mas não achei o dist\\PainelDoBar.exe.")
    except Parar:
        trocar_versao(__version__)          # nada foi publicado: volta o número antigo
        raise

    passo("Gravando no Git e enviando para o GitHub")
    git("add", "-A")
    git("commit", "-m", f"Versão {nova}: {notas}")
    git("tag", f"v{nova}")
    rodar("git", "push", "origin", "main", f"v{nova}")

    passo("Criando a versão no GitHub com o .exe")
    url = criar_release(nova, notas, exe)
    print(f"\nPronto! Versão {nova} publicada: {url}")
    print("Os painéis instalados vão oferecer a atualização na próxima vez que abrirem.")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    try:
        publicar(sys.argv[1].strip(), sys.argv[2].strip())
    except Parar as exc:
        print(f"\n[ERRO] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
