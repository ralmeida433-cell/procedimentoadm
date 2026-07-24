"""Deriva as variáveis do template `ata_reuniao_cedmu.docx`.

Baseado no MODELO REFERENCIAL de "Ata de Reunião do CEDMU" do
`especialista-mappa/references/cap17-cedmu.md` (Cap. XVII do MAPPA).

As seções de fundamentação e o parecer (itens 3 a 7 da ata) são o
julgamento do próprio Conselho - o sistema nunca fabrica esse conteúdo;
fica marcado [PREENCHER] até o CEDMU redigir e informar o texto.
"""
from __future__ import annotations

from .formatacao import MESES_PT


def _preencher_ou_marcar(dados: dict, pendentes: list[str], campo: str, rotulo: str) -> str:
    valor = dados.get(campo)
    if valor:
        return str(valor)
    pendentes.append(rotulo)
    return f"[PREENCHER: {rotulo}]"


def _qualificacao(dados: dict, pendentes: list[str], prefixo: str, rotulo: str) -> str:
    re_ = dados.get(f"re_{prefixo}")
    posto = dados.get(f"posto_{prefixo}")
    nome = dados.get(f"nome_{prefixo}")
    if re_ and posto and nome:
        return f"nº {re_}, {posto} PM {nome}"
    pendentes.append(rotulo)
    return f"[PREENCHER: {rotulo}]"


def preparar_dados_ata_cedmu(dados: dict) -> tuple[dict, list[str]]:
    """Retorna (variáveis_do_template, campos_pendentes_de_preenchimento_manual)."""
    pendentes: list[str] = []

    data_reuniao = dados.get("data_reuniao")
    data_bie_conselho = dados.get("data_bie_conselho")

    variaveis = {
        "referencia_procedimento": _preencher_ou_marcar(
            dados, pendentes, "referencia_procedimento",
            "referência do procedimento analisado (ex.: Despacho/Portaria nº ___)",
        ),
        "cidade_reuniao": _preencher_ou_marcar(dados, pendentes, "cidade_reuniao", "cidade da reunião"),
        "local_reuniao": _preencher_ou_marcar(dados, pendentes, "local_reuniao", "local da reunião"),
        "numero_conselho": _preencher_ou_marcar(dados, pendentes, "numero_conselho", "nº do Conselho (CEDMU)"),
        "numero_bie_conselho": _preencher_ou_marcar(
            dados, pendentes, "numero_bie_conselho", "nº do BI/BGPM/BGBM de designação do Conselho"
        ),
        "qualificacao_presidente": _qualificacao(
            dados, pendentes, "presidente", "qualificação do Presidente do Conselho"
        ),
        "qualificacao_membro": _qualificacao(dados, pendentes, "membro", "qualificação do Membro"),
        "qualificacao_escrivao": _qualificacao(
            dados, pendentes, "escrivao", "qualificação do Membro/Escrivão"
        ),
        "nome_presidente_upper": _preencher_ou_marcar(
            dados, pendentes, "nome_presidente", "nome do Presidente"
        ).upper(),
        "posto_presidente": _preencher_ou_marcar(dados, pendentes, "posto_presidente", "posto do Presidente"),
        "nome_membro_upper": _preencher_ou_marcar(dados, pendentes, "nome_membro", "nome do Membro").upper(),
        "posto_membro": _preencher_ou_marcar(dados, pendentes, "posto_membro", "posto do Membro"),
        "nome_escrivao_upper": _preencher_ou_marcar(
            dados, pendentes, "nome_escrivao", "nome do Membro/Escrivão"
        ).upper(),
        "posto_escrivao": _preencher_ou_marcar(
            dados, pendentes, "posto_escrivao", "posto do Membro/Escrivão"
        ),
        "nome_escrivao": _preencher_ou_marcar(dados, pendentes, "nome_escrivao", "nome do Membro/Escrivão"),
        "texto_comparecimento_acusado": (
            "não tendo comparecido o acusado/indicado para recompensa"
            if not dados.get("acusado_compareceu")
            else "tendo comparecido o acusado/indicado para recompensa"
        ),
        "qualificacao_acusado": _preencher_ou_marcar(
            dados, pendentes, "qualificacao_acusado", "qualificação do(s) acusado(s)/indicado(s)"
        ),
        "finalidade_texto": _preencher_ou_marcar(
            dados, pendentes, "finalidade_texto", "finalidade (seção 2 da ata)"
        ),
        "verificacao_preliminar_texto": _preencher_ou_marcar(
            dados, pendentes, "verificacao_preliminar_texto", "verificação preliminar (seção 3 da ata)"
        ),
        "fundamentacao_fatica_texto": _preencher_ou_marcar(
            dados, pendentes, "fundamentacao_fatica_texto", "fundamentação fática (seção 4 da ata)"
        ),
        "fundamentacao_legal_texto": _preencher_ou_marcar(
            dados, pendentes, "fundamentacao_legal_texto", "fundamentação legal (seção 5 da ata)"
        ),
        "analise_merito_texto": _preencher_ou_marcar(
            dados, pendentes, "analise_merito_texto", "análise de mérito (seção 6 da ata)"
        ),
        "parecer_texto": _preencher_ou_marcar(
            dados, pendentes, "parecer_texto", "parecer do CEDMU (seção 7 da ata)"
        ),
        "hora_inicio_reuniao": _preencher_ou_marcar(
            dados, pendentes, "hora_inicio_reuniao", "hora de início da reunião"
        ),
        "hora_fim_reuniao": _preencher_ou_marcar(
            dados, pendentes, "hora_fim_reuniao", "hora de encerramento da reunião"
        ),
        "numero_regiao_pm": _preencher_ou_marcar(dados, pendentes, "numero_regiao_pm", "nº da Região de Polícia Militar"),
        "numero_batalhao_pm": _preencher_ou_marcar(dados, pendentes, "numero_batalhao_pm", "nº do Batalhão"),
    }

    if data_reuniao:
        variaveis["dia_reuniao"] = f"{data_reuniao.day:02d}"
        variaveis["mes_reuniao_extenso"] = MESES_PT[data_reuniao.month]
        variaveis["ano_reuniao"] = str(data_reuniao.year)
    else:
        pendentes.append("data da reunião")
        variaveis["dia_reuniao"] = "[PREENCHER: dia da reunião]"
        variaveis["mes_reuniao_extenso"] = "[PREENCHER: mês da reunião]"
        variaveis["ano_reuniao"] = "[PREENCHER: ano da reunião]"

    if data_bie_conselho:
        variaveis["data_bie_conselho"] = (
            f"{data_bie_conselho.day:02d}/{data_bie_conselho.month:02d}/{data_bie_conselho.year}"
        )
    else:
        pendentes.append("data do BI de designação do Conselho")
        variaveis["data_bie_conselho"] = "[PREENCHER: data do BI de designação do Conselho]"

    return variaveis, pendentes
