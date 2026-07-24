"""Persistência do estado de um PCD em andamento no assistente interativo.

Antes da instauração (quando ainda não existe pasta de processo), o
progresso é salvo como "rascunho" em `processos/_rascunhos/<chave>.json`.
Depois que a instauração é concluída com sucesso, o rascunho vira o estado
oficial do processo, salvo em `processos/<id>/estado_assistente.json`, e o
rascunho é apagado.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

NOME_ARQUIVO_ESTADO = "estado_assistente.json"
DIR_RASCUNHOS_NOME = "_rascunhos"


def slugificar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto or "rascunho"


def _serializar(valor):
    if isinstance(valor, date):
        return {"__data__": valor.isoformat()}
    return valor


def _desserializar(valor):
    if isinstance(valor, dict) and "__data__" in valor:
        return date.fromisoformat(valor["__data__"])
    return valor


def _empacotar(dados: dict) -> dict:
    return {k: _serializar(v) for k, v in dados.items()}


def _desempacotar(payload: dict) -> dict:
    return {k: _desserializar(v) for k, v in payload.items()}


# ---- Rascunhos (antes da instauração) ----

def _caminho_rascunho(diretorio_base: Path, chave: str) -> Path:
    return diretorio_base / DIR_RASCUNHOS_NOME / f"{slugificar(chave)}.json"


def salvar_rascunho(diretorio_base: Path, chave: str, dados: dict) -> None:
    caminho = _caminho_rascunho(diretorio_base, chave)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"dados": _empacotar(dados)}, ensure_ascii=False, indent=2), encoding="utf-8")


def carregar_rascunho(diretorio_base: Path, chave: str) -> dict | None:
    caminho = _caminho_rascunho(diretorio_base, chave)
    if not caminho.exists():
        return None
    payload = json.loads(caminho.read_text(encoding="utf-8"))
    return _desempacotar(payload["dados"])


def remover_rascunho(diretorio_base: Path, chave: str) -> None:
    _caminho_rascunho(diretorio_base, chave).unlink(missing_ok=True)


def listar_rascunhos(diretorio_base: Path) -> list[str]:
    pasta = diretorio_base / DIR_RASCUNHOS_NOME
    if not pasta.exists():
        return []
    return sorted(p.stem for p in pasta.glob("*.json"))


# ---- Estado oficial do processo (depois da instauração) ----

def salvar_estado_processo(diretorio_processo: Path, dados: dict, etapa_concluida_ate: str) -> None:
    diretorio_processo.mkdir(parents=True, exist_ok=True)
    payload = {"etapa_concluida_ate": etapa_concluida_ate, "dados": _empacotar(dados)}
    (diretorio_processo / NOME_ARQUIVO_ESTADO).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def carregar_estado_processo(diretorio_processo: Path) -> tuple[dict, str] | None:
    caminho = diretorio_processo / NOME_ARQUIVO_ESTADO
    if not caminho.exists():
        return None
    payload = json.loads(caminho.read_text(encoding="utf-8"))
    return _desempacotar(payload["dados"]), payload["etapa_concluida_ate"]


def listar_processos_em_andamento(diretorio_base: Path) -> list[Path]:
    if not diretorio_base.exists():
        return []
    return sorted(
        p for p in diretorio_base.iterdir()
        if p.is_dir() and p.name != DIR_RASCUNHOS_NOME and (p / NOME_ARQUIVO_ESTADO).exists()
    )
