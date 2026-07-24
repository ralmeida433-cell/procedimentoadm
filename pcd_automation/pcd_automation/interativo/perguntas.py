"""Definição declarativa das perguntas de cada etapa do PCD.

Para adicionar um campo novo ao assistente interativo: (1) garanta que ele
já existe em `gerador_portarias.planilha.DEFINICAO_COLUNAS` (é de lá que
vem o rótulo e o tipo da pergunta) e (2) inclua a chave na lista
`campos_obrigatorios` ou `campos_opcionais` da etapa correspondente abaixo.
Nada mais precisa mudar - o assistente percorre essas listas sozinho.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pcd_automation.gerador_portarias import (
    abrir_vista_final,
    abrir_vista_inicial,
    gerar_cedmu,
    gerar_oficio,
    gerar_relatorio,
    instaurar_processo,
    notificar_oitiva,
    registrar_depoimento,
)


@dataclass
class Etapa:
    id: str
    titulo: str
    campos_obrigatorios: list[str]
    campos_opcionais: list[str]
    funcao: Callable


ETAPAS: list[Etapa] = [
    Etapa(
        id="instauracao",
        titulo="Instauração",
        campos_obrigatorios=[
            "nome_sindicado", "re_sindicado", "posto_graduacao_sindicado", "unidade_sindicado",
            "data_fato", "resumo_fato",
            "nome_autoridade_processante", "posto_autoridade_processante", "re_autoridade_processante",
            "nome_autoridade_delegante", "posto_autoridade_delegante", "data_instauracao",
            "nome_comunicante", "posto_comunicante", "re_comunicante", "unidade_comunicante", "data_comunicacao",
        ],
        campos_opcionais=[
            # REDS nem sempre existe (PCD pode nascer de comunicação interna, sem despacho de
            # central de emergência) - não é exigido pelo MAPPA, por isso é opcional.
            "reds",
            "numero_processo", "numero_regiao_pm", "numero_batalhao_pm", "unidade_autoridade_processante",
            "numero_comunicacao_disciplinar", "numero_folhas_comunicacao_disciplinar", "numero_folhas_escala_servico",
            "cidade_fato", "hora_fato", "local_fato", "tipificacao_cedm", "cidade_sede",
            "estavel_autoridade_processante", "parentesco_ou_inimizade", "observacoes_impedimento", "prorrogado",
        ],
        funcao=instaurar_processo,
    ),
    Etapa(
        id="vista_inicial",
        titulo="Vista Inicial (defesa prévia)",
        campos_obrigatorios=[
            "data_citacao", "numero_folha_inicial_defesa_previa", "numero_folha_final_defesa_previa",
        ],
        campos_opcionais=["numero_folhas_autos_defesa_previa", "numero_inciso_cedm", "numero_artigo_cedm"],
        funcao=abrir_vista_inicial,
    ),
    Etapa(
        id="oitiva",
        titulo="Oitiva (notificações)",
        campos_obrigatorios=[
            "data_oitiva", "hora_oitiva", "nome_testemunha", "posto_testemunha", "re_testemunha",
            "unidade_testemunha", "data_notificacao_testemunha", "data_notificacao_sindicado",
        ],
        campos_opcionais=["endereco_sede"],
        funcao=notificar_oitiva,
    ),
    Etapa(
        id="depoimento",
        titulo="Termo de Depoimento",
        campos_obrigatorios=["data_oitiva", "nome_testemunha", "posto_testemunha", "re_testemunha"],
        campos_opcionais=[
            "numero_ordem_testemunha", "nome_pai_testemunha", "nome_mae_testemunha", "idade_testemunha",
            "data_nascimento_testemunha", "sexo_testemunha", "nacionalidade_testemunha", "naturalidade_testemunha",
            "estado_civil_testemunha", "cpf_testemunha", "identidade_testemunha", "local_trabalho_testemunha",
            "telefone_celular_testemunha", "telefone_residencial_testemunha", "telefone_comercial_testemunha",
            "escolaridade_testemunha", "teor_depoimento", "hora_inicio_depoimento", "hora_fim_depoimento",
            "nome_defensor_sindicado",
        ],
        funcao=registrar_depoimento,
    ),
    Etapa(
        id="vista_final",
        titulo="Vista Final (RED)",
        campos_obrigatorios=["data_vista_final", "numero_folha_inicial_red", "numero_folha_final_red"],
        campos_opcionais=["numero_folhas_autos_red", "numero_inciso_cedm", "numero_artigo_cedm"],
        funcao=abrir_vista_final,
    ),
    Etapa(
        id="relatorio",
        titulo="Relatório do Encarregado",
        campos_obrigatorios=["analise_fatos_e_provas", "alegacoes_defesa_analise"],
        campos_opcionais=[
            "numero_folha_depoimento_testemunha", "objetos_apreendidos", "outras_provas",
            "data_hora_militar_fato", "em_servico_sindicado", "incidentes_processuais", "data_relatorio",
        ],
        funcao=gerar_relatorio,
    ),
    Etapa(
        id="oficio",
        titulo="Ofício de Remessa",
        campos_obrigatorios=["numero_oficio_remessa", "numero_folhas_autos_final"],
        campos_opcionais=["data_oficio_remessa"],
        funcao=gerar_oficio,
    ),
    Etapa(
        id="cedmu",
        titulo="Análise do CEDMU",
        campos_obrigatorios=[
            "data_reuniao", "numero_conselho", "nome_presidente", "posto_presidente", "re_presidente",
            "qualificacao_acusado", "finalidade_texto", "fundamentacao_legal_texto",
            "analise_merito_texto", "parecer_texto",
        ],
        campos_opcionais=[
            "referencia_procedimento", "cidade_reuniao", "local_reuniao", "numero_bie_conselho",
            "data_bie_conselho", "nome_membro", "posto_membro", "re_membro", "nome_escrivao",
            "posto_escrivao", "re_escrivao", "acusado_compareceu", "verificacao_preliminar_texto",
            "fundamentacao_fatica_texto", "hora_inicio_reuniao", "hora_fim_reuniao",
        ],
        funcao=gerar_cedmu,
    ),
]


def indice_etapa(id_etapa: str) -> int:
    for i, etapa in enumerate(ETAPAS):
        if etapa.id == id_etapa:
            return i
    raise ValueError(f"Etapa desconhecida: {id_etapa!r}")


def _etapa_dispensavel(etapa: Etapa, dados: dict) -> bool:
    """Etapas que não se aplicam a todo processo, dependendo dos dados.

    CEDMU (art. 523, §§1º-2º, do MAPPA): só é obrigatório remeter os autos
    ao CEDMU quando há razões escritas de defesa (RED) final apresentadas -
    processos sem RED (ex.: arquivados antes disso, ou sem contestação)
    não carecem de manifestação do Conselho.
    """
    if etapa.id == "cedmu":
        return not dados.get("data_red_apresentada")
    return False


def proxima_etapa(indice_atual: int, dados: dict) -> Etapa | None:
    """Próxima etapa após a de índice `indice_atual`, pulando etapas
    dispensáveis para os dados informados (ver `_etapa_dispensavel`)."""
    indice = indice_atual + 1
    while indice < len(ETAPAS):
        etapa = ETAPAS[indice]
        if _etapa_dispensavel(etapa, dados):
            indice += 1
            continue
        return etapa
    return None


def processo_concluido(indice_atual: int, dados: dict) -> bool:
    return proxima_etapa(indice_atual, dados) is None
