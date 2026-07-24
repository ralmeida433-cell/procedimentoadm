"""Cálculo de prazos do PCD conforme o CEDM (Lei 14.310/2002) e o MAPPA.

Regras adotadas (corrigidas conforme `tabela-prazos-consolidada.md` da skill
especialista-mappa, que consolida o texto do MAPPA - a redação do modelo de
Despacho de Instauração, "Prazo: 15 (quinze) dias corridos...", só dá o prazo
base, não o valor da prorrogação):
- Conclusão do processo: 15 dias corridos, prorrogáveis por até 10 dias
  corridos mediante justificativa fundamentada (total máximo de 25 dias
  corridos) - NÃO é "por igual período" (isso daria 30, valor incorreto usado
  numa versão anterior deste módulo).
- Prazo de defesa: 5 dias úteis, contados da citação ou do encerramento
  da instrução processual.
- Art. 39 do MAPPA: "...não se computando os prazos destinados à defesa"
  - os dois prazos de 5 dias úteis (defesa prévia e RED final) NÃO contam
  dentro do prazo regulamentar de 15(+10) dias corridos; correm à parte,
  somados ao prazo de conclusão. Auditoria encontrou esse ponto ausente
  numa versão anterior (`calcular_prazo_conclusao` somava só 15/25 dias
  corridos, sem excluir os dias de defesa - o que gerava alerta de atraso
  falso). Corrigido em `calcular_prazo_conclusao`.
- Prescrição da pretensão punitiva (art. 508, MAPPA): varia pela natureza
  da sanção (2, 4 ou 5 anos). O PCD só trata de transgressões de natureza
  NÃO demissionária (ver despacho de instauração e Ofício Circular
  00855.1.1/2024-CPM citado nos modelos), logo o prazo aplicável aqui é
  sempre o do inciso I do art. 508: 2 (dois) anos, contados da data do
  fato (art. 509).

Este módulo não conhece feriados (apenas fins de semana). Se a unidade
precisar considerar feriados municipais/estaduais, informe um calendário
específico antes de usar em produção.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

BASE_LEGAL = "CEDM - Lei 14.310/2002"

PRAZO_CONCLUSAO_DIAS_CORRIDOS = 15
PRORROGACAO_CONCLUSAO_DIAS_CORRIDOS = 10
PRAZO_DEFESA_DIAS_UTEIS = 5
PRESCRICAO_PCD_ANOS = 2  # art. 508, I, MAPPA - PCD é sempre não demissionário


def _proximo_dia_util(d: date) -> date:
    while d.weekday() >= 5:  # 5=sábado, 6=domingo
        d += timedelta(days=1)
    return d


def somar_dias_uteis(data_inicio: date, dias_uteis: int) -> date:
    """Avança `dias_uteis` dias úteis a partir de `data_inicio` (exclusive)."""
    atual = data_inicio
    restantes = dias_uteis
    while restantes > 0:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            restantes -= 1
    return atual


def calcular_prazo_defesa(data_referencia: date) -> date:
    """Data-limite para apresentação de razões de defesa (5 dias úteis)."""
    return somar_dias_uteis(data_referencia, PRAZO_DEFESA_DIAS_UTEIS)


def calcular_prazo_conclusao(
    data_instauracao: date,
    prorrogado: bool = False,
    *,
    data_citacao: date | None = None,
    data_vista_final: date | None = None,
) -> date:
    """Data-limite para conclusão do PCD.

    15 dias corridos da instauração; se `prorrogado`, soma mais 10 dias
    corridos (prorrogação exige justificativa fundamentada - a justificativa
    em si não é validada aqui, apenas o efeito no prazo).

    Art. 39 do MAPPA: os prazos de defesa (5 dias úteis cada, para a defesa
    prévia e para a RED final) NÃO contam no prazo regulamentar - por isso,
    para cada janela de defesa já iniciada (`data_citacao`/`data_vista_final`
    informados), somamos de volta os dias corridos efetivamente consumidos
    por ela. Sem essas datas, o cálculo cai no prazo-base (comportamento
    anterior), pois ainda não há como saber quantos dias a defesa vai
    consumir.
    """
    dias = PRAZO_CONCLUSAO_DIAS_CORRIDOS + (PRORROGACAO_CONCLUSAO_DIAS_CORRIDOS if prorrogado else 0)
    prazo = data_instauracao + timedelta(days=dias)

    if data_citacao:
        prazo += calcular_prazo_defesa(data_citacao) - data_citacao
    if data_vista_final:
        prazo += calcular_prazo_defesa(data_vista_final) - data_vista_final

    return prazo


@dataclass
class StatusPrazo:
    tipo: str
    data_limite: date
    atrasado: bool
    dias_atraso: int
    dias_restantes: int


def verificar_atraso(data_limite: date, tipo: str, data_referencia: date | None = None) -> StatusPrazo:
    hoje = data_referencia or date.today()
    delta = (hoje - data_limite).days
    return StatusPrazo(
        tipo=tipo,
        data_limite=data_limite,
        atrasado=delta > 0,
        dias_atraso=max(delta, 0),
        dias_restantes=max(-delta, 0),
    )


@dataclass
class StatusPrescricao:
    data_limite: date
    prescrito: bool
    dias_restantes: int


def verificar_prescricao(data_fato: date, data_referencia: date | None = None) -> StatusPrescricao:
    """Verifica a prescrição da pretensão punitiva (art. 508, I c/c 509, MAPPA).

    PCD trata só de transgressão não demissionária -> prazo fixo de 2 anos,
    contados da data do fato (regra geral do art. 509; não trata aqui das
    exceções de transgressão permanente/residual a delito de falsidade,
    que exigiriam outra data de início - ver cap. XVI se isso importar).
    """
    hoje = data_referencia or date.today()
    try:
        data_limite = data_fato.replace(year=data_fato.year + PRESCRICAO_PCD_ANOS)
    except ValueError:
        # 29 de fevereiro em ano que não é bissexto 2 anos depois
        data_limite = data_fato.replace(month=2, day=28, year=data_fato.year + PRESCRICAO_PCD_ANOS)
    delta = (data_limite - hoje).days
    return StatusPrescricao(data_limite=data_limite, prescrito=delta < 0, dias_restantes=max(delta, 0))


def gerar_alertas_processo(processo: dict, data_referencia: date | None = None) -> list[dict]:
    """Recebe um dict com dados do processo e retorna alertas de prazo.

    Chaves esperadas em `processo` (as ausentes são ignoradas):
      - data_instauracao (date)
      - prorrogado (bool)
      - data_conclusao_real (date | None) - se já concluído, não gera alerta
      - data_fato (date) - para a verificação de prescrição
      - data_citacao (date) - citação inicial, para o prazo de defesa prévia
      - data_defesa_previa_apresentada (date | None)
      - data_vista_final (date) - abertura da vista final, para o prazo da RED
      - data_red_apresentada (date | None)
      - data_notificacao_testemunha, data_notificacao_sindicado (date | None)
      - data_oitiva (date | None) - para a checagem de antecedência da notificação
    """
    hoje = data_referencia or date.today()
    alertas: list[dict] = []

    data_instauracao = processo.get("data_instauracao")
    if data_instauracao and not processo.get("data_conclusao_real"):
        prazo = calcular_prazo_conclusao(
            data_instauracao,
            processo.get("prorrogado", False),
            data_citacao=processo.get("data_citacao"),
            data_vista_final=processo.get("data_vista_final"),
        )
        status = verificar_atraso(prazo, "conclusao", hoje)
        if status.atrasado:
            alertas.append({
                "tipo": "ATRASO_EM_PROCESSO",
                "prazo": "conclusao",
                "mensagem": (
                    f"Prazo de conclusão vencido em {status.data_limite.isoformat()} "
                    f"({status.dias_atraso} dia(s) de atraso)."
                ),
                "dias_atraso": status.dias_atraso,
            })
        elif status.dias_restantes <= 5:
            alertas.append({
                "tipo": "PRAZO_PROXIMO_VENCIMENTO",
                "prazo": "conclusao",
                "mensagem": (
                    f"Prazo de conclusão vence em {status.data_limite.isoformat()} "
                    f"({status.dias_restantes} dia(s) restante(s))."
                ),
                "dias_atraso": 0,
            })

    for campo_data, campo_apresentada, prazo_nome, rotulo in [
        ("data_citacao", "data_defesa_previa_apresentada", "defesa_previa", "razões de defesa prévia"),
        ("data_vista_final", "data_red_apresentada", "red", "razões escritas de defesa final (RED)"),
    ]:
        data_referencia_prazo = processo.get(campo_data)
        data_apresentada = processo.get(campo_apresentada)

        if data_referencia_prazo and not data_apresentada:
            prazo_defesa = calcular_prazo_defesa(data_referencia_prazo)
            status = verificar_atraso(prazo_defesa, prazo_nome, hoje)
            if status.atrasado:
                alertas.append({
                    "tipo": "ATRASO_EM_PROCESSO",
                    "prazo": prazo_nome,
                    "mensagem": (
                        f"Prazo para {rotulo} vencido em {status.data_limite.isoformat()} "
                        f"({status.dias_atraso} dia(s) de atraso)."
                    ),
                    "dias_atraso": status.dias_atraso,
                })
        elif data_referencia_prazo and data_apresentada:
            # A defesa já foi apresentada - confere se foi DENTRO do prazo de
            # 5 dias úteis, e não só se está pendente (achado de auditoria:
            # antes disso o sistema parava de checar assim que a data era
            # preenchida, deixando passar cerceamento de defesa despercebido).
            prazo_defesa = calcular_prazo_defesa(data_referencia_prazo)
            if data_apresentada > prazo_defesa:
                dias_apos = (data_apresentada - prazo_defesa).days
                alertas.append({
                    "tipo": "DEFESA_FORA_DO_PRAZO",
                    "prazo": prazo_nome,
                    "mensagem": (
                        f"{rotulo.capitalize()} apresentada em {data_apresentada.isoformat()}, "
                        f"{dias_apos} dia(s) após o limite de {prazo_defesa.isoformat()} - "
                        "risco de intempestividade/preclusão (ver art. 41 do MAPPA sobre "
                        "revelia e defensor ad hoc)."
                    ),
                    "dias_atraso": dias_apos,
                })

    for campo_notificacao, rotulo in [
        ("data_notificacao_testemunha", "da testemunha"),
        ("data_notificacao_sindicado", "do sindicado para a audição"),
    ]:
        data_notificacao = processo.get(campo_notificacao)
        data_oitiva = processo.get("data_oitiva")
        if data_notificacao and data_oitiva and data_notificacao >= data_oitiva:
            alertas.append({
                "tipo": "NOTIFICACAO_SEM_ANTECEDENCIA",
                "prazo": "oitiva",
                "mensagem": (
                    f"Notificação {rotulo} ({data_notificacao.isoformat()}) não tem antecedência "
                    f"mínima em relação à data da oitiva ({data_oitiva.isoformat()}) - confira se "
                    "houve tempo hábil de ciência antes do ato (risco de cerceamento de defesa)."
                ),
                "dias_atraso": 0,
            })

    data_fato = processo.get("data_fato")
    if data_fato and not processo.get("data_conclusao_real"):
        status_prescricao = verificar_prescricao(data_fato, hoje)
        if status_prescricao.prescrito:
            alertas.append({
                "tipo": "PRESCRICAO",
                "prazo": "prescricao",
                "mensagem": (
                    f"Pretensão punitiva PRESCRITA desde {status_prescricao.data_limite.isoformat()} "
                    f"(art. 508, I, do MAPPA - 2 anos da data do fato). Suscite o incidente à "
                    "autoridade delegante para arquivamento (art. 510)."
                ),
                "dias_atraso": 0,
            })
        elif status_prescricao.dias_restantes <= 60:
            alertas.append({
                "tipo": "PRESCRICAO_PROXIMA",
                "prazo": "prescricao",
                "mensagem": (
                    f"Pretensão punitiva prescreve em {status_prescricao.data_limite.isoformat()} "
                    f"({status_prescricao.dias_restantes} dia(s) restante(s))."
                ),
                "dias_atraso": 0,
            })

    return alertas
