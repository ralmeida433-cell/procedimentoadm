"""Deriva as variáveis do template `despacho_instauracao.docx` a partir do
dict canônico de dados do processo (ver `pcd_automation.schema`).

Campos que exigem redação/julgamento jurídico do encarregado (ex.:
tipificação no CEDM) e não foram informados na planilha viram um marcador
"[PREENCHER: ...]" visível no documento gerado, em vez de serem adivinhados.

O modelo original só negrita o ÚLTIMO dígito do ano na linha "Quartel em"
(a data fica em runs diferentes: fixo "202" + um branco de 1 dígito) -
isso é uma limitação do modelo em si, não deste código: só funciona para
instaurações entre 2020 e 2029. Fora dessa década, sinalizamos
[PREENCHER] em vez de gerar uma data errada em silêncio.
"""
from __future__ import annotations

from .formatacao import MESES_PT


def preparar_dados_despacho(dados: dict) -> tuple[dict, list[str]]:
    """Retorna (variáveis_do_template, campos_pendentes_de_preenchimento_manual)."""
    data_instauracao = dados["data_instauracao"]
    data_fato = dados.get("data_fato")
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    variaveis = {
        "numero_processo": preencher_ou_marcar("numero_processo", "número sequencial do processo"),
        "ano_processo": str(data_instauracao.year),
        "re_autoridade_processante": dados["re_autoridade_processante"],
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
        "nome_autoridade_processante": dados["nome_autoridade_processante"],
        "unidade_autoridade_processante": (
            dados.get("unidade_autoridade_processante") or dados.get("unidade_sindicado")
        ),
        "numero_comunicacao_disciplinar": preencher_ou_marcar(
            "numero_comunicacao_disciplinar", "nº da Comunicação Disciplinar"
        ),
        "numero_folhas_anexo": preencher_ou_marcar(
            "numero_folhas_comunicacao_disciplinar", "nº de folhas da Comunicação Disciplinar anexa"
        ),
        "re_sindicado": dados["re_sindicado"],
        "posto_graduacao_sindicado_upper": dados["posto_graduacao_sindicado"].upper(),
        "nome_sindicado_upper": dados["nome_sindicado"].upper(),
        "resumo_fato": dados["resumo_fato"],
        "cidade_fato": preencher_ou_marcar("cidade_fato", "cidade do fato"),
        "hora_fato": preencher_ou_marcar("hora_fato", "hora aproximada do fato"),
        "tipificacao_cedm": preencher_ou_marcar(
            "tipificacao_cedm", "inciso e artigo do CEDM correspondente à transgressão"
        ),
        "posto_autoridade_delegante": dados["posto_autoridade_delegante"],
        "nome_autoridade_delegante": dados["nome_autoridade_delegante"],
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
    }

    if not variaveis["unidade_autoridade_processante"]:
        pendentes.append("unidade da autoridade processante")
        variaveis["unidade_autoridade_processante"] = "[PREENCHER: unidade da autoridade processante]"

    if data_fato:
        variaveis["dia_fato"] = f"{data_fato.day:02d}"
        # O modelo só marca como branco os 2 últimos dígitos do ano
        # ("do ano de 20XX") - o "20" é fixo, então isso vale para
        # qualquer ano de 2000 a 2099.
        variaveis["ano_fato_sufixo"] = f"{data_fato.year % 100:02d}"
    else:
        pendentes.append("dia/ano do fato")
        variaveis["dia_fato"] = "[PREENCHER: dia do fato]"
        variaveis["ano_fato_sufixo"] = "[PREENCHER: ano do fato]"

    cidade_sede = dados.get("cidade_sede") or dados.get("cidade_fato")
    if cidade_sede:
        variaveis["cidade_sede"] = cidade_sede
    else:
        pendentes.append("cidade sede da unidade")
        variaveis["cidade_sede"] = "[PREENCHER: cidade sede da unidade]"

    variaveis["dia_instauracao"] = f"{data_instauracao.day:02d}"
    variaveis["mes_instauracao_extenso"] = MESES_PT[data_instauracao.month]
    if 2020 <= data_instauracao.year <= 2029:
        variaveis["ano_instauracao_ultimo_digito"] = str(data_instauracao.year)[-1]
    else:
        pendentes.append(
            f"ano de instauração {data_instauracao.year} fora da década 2020-2029 suportada pelo modelo "
            "(campo 'Quartel em ..., XX de ... de 202X' precisa de ajuste manual no Word)"
        )
        variaveis["ano_instauracao_ultimo_digito"] = "[PREENCHER: último dígito do ano - fora de 2020-2029]"

    return variaveis, pendentes
