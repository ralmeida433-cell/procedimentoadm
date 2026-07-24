"""Lógica compartilhada entre o Termo de Abertura de Vista Inicial (defesa
prévia) e o Termo de Abertura de Vista Final (RED) - os dois templates têm
o mesmo corpo de texto e os mesmos marcadores {{campo}}, diferindo apenas
em QUAL data/contagem de folhas de cada estágio alimenta esses marcadores
(cada estágio tem sua própria data de citação e sua própria contagem de
folhas dos autos, que cresce conforme o processo avança).
"""
from __future__ import annotations

from .formatacao import MESES_PT, data_por_extenso


def preparar_dados_vista(
    dados: dict,
    *,
    campo_data_evento: str,
    campo_folhas_total: str,
    campo_folha_inicial: str,
    campo_folha_final: str,
    rotulo_estagio: str,
) -> tuple[dict, list[str]]:
    """Retorna (variáveis_do_template, campos_pendentes_de_preenchimento_manual)."""
    data_evento = dados[campo_data_evento]
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
        "ano_processo": str(dados["data_instauracao"].year),
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "dia_citacao": f"{data_evento.day:02d}",
        "mes_citacao_extenso": MESES_PT[data_evento.month],
        "ano_citacao": str(data_evento.year),
        "data_citacao_extenso": data_por_extenso(data_evento),
        "nome_autoridade_processante": dados["nome_autoridade_processante"],
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
        "re_sindicado": dados["re_sindicado"],
        "posto_graduacao_sindicado": dados["posto_graduacao_sindicado"],
        "nome_sindicado": dados["nome_sindicado"],
        "unidade_sindicado": dados["unidade_sindicado"],
        "numero_folhas_anexo": preencher_ou_marcar(
            campo_folhas_total, f"nº de folhas dos autos ({rotulo_estagio})"
        ),
        "numero_folha_inicial": preencher_ou_marcar(
            campo_folha_inicial, f"nº da folha inicial ({rotulo_estagio})"
        ),
        "numero_folha_final": preencher_ou_marcar(
            campo_folha_final, f"nº da folha final ({rotulo_estagio})"
        ),
        # O modelo tem blancos separados para o número do inciso e do
        # artigo (não um campo único de citação como em outros
        # documentos) - por isso usa numero_inciso_cedm/numero_artigo_cedm,
        # não tipificacao_cedm.
        "numero_inciso_cedm": preencher_ou_marcar("numero_inciso_cedm", "número do inciso do CEDM"),
        "numero_artigo_cedm": preencher_ou_marcar("numero_artigo_cedm", "número do artigo do CEDM"),
        "resumo_fato": dados["resumo_fato"],
        "cidade_fato": preencher_ou_marcar("cidade_fato", "cidade do fato"),
        "hora_fato": preencher_ou_marcar("hora_fato", "hora aproximada do fato"),
        "cidade_sede": dados.get("cidade_sede") or dados.get("cidade_fato"),
    }

    if data_fato:
        variaveis["dia_fato"] = f"{data_fato.day:02d}"
        variaveis["ano_fato"] = str(data_fato.year)
    else:
        pendentes.append("dia/ano do fato")
        variaveis["dia_fato"] = "[PREENCHER: dia do fato]"
        variaveis["ano_fato"] = "[PREENCHER: ano do fato]"

    if not variaveis["cidade_sede"]:
        pendentes.append("cidade sede da unidade")
        variaveis["cidade_sede"] = "[PREENCHER: cidade sede da unidade]"

    return variaveis, pendentes
