"""Orquestra a instauração de um PCD: valida, cria a estrutura de diretórios,
gera a Comunicação Disciplinar e o Despacho de Instauração, e registra o
log da etapa.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from pcd_automation.gestao_prazos import calcular_prazo_conclusao
from pcd_automation.log import registrar_evento
from pcd_automation.modelo_documentos import gerar_comunicacao_disciplinar, gerar_despacho_instauracao
from pcd_automation.validador_juridico import validar_processo


@dataclass
class ResultadoInstauracao:
    ok: bool
    processo_id: str | None = None
    diretorio: Path | None = None
    caminho_comunicacao: Path | None = None
    caminho_despacho: Path | None = None
    prazo_conclusao: str | None = None
    erros: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    campos_manuais_pendentes: list[str] = field(default_factory=list)


def _slugificar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto or "SEMNOME"


def gerar_processo_id(dados: dict) -> str:
    reds = _slugificar(dados.get("reds") or "SEMREDS")
    nome = _slugificar(dados.get("nome_sindicado", ""))
    data_instauracao = dados["data_instauracao"]
    return f"PCD_{reds}_{nome}_{data_instauracao.isoformat()}"


def instaurar_processo(dados: dict, diretorio_base: Path | str) -> ResultadoInstauracao:
    diretorio_base = Path(diretorio_base)

    resultado_validacao = validar_processo(dados)
    if not resultado_validacao.ok:
        return ResultadoInstauracao(ok=False, erros=resultado_validacao.erros, alertas=resultado_validacao.alertas)

    processo_id = gerar_processo_id(dados)
    diretorio_processo = diretorio_base / processo_id
    diretorio_processo.mkdir(parents=True, exist_ok=True)
    caminho_log = diretorio_processo / "log.jsonl"

    registrar_evento(caminho_log, "instauracao_iniciada", {"processo_id": processo_id})

    caminho_comunicacao = diretorio_processo / "00_comunicacao_disciplinar.docx"
    caminho_despacho = diretorio_processo / "01_despacho_instauracao.docx"
    try:
        pendentes_comunicacao = gerar_comunicacao_disciplinar(dados, caminho_comunicacao)
        pendentes_despacho = gerar_despacho_instauracao(dados, caminho_despacho)
    except Exception as exc:
        registrar_evento(caminho_log, "instauracao_falhou", {"erro": str(exc)}, nivel="ERROR")
        return ResultadoInstauracao(
            ok=False,
            processo_id=processo_id,
            diretorio=diretorio_processo,
            erros=[f"Falha ao gerar os documentos de instauração: {exc}"],
            alertas=resultado_validacao.alertas,
        )

    pendentes = pendentes_comunicacao + pendentes_despacho
    prazo_conclusao = calcular_prazo_conclusao(dados["data_instauracao"], dados.get("prorrogado", False))

    registrar_evento(caminho_log, "despacho_gerado", {
        "arquivo_comunicacao": str(caminho_comunicacao),
        "arquivo_despacho": str(caminho_despacho),
        "prazo_conclusao": prazo_conclusao.isoformat(),
        "campos_pendentes_preenchimento_manual": pendentes,
        "alertas_validacao": resultado_validacao.alertas,
    })

    return ResultadoInstauracao(
        ok=True,
        processo_id=processo_id,
        diretorio=diretorio_processo,
        caminho_comunicacao=caminho_comunicacao,
        caminho_despacho=caminho_despacho,
        prazo_conclusao=prazo_conclusao.isoformat(),
        alertas=resultado_validacao.alertas,
        campos_manuais_pendentes=pendentes,
    )
