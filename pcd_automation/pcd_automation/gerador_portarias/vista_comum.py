"""Lógica compartilhada entre a abertura da Vista Inicial (defesa prévia) e
da Vista Final (RED): ambas exigem que o processo já tenha sido instaurado,
geram um termo na mesma pasta do processo e registram o log da etapa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pcd_automation.gestao_prazos import calcular_prazo_defesa
from pcd_automation.log import registrar_evento

from .instaurar import gerar_processo_id


@dataclass
class ResultadoVista:
    ok: bool
    processo_id: str | None = None
    diretorio: Path | None = None
    caminho_termo: Path | None = None
    prazo_defesa: str | None = None
    erros: list[str] = field(default_factory=list)
    campos_manuais_pendentes: list[str] = field(default_factory=list)


def abrir_vista(
    dados: dict,
    diretorio_base: Path | str,
    *,
    campo_data_evento: str,
    campos_obrigatorios: list[str],
    gerar_termo: Callable[[dict, Path], list[str]],
    nome_arquivo: str,
    nome_etapa: str,
    rotulo_estagio: str,
) -> ResultadoVista:
    diretorio_base = Path(diretorio_base)
    processo_id = gerar_processo_id(dados)
    diretorio_processo = diretorio_base / processo_id

    if not diretorio_processo.exists():
        return ResultadoVista(
            ok=False,
            processo_id=processo_id,
            erros=[
                f"Processo {processo_id} não encontrado em {diretorio_base} - "
                f"instaure antes de abrir a {rotulo_estagio}."
            ],
        )

    faltantes = [c for c in campos_obrigatorios if not dados.get(c)]
    if faltantes:
        return ResultadoVista(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Campo obrigatório ausente para abertura da {rotulo_estagio}: {c}" for c in faltantes],
        )

    caminho_log = diretorio_processo / "log.jsonl"
    caminho_termo = diretorio_processo / nome_arquivo

    try:
        pendentes = gerar_termo(dados, caminho_termo)
    except Exception as exc:
        registrar_evento(caminho_log, f"{nome_etapa}_falhou", {"erro": str(exc)}, nivel="ERROR")
        return ResultadoVista(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Falha ao gerar o termo de {rotulo_estagio}: {exc}"],
        )

    prazo_defesa = calcular_prazo_defesa(dados[campo_data_evento])

    registrar_evento(caminho_log, f"{nome_etapa}_aberta", {
        "arquivo": str(caminho_termo),
        "prazo_defesa": prazo_defesa.isoformat(),
        "campos_pendentes_preenchimento_manual": pendentes,
    })

    return ResultadoVista(
        ok=True,
        processo_id=processo_id,
        diretorio=diretorio_processo,
        caminho_termo=caminho_termo,
        prazo_defesa=prazo_defesa.isoformat(),
        campos_manuais_pendentes=pendentes,
    )
