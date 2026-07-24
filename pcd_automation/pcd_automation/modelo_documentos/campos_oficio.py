"""Deriva as variáveis do template `oficio_remessa.docx` - último documento
do PCD, remete os autos concluídos à autoridade delegante para solução."""
from __future__ import annotations

from datetime import date

from .formatacao import data_por_extenso


def preparar_dados_oficio(dados: dict) -> tuple[dict, list[str]]:
    data_oficio = dados.get("data_oficio_remessa") or date.today()
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    variaveis = {
        "numero_oficio_remessa": preencher_ou_marcar("numero_oficio_remessa", "nº do Ofício de Remessa"),
        "numero_processo": preencher_ou_marcar("numero_processo", "número sequencial do processo"),
        "ano_processo": str(dados["data_instauracao"].year),
        "cidade_sede": preencher_ou_marcar("cidade_sede", "cidade sede da unidade"),
        "data_oficio_remessa_extenso": data_por_extenso(data_oficio),
        "posto_autoridade_delegante": dados["posto_autoridade_delegante"],
        "nome_autoridade_delegante": dados["nome_autoridade_delegante"],
        "numero_folhas_autos_final": preencher_ou_marcar(
            "numero_folhas_autos_final", "nº total de folhas dos autos"
        ),
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "nome_autoridade_processante": dados["nome_autoridade_processante"],
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
    }

    return variaveis, pendentes
