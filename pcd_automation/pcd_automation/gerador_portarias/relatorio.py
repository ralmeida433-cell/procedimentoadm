"""Orquestra a geração do Relatório do Encarregado."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pcd_automation.log import registrar_evento
from pcd_automation.modelo_documentos import gerar_relatorio_encarregado

from .instaurar import gerar_processo_id


@dataclass
class ResultadoRelatorio:
    ok: bool
    processo_id: str | None = None
    diretorio: Path | None = None
    caminho_termo: Path | None = None
    erros: list[str] = field(default_factory=list)
    campos_manuais_pendentes: list[str] = field(default_factory=list)


def gerar_relatorio(dados: dict, diretorio_base: Path | str) -> ResultadoRelatorio:
    diretorio_base = Path(diretorio_base)
    processo_id = gerar_processo_id(dados)
    diretorio_processo = diretorio_base / processo_id

    if not diretorio_processo.exists():
        return ResultadoRelatorio(
            ok=False,
            processo_id=processo_id,
            erros=[f"Processo {processo_id} não encontrado em {diretorio_base} - instaure antes de gerar o relatório."],
        )

    caminho_log = diretorio_processo / "log.jsonl"
    caminho_termo = diretorio_processo / "07_relatorio_encarregado.docx"

    try:
        pendentes = gerar_relatorio_encarregado(dados, caminho_termo)
    except Exception as exc:
        registrar_evento(caminho_log, "relatorio_falhou", {"erro": str(exc)}, nivel="ERROR")
        return ResultadoRelatorio(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Falha ao gerar o Relatório do Encarregado: {exc}"],
        )

    registrar_evento(caminho_log, "relatorio_gerado", {
        "arquivo": str(caminho_termo),
        "campos_pendentes_preenchimento_manual": pendentes,
    })

    return ResultadoRelatorio(
        ok=True,
        processo_id=processo_id,
        diretorio=diretorio_processo,
        caminho_termo=caminho_termo,
        campos_manuais_pendentes=pendentes,
    )
