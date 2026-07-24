"""Orquestra a notificação da oitiva de testemunha: gera, na mesma pasta do
processo já instaurado, a notificação de comparecimento da testemunha e a
notificação do sindicado/defensor para ciência da audição.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pcd_automation.log import registrar_evento
from pcd_automation.modelo_documentos import gerar_notificacao_sindicado_audicao, gerar_notificacao_testemunha

from .instaurar import gerar_processo_id

CAMPOS_OBRIGATORIOS_OITIVA = [
    "data_oitiva", "hora_oitiva",
    "nome_testemunha", "posto_testemunha", "re_testemunha", "unidade_testemunha",
    "data_notificacao_testemunha", "data_notificacao_sindicado",
]


@dataclass
class ResultadoOitiva:
    ok: bool
    processo_id: str | None = None
    diretorio: Path | None = None
    caminho_notificacao_testemunha: Path | None = None
    caminho_notificacao_sindicado: Path | None = None
    erros: list[str] = field(default_factory=list)
    campos_manuais_pendentes: list[str] = field(default_factory=list)


def notificar_oitiva(dados: dict, diretorio_base: Path | str) -> ResultadoOitiva:
    diretorio_base = Path(diretorio_base)
    processo_id = gerar_processo_id(dados)
    diretorio_processo = diretorio_base / processo_id

    if not diretorio_processo.exists():
        return ResultadoOitiva(
            ok=False,
            processo_id=processo_id,
            erros=[f"Processo {processo_id} não encontrado em {diretorio_base} - instaure antes de notificar a oitiva."],
        )

    faltantes = [c for c in CAMPOS_OBRIGATORIOS_OITIVA if not dados.get(c)]
    if faltantes:
        return ResultadoOitiva(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Campo obrigatório ausente para notificar a oitiva: {c}" for c in faltantes],
        )

    caminho_log = diretorio_processo / "log.jsonl"
    caminho_notif_testemunha = diretorio_processo / "04_notificacao_testemunha.docx"
    caminho_notif_sindicado = diretorio_processo / "05_notificacao_sindicado_audicao.docx"

    try:
        pendentes_testemunha = gerar_notificacao_testemunha(dados, caminho_notif_testemunha)
        pendentes_sindicado = gerar_notificacao_sindicado_audicao(dados, caminho_notif_sindicado)
    except Exception as exc:
        registrar_evento(caminho_log, "oitiva_notificacao_falhou", {"erro": str(exc)}, nivel="ERROR")
        return ResultadoOitiva(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Falha ao gerar as notificações de oitiva: {exc}"],
        )

    pendentes = pendentes_testemunha + pendentes_sindicado

    registrar_evento(caminho_log, "oitiva_notificada", {
        "arquivo_notificacao_testemunha": str(caminho_notif_testemunha),
        "arquivo_notificacao_sindicado": str(caminho_notif_sindicado),
        "campos_pendentes_preenchimento_manual": pendentes,
    })

    return ResultadoOitiva(
        ok=True,
        processo_id=processo_id,
        diretorio=diretorio_processo,
        caminho_notificacao_testemunha=caminho_notif_testemunha,
        caminho_notificacao_sindicado=caminho_notif_sindicado,
        campos_manuais_pendentes=pendentes,
    )
