"""Orquestra o registro do Termo de Depoimento da testemunha."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pcd_automation.log import registrar_evento
from pcd_automation.modelo_documentos import gerar_termo_depoimento

from .instaurar import gerar_processo_id

CAMPOS_OBRIGATORIOS_DEPOIMENTO = [
    "data_oitiva", "nome_testemunha", "posto_testemunha", "re_testemunha",
]


@dataclass
class ResultadoDepoimento:
    ok: bool
    processo_id: str | None = None
    diretorio: Path | None = None
    caminho_termo: Path | None = None
    erros: list[str] = field(default_factory=list)
    campos_manuais_pendentes: list[str] = field(default_factory=list)


def registrar_depoimento(dados: dict, diretorio_base: Path | str) -> ResultadoDepoimento:
    diretorio_base = Path(diretorio_base)
    processo_id = gerar_processo_id(dados)
    diretorio_processo = diretorio_base / processo_id

    if not diretorio_processo.exists():
        return ResultadoDepoimento(
            ok=False,
            processo_id=processo_id,
            erros=[f"Processo {processo_id} não encontrado em {diretorio_base} - instaure antes de registrar o depoimento."],
        )

    faltantes = [c for c in CAMPOS_OBRIGATORIOS_DEPOIMENTO if not dados.get(c)]
    if faltantes:
        return ResultadoDepoimento(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Campo obrigatório ausente para registrar o depoimento: {c}" for c in faltantes],
        )

    caminho_log = diretorio_processo / "log.jsonl"
    caminho_termo = diretorio_processo / "06_termo_depoimento_testemunha.docx"

    try:
        pendentes = gerar_termo_depoimento(dados, caminho_termo)
    except Exception as exc:
        registrar_evento(caminho_log, "depoimento_falhou", {"erro": str(exc)}, nivel="ERROR")
        return ResultadoDepoimento(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Falha ao gerar o Termo de Depoimento: {exc}"],
        )

    registrar_evento(caminho_log, "depoimento_registrado", {
        "arquivo": str(caminho_termo),
        "campos_pendentes_preenchimento_manual": pendentes,
    })

    return ResultadoDepoimento(
        ok=True,
        processo_id=processo_id,
        diretorio=diretorio_processo,
        caminho_termo=caminho_termo,
        campos_manuais_pendentes=pendentes,
    )
