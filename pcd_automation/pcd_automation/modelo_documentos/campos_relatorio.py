"""Deriva as variáveis do template `relatorio_encarregado.docx`.

A seção "1. Dados" é objetiva e pode ser auto-preenchida. As seções
"2. Dos fatos e da análise das provas", "3. Das alegações de defesa" e o
"6. Parecer" são o julgamento e a análise jurídica do próprio encarregado
- o sistema nunca fabrica esse conteúdo; ele só é preenchido se o
encarregado já tiver redigido o texto e informado na planilha, caso
contrário fica marcado [PREENCHER] para redação manual no Word.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from pcd_automation.redacao import formatar_gdh

from .formatacao import MESES_PT, data_por_extenso


def _gdh_do_fato(dados: dict, pendentes: list[str]) -> str:
    """Monta o Grupo Data-Hora (GDH) do fato no padrão militar
    `DDHHMMMesAA - Sem` (ex.: "050820Mar26 - Qui"), automaticamente a partir
    da data e da hora do fato. Se o usuário informou `data_hora_militar_fato`
    manualmente, respeita o valor informado. Sem data do fato, marca
    [PREENCHER]. A `hora_fato` já chega normalizada como 'XXhXXmin'."""
    if dados.get("data_hora_militar_fato"):
        return str(dados["data_hora_militar_fato"])
    data_fato = dados.get("data_fato")
    if not data_fato:
        pendentes.append("data/hora do fato no formato militar (GDH)")
        return "[PREENCHER: data/hora do fato no formato militar (GDH)]"
    m = re.fullmatch(r"(\d{2})h(\d{2})min", str(dados.get("hora_fato") or ""))
    if m:
        momento = datetime(data_fato.year, data_fato.month, data_fato.day, int(m.group(1)), int(m.group(2)))
        return formatar_gdh(momento)
    # Sem hora reconhecível: GDH só com a data.
    return formatar_gdh(data_fato, com_hora=False)


def preparar_dados_relatorio(dados: dict) -> tuple[dict, list[str]]:
    data_fato = dados.get("data_fato")
    data_relatorio = dados.get("data_relatorio") or date.today()
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    if dados.get("incidentes_processuais"):
        incidentes = str(dados["incidentes_processuais"])
    elif dados.get("prorrogado"):
        incidentes = (
            "O prazo de conclusão foi prorrogado por mais 10 (dez) dias corridos, "
            "mediante justificativa fundamentada nos autos."
        )
    else:
        incidentes = "Não houve incidentes processuais dignos de nota."

    variaveis = {
        "numero_comunicacao_disciplinar": preencher_ou_marcar(
            "numero_comunicacao_disciplinar", "nº da Comunicação Disciplinar"
        ),
        "data_comunicacao_barra": _formatar_data_barra(dados.get("data_comunicacao"), pendentes, "data da comunicação"),
        "re_sindicado": dados["re_sindicado"],
        "posto_graduacao_sindicado": dados["posto_graduacao_sindicado"],
        "nome_sindicado_upper": dados["nome_sindicado"].upper(),
        "tipificacao_cedm": preencher_ou_marcar(
            "tipificacao_cedm", "inciso e artigo do CEDM correspondente à transgressão"
        ),
        "cidade_fato": preencher_ou_marcar("cidade_fato", "cidade do fato"),
        "hora_fato": preencher_ou_marcar("hora_fato", "hora aproximada do fato"),
        "resumo_fato": dados["resumo_fato"],
        "data_hora_militar_fato": _gdh_do_fato(dados, pendentes),
        "em_servico_sindicado": "SIM" if dados.get("em_servico_sindicado") else "NÃO",
        "re_testemunha": preencher_ou_marcar("re_testemunha", "número de matrícula da testemunha"),
        "posto_testemunha": preencher_ou_marcar("posto_testemunha", "posto/graduação da testemunha"),
        "nome_testemunha_upper": preencher_ou_marcar("nome_testemunha", "nome da testemunha").upper(),
        "numero_folha_depoimento_testemunha": preencher_ou_marcar(
            "numero_folha_depoimento_testemunha", "nº da folha do depoimento da testemunha"
        ),
        "objetos_apreendidos": dados.get("objetos_apreendidos") or "Nenhum",
        "outras_provas": dados.get("outras_provas") or "Nenhuma",
        "analise_fatos_e_provas": preencher_ou_marcar(
            "analise_fatos_e_provas", "análise dos fatos e das provas (seção 2 do relatório)"
        ),
        "alegacoes_defesa_analise": preencher_ou_marcar(
            "alegacoes_defesa_analise", "análise das alegações de defesa (seção 3 do relatório)"
        ),
        "incidentes_processuais": incidentes,
        "cidade_sede": preencher_ou_marcar("cidade_sede", "cidade sede da unidade"),
        "data_relatorio_extenso": data_por_extenso(data_relatorio),
        "nome_autoridade_processante": dados["nome_autoridade_processante"],
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
    }

    if data_fato:
        variaveis["dia_fato"] = f"{data_fato.day:02d}"
        variaveis["mes_fato_extenso"] = MESES_PT[data_fato.month]
        # O modelo só marca como branco o último dígito do ano ("do ano de
        # 202X") - "202" é fixo, então só funciona para 2020-2029; fora
        # dessa década, sinalizamos em vez de gerar data errada.
        if 2020 <= data_fato.year <= 2029:
            variaveis["ano_fato_ultimo_digito"] = str(data_fato.year)[-1]
        else:
            pendentes.append(
                f"ano do fato {data_fato.year} fora da década 2020-2029 suportada pelo modelo "
                "(campo do relatório precisa de ajuste manual no Word)"
            )
            variaveis["ano_fato_ultimo_digito"] = "[PREENCHER: último dígito do ano - fora de 2020-2029]"
    else:
        pendentes.append("data do fato")
        variaveis["dia_fato"] = "[PREENCHER: dia do fato]"
        variaveis["mes_fato_extenso"] = "[PREENCHER: mês do fato]"
        variaveis["ano_fato_ultimo_digito"] = "[PREENCHER: ano do fato]"

    return variaveis, pendentes


def _formatar_data_barra(valor, pendentes: list[str], rotulo: str) -> str:
    if not valor:
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"
    return f"{valor.day:02d}/{valor.month:02d}/{valor.year}"
