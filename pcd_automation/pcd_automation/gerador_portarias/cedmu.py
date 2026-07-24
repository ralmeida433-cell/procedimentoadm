"""Orquestra a geração da Ata de Reunião do CEDMU.

Etapa condicional: só é exigida quando há RED final apresentada (art. 523,
§§1º-2º, do MAPPA - o fator determinante é a existência de razões escritas
de defesa final; processos sem RED não carecem de manifestação do CEDMU).
Ver `interativo.perguntas.proxima_etapa`, que pula esta etapa nesse caso.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pcd_automation.log import registrar_evento
from pcd_automation.modelo_documentos import gerar_ata_cedmu as _gerar_ata_cedmu_docx

from .instaurar import gerar_processo_id


@dataclass
class ResultadoCedmu:
    ok: bool
    processo_id: str | None = None
    diretorio: Path | None = None
    caminho_termo: Path | None = None
    erros: list[str] = field(default_factory=list)
    campos_manuais_pendentes: list[str] = field(default_factory=list)


def gerar_cedmu(dados: dict, diretorio_base: Path | str) -> ResultadoCedmu:
    diretorio_base = Path(diretorio_base)
    processo_id = gerar_processo_id(dados)
    diretorio_processo = diretorio_base / processo_id

    if not diretorio_processo.exists():
        return ResultadoCedmu(
            ok=False,
            processo_id=processo_id,
            erros=[f"Processo {processo_id} não encontrado em {diretorio_base} - instaure antes de gerar a ata do CEDMU."],
        )

    caminho_log = diretorio_processo / "log.jsonl"
    caminho_termo = diretorio_processo / "09_ata_reuniao_cedmu.docx"

    try:
        pendentes = _gerar_ata_cedmu_docx(dados, caminho_termo)
    except Exception as exc:
        registrar_evento(caminho_log, "cedmu_falhou", {"erro": str(exc)}, nivel="ERROR")
        return ResultadoCedmu(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Falha ao gerar a Ata de Reunião do CEDMU: {exc}"],
        )

    registrar_evento(caminho_log, "cedmu_gerado", {
        "arquivo": str(caminho_termo),
        "campos_pendentes_preenchimento_manual": pendentes,
    })

    return ResultadoCedmu(
        ok=True,
        processo_id=processo_id,
        diretorio=diretorio_processo,
        caminho_termo=caminho_termo,
        campos_manuais_pendentes=pendentes,
    )
