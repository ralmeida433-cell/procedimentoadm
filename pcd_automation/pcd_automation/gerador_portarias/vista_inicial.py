"""Orquestra a abertura da Vista Inicial (defesa prévia)."""
from __future__ import annotations

from pathlib import Path

from pcd_automation.modelo_documentos import gerar_termo_vista_inicial

from .vista_comum import ResultadoVista, abrir_vista

CAMPOS_OBRIGATORIOS_VISTA_INICIAL = [
    "data_citacao", "numero_folha_inicial_defesa_previa", "numero_folha_final_defesa_previa",
]


def abrir_vista_inicial(dados: dict, diretorio_base: Path | str) -> ResultadoVista:
    return abrir_vista(
        dados,
        diretorio_base,
        campo_data_evento="data_citacao",
        campos_obrigatorios=CAMPOS_OBRIGATORIOS_VISTA_INICIAL,
        gerar_termo=gerar_termo_vista_inicial,
        nome_arquivo="02_termo_abertura_vista_inicial.docx",
        nome_etapa="vista_inicial",
        rotulo_estagio="Vista Inicial (defesa prévia)",
    )
