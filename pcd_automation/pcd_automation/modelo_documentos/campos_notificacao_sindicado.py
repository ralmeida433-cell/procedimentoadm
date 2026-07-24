"""Deriva as variáveis do template `notificacao_sindicado_audicao.docx` -
dá ciência ao sindicado/defensor da data da audição de testemunhas, para
que possam comparecer facultativamente e exercer o contraditório."""
from __future__ import annotations

from .formatacao import MESES_PT, data_por_extenso


def preparar_dados_notificacao_sindicado(dados: dict) -> tuple[dict, list[str]]:
    data_oitiva = dados["data_oitiva"]
    data_notificacao = dados["data_notificacao_sindicado"]
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    variaveis = {
        "re_sindicado": dados["re_sindicado"],
        "posto_graduacao_sindicado": dados["posto_graduacao_sindicado"],
        "nome_sindicado": dados["nome_sindicado"],
        "numero_processo": preencher_ou_marcar("numero_processo", "número sequencial do processo"),
        "ano_processo": str(dados["data_instauracao"].year),
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "dia_oitiva": f"{data_oitiva.day:02d}",
        "mes_oitiva_extenso": MESES_PT[data_oitiva.month],
        "ano_oitiva": str(data_oitiva.year),
        "hora_oitiva": preencher_ou_marcar("hora_oitiva", "hora da oitiva"),
        "posto_testemunha": preencher_ou_marcar("posto_testemunha", "posto/graduação da testemunha"),
        "nome_testemunha_upper": preencher_ou_marcar("nome_testemunha", "nome da testemunha").upper(),
        "nome_autoridade_processante": dados["nome_autoridade_processante"],
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
        "cidade_sede": dados.get("cidade_sede") or dados.get("cidade_fato"),
        "data_notificacao_sindicado_barra": (
            f"{data_notificacao.day:02d}/{data_notificacao.month:02d}/{data_notificacao.year}"
        ),
        "data_notificacao_sindicado_extenso": data_por_extenso(data_notificacao),
    }

    if not variaveis["cidade_sede"]:
        pendentes.append("cidade sede da unidade")
        variaveis["cidade_sede"] = "[PREENCHER: cidade sede da unidade]"

    return variaveis, pendentes
