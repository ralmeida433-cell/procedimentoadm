"""Ponto de entrada WSGI para hospedagem (ex.: PythonAnywhere).

Servidores de produção (o do PythonAnywhere, gunicorn, waitress etc.) não
usam `python main.py servidor` (aquele é o servidor de DESENVOLVIMENTO do
Flask, só para uso local). Eles importam um objeto WSGI chamado
`application` - é o que este arquivo expõe.

No PythonAnywhere, o arquivo WSGI da conta (algo como
`/var/www/<usuario>_pythonanywhere_com_wsgi.py`) deve conter apenas:

    import sys
    caminho = "/home/<usuario>/procedimentoadm/pcd_automation"
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
    from wsgi import application  # noqa

Configure as variáveis de ambiente na aba "Web" do PythonAnywhere (ou aqui
via .env, se preferir manter local):
  - OPENROUTER_API_KEY : chave da IA (consulta ao MAPPA e extração).
  - PCD_SENHA          : senha de acesso ao sistema (ATIVA o login).
  - PCD_SECRET_KEY     : chave para assinar os cookies de sessão (fixa).
  - PCD_DIRETORIO_PROCESSOS : (opcional) pasta onde salvar os processos.
"""
from __future__ import annotations

import os
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent

# Carrega .env se existir (útil no uso local; no servidor prefira definir as
# variáveis de ambiente pela interface da hospedagem).
try:
    from dotenv import load_dotenv

    load_dotenv(_RAIZ / ".env")
except ImportError:
    pass

from pcd_automation.webapp.app import criar_app  # noqa: E402  (após load_dotenv)

_DIRETORIO_PROCESSOS = Path(
    os.environ.get("PCD_DIRETORIO_PROCESSOS") or (_RAIZ / "processos")
)

application = criar_app(_DIRETORIO_PROCESSOS)
