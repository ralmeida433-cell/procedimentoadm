"""Deriva as variáveis do template `comunicacao_disciplinar.docx`.

A Comunicação Disciplinar é o relato inicial que origina o PCD - ela é
redigida e assinada pelo comunicante (quem presenciou/tomou conhecimento
da transgressão), não necessariamente pela autoridade processante que
será designada depois pelo Despacho de Instauração. Por isso usa seus
próprios campos de identificação (nome/posto/matrícula/unidade do comunicante) e
sua própria data, distintos dos da instauração.

O bloco de testemunha e "bens/documentos relacionados" são opcionais -
nem toda comunicação tem testemunha.
"""
from __future__ import annotations


def preparar_dados_comunicacao(dados: dict) -> tuple[dict, list[str]]:
    """Retorna (variáveis_do_template, campos_pendentes_de_preenchimento_manual)."""
    data_fato = dados.get("data_fato")
    data_comunicacao = dados["data_comunicacao"]
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    variaveis = {
        "numero_comunicacao_disciplinar": preencher_ou_marcar(
            "numero_comunicacao_disciplinar", "nº da Comunicação Disciplinar"
        ),
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "numero_folhas_escala_servico": preencher_ou_marcar(
            "numero_folhas_escala_servico", "nº de folhas da Escala de Serviço anexa"
        ),
        "unidade_sindicado": dados["unidade_sindicado"],
        "re_sindicado": dados["re_sindicado"],
        "posto_graduacao_sindicado": dados["posto_graduacao_sindicado"],
        "nome_sindicado_upper": dados["nome_sindicado"].upper(),
        "hora_fato": preencher_ou_marcar("hora_fato", "hora aproximada do fato"),
        "local_fato": preencher_ou_marcar("local_fato", "local do fato"),
        "resumo_fato": dados["resumo_fato"],
        "unidade_testemunha": preencher_ou_marcar("unidade_testemunha", "unidade da testemunha"),
        "re_testemunha": preencher_ou_marcar("re_testemunha", "número de matrícula da testemunha"),
        "posto_testemunha": preencher_ou_marcar("posto_testemunha", "posto/graduação da testemunha"),
        "nome_testemunha_upper": preencher_ou_marcar("nome_testemunha", "nome da testemunha").upper(),
        "bens_documentos_relacionados": dados.get("bens_documentos_relacionados") or "",
        "unidade_comunicante": dados["unidade_comunicante"],
        "re_comunicante": dados["re_comunicante"],
        "posto_comunicante": dados["posto_comunicante"],
        "nome_comunicante_upper": dados["nome_comunicante"].upper(),
        "cidade_sede": dados.get("cidade_sede") or dados.get("cidade_fato"),
        "data_comunicacao_barra": f"{data_comunicacao.day:02d}/{data_comunicacao.month:02d}/{data_comunicacao.year}",
    }

    if data_fato:
        variaveis["data_fato_barra"] = f"{data_fato.day:02d}/{data_fato.month:02d}/{data_fato.year}"
    else:
        pendentes.append("data do fato")
        variaveis["data_fato_barra"] = "[PREENCHER: data do fato]"

    if not variaveis["cidade_sede"]:
        pendentes.append("cidade sede da unidade")
        variaveis["cidade_sede"] = "[PREENCHER: cidade sede da unidade]"

    return variaveis, pendentes
