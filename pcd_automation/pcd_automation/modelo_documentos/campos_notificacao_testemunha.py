"""Deriva as variáveis do template `notificacao_testemunha.docx` - convoca
a testemunha a comparecer para ser ouvida (oitiva)."""
from __future__ import annotations

from .formatacao import data_por_extenso


def preparar_dados_notificacao_testemunha(dados: dict) -> tuple[dict, list[str]]:
    data_oitiva = dados["data_oitiva"]
    data_notificacao = dados["data_notificacao_testemunha"]
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    variaveis = {
        "posto_autoridade_delegante": dados["posto_autoridade_delegante"],
        "nome_autoridade_delegante": dados["nome_autoridade_delegante"],
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "re_testemunha": preencher_ou_marcar("re_testemunha", "número de matrícula da testemunha"),
        "posto_testemunha": preencher_ou_marcar("posto_testemunha", "posto/graduação da testemunha"),
        "nome_testemunha_upper": preencher_ou_marcar("nome_testemunha", "nome da testemunha").upper(),
        "unidade_testemunha": preencher_ou_marcar("unidade_testemunha", "unidade da testemunha"),
        "hora_oitiva": preencher_ou_marcar("hora_oitiva", "hora da oitiva"),
        "endereco_sede": preencher_ou_marcar("endereco_sede", "endereço da sede da unidade"),
        "nome_autoridade_processante_upper": dados["nome_autoridade_processante"].upper(),
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
        "cidade_sede": dados.get("cidade_sede") or dados.get("cidade_fato"),
        "data_oitiva_barra": f"{data_oitiva.day:02d}/{data_oitiva.month:02d}/{data_oitiva.year}",
        "data_notificacao_testemunha_barra": (
            f"{data_notificacao.day:02d}/{data_notificacao.month:02d}/{data_notificacao.year}"
        ),
    }

    variaveis["data_notificacao_testemunha_extenso"] = data_por_extenso(data_notificacao)

    if not variaveis["cidade_sede"]:
        pendentes.append("cidade sede da unidade")
        variaveis["cidade_sede"] = "[PREENCHER: cidade sede da unidade]"

    return variaveis, pendentes
