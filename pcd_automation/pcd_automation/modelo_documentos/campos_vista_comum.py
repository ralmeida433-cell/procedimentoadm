"""Lógica compartilhada entre o Termo de Abertura de Vista Inicial (defesa
prévia) e o Termo de Abertura de Vista Final (RED) - os dois templates têm
o mesmo corpo de texto e os mesmos marcadores {{campo}}, diferindo apenas
em QUAL data/contagem de folhas de cada estágio alimenta esses marcadores
(cada estágio tem sua própria data de citação e sua própria contagem de
folhas dos autos, que cresce conforme o processo avança).
"""
from __future__ import annotations

from pcd_automation.transgressoes_cedm import extrair_de_texto

from .formatacao import MESES_PT, data_por_extenso


def _inciso_e_artigo(dados: dict, pendentes: list[str]) -> tuple[str, str]:
    """Devolve (inciso, artigo) para os blancos separados do Termo de Vista.

    O encarregado já informou a tipificação uma vez, na instauração
    (`tipificacao_cedm`, ex.: "art. 13, inciso XX, do CEDM..."). Redigitar o
    número aqui só abre espaço para os documentos do mesmo processo citarem
    dispositivos diferentes - então o padrão é derivar da tipificação. Valores
    informados explicitamente prevalecem, e a derivação só acontece quando a
    citação é reconhecida na base do CEDM.
    """
    inciso = dados.get("numero_inciso_cedm")
    artigo = dados.get("numero_artigo_cedm")
    if inciso and artigo:
        return str(inciso), str(artigo)

    transgressao = extrair_de_texto(dados.get("tipificacao_cedm"))
    if transgressao is not None:
        return str(inciso or transgressao.inciso), str(artigo or transgressao.artigo)

    if not inciso:
        pendentes.append("número do inciso do CEDM")
    if not artigo:
        pendentes.append("número do artigo do CEDM")
    return (
        str(inciso) if inciso else "[PREENCHER: número do inciso do CEDM]",
        str(artigo) if artigo else "[PREENCHER: número do artigo do CEDM]",
    )


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

    inciso_cedm, artigo_cedm = _inciso_e_artigo(dados, pendentes)

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
        # normalmente derivados de tipificacao_cedm (ver _inciso_e_artigo).
        "numero_inciso_cedm": inciso_cedm,
        "numero_artigo_cedm": artigo_cedm,
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
