"""Orquestra a abertura da Vista Final (RED)."""
from __future__ import annotations

from pathlib import Path

from pcd_automation.modelo_documentos import gerar_termo_vista_final

from .vista_comum import ResultadoVista, abrir_vista

CAMPOS_OBRIGATORIOS_VISTA_FINAL = ["data_vista_final", "numero_folha_inicial_red", "numero_folha_final_red"]


def abrir_vista_final(dados: dict, diretorio_base: Path | str) -> ResultadoVista:
    return abrir_vista(
        dados,
        diretorio_base,
        campo_data_evento="data_vista_final",
        campos_obrigatorios=CAMPOS_OBRIGATORIOS_VISTA_FINAL,
        gerar_termo=gerar_termo_vista_final,
        nome_arquivo="03_termo_abertura_vista_final.docx",
        nome_etapa="vista_final",
        rotulo_estagio="Vista Final (RED)",
    )
