"""Validações jurídicas mínimas antes de instaurar um PCD (CEDM - Lei 14.310/2002)
e do MAPPA (Res. Conjunta 4.220/2012).

Este módulo verifica pré-condições formais e sinaliza risco de nulidade.
Ele NÃO substitui a análise da autoridade delegante - apenas impede que o
sistema gere uma portaria com dados incompletos, com impedimento declarado
ou estruturalmente inconsistente, e alerta sobre casos que exigem
confirmação humana (ex.: estabilidade de graduado, antiguidade quando dois
militares têm o mesmo posto/graduação - o sistema não tem como saber quem é
mais antigo, só compara posto/graduação).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pcd_automation.schema import (
    CAMPOS_OBRIGATORIOS_INSTAURACAO,
    GRADUADOS_ELEGIVEIS,
    OFICIAIS,
    precedencia_posto,
)


@dataclass
class ResultadoValidacao:
    ok: bool
    erros: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)


def validar_completude(dados: dict) -> list[str]:
    faltantes = [
        campo for campo in CAMPOS_OBRIGATORIOS_INSTAURACAO
        if not dados.get(campo)
    ]
    return [f"Campo obrigatório ausente: {campo}" for campo in faltantes]


def validar_autoridade_processante(dados: dict) -> tuple[list[str], list[str]]:
    """Verifica se a autoridade processante pode presidir o PCD.

    Regra (CEDM, conforme tooltip/documentação anterior deste sistema - art.
    70): oficial, ou subtenente/sargento estável. Mantida por não termos como
    conferir o texto integral do CEDM nesta sessão (só temos o MAPPA nas
    referências) - ver também `validar_precedencia_hierarquica`, que aplica
    uma regra ADICIONAL e mais específica de PCD (art. 62, ICCPM/BM 01/2014),
    cumulativa a esta.
    """
    erros: list[str] = []
    alertas: list[str] = []
    posto = dados.get("posto_autoridade_processante")

    if posto in OFICIAIS:
        return erros, alertas

    if posto in GRADUADOS_ELEGIVEIS:
        estavel = dados.get("estavel_autoridade_processante")
        if estavel is None:
            alertas.append(
                f"Autoridade processante é {posto}: confirme a estabilidade "
                "(campo 'estavel_autoridade_processante' não informado) antes de instaurar."
            )
        elif not estavel:
            erros.append(
                f"Autoridade processante ({posto}) não é estável - "
                "não pode presidir o PCD (CEDM)."
            )
        return erros, alertas

    erros.append(
        f"Posto/graduação da autoridade processante inválido ou não reconhecido: {posto!r}."
    )
    return erros, alertas


def validar_precedencia_hierarquica(dados: dict) -> tuple[list[str], list[str]]:
    """Confere precedência hierárquica (posto/graduação) entre os envolvidos.

    - Encarregado (autoridade processante) deve ter precedência hierárquica
      sobre o sindicado (art. 62, ICCPM/BM 01/2014, interpretativo do art.
      38 do MAPPA: "poderá ser militar de qualquer posto ou graduação, desde
      que possuidor de precedência hierárquica em relação ao comunicado").
    - Comunicante deve ter precedência hierárquica sobre o sindicado (art.
      35 do MAPPA: a CD é "feita e assinada por militar possuidor de
      precedência hierárquica em relação ao comunicado").

    Quando os dois têm o MESMO posto/graduação, a precedência se decide por
    antiguidade (data de praça/promoção) - dado que este sistema não
    coleta, por isso vira ALERTA (confirmar manualmente), não erro.
    Postos não reconhecidos não são avaliados aqui (outro erro já acusa).
    """
    erros: list[str] = []
    alertas: list[str] = []

    posto_sindicado = dados.get("posto_graduacao_sindicado")
    indice_sindicado = precedencia_posto(posto_sindicado)
    if indice_sindicado is None:
        return erros, alertas

    for campo_posto, rotulo, base_legal in [
        ("posto_autoridade_processante", "Autoridade processante (encarregado)", "art. 62, ICCPM/BM 01/2014"),
        ("posto_comunicante", "Comunicante", "art. 35 do MAPPA"),
    ]:
        posto_avaliado = dados.get(campo_posto)
        indice_avaliado = precedencia_posto(posto_avaliado)
        if indice_avaliado is None:
            continue
        if indice_avaliado < indice_sindicado:
            erros.append(
                f"{rotulo} ({posto_avaliado}) não tem precedência hierárquica sobre o sindicado "
                f"({posto_sindicado}) - {base_legal} exige precedência hierárquica."
            )
        elif indice_avaliado == indice_sindicado:
            alertas.append(
                f"{rotulo} e o sindicado têm o mesmo posto/graduação ({posto_sindicado}) - "
                f"confirme que o(a) {rotulo.lower()} é mais antigo(a) (precedência por antiguidade, "
                "não avaliada automaticamente)."
            )

    return erros, alertas


def validar_impedimentos_estruturais(dados: dict) -> list[str]:
    """Impedimentos que dá para checar pelos próprios dados, sem depender de
    autodeclaração (diferente de `validar_impedimento`, que só olha o campo
    'parentesco_ou_inimizade' preenchido manualmente).

    Compara por número de matrícula (RE) quando ambos os lados o têm - mais
    confiável que nome, que pode ter grafias diferentes -, e cai para nome
    (case-insensitive) como alternativa.
    """
    def mesma_pessoa(re_a, nome_a, re_b, nome_b) -> bool:
        if re_a and re_b:
            return str(re_a).strip() == str(re_b).strip()
        if nome_a and nome_b:
            return str(nome_a).strip().casefold() == str(nome_b).strip().casefold()
        return False

    erros: list[str] = []

    pares = [
        ("re_autoridade_processante", "nome_autoridade_processante", "re_comunicante", "nome_comunicante",
         "O encarregado não pode ser também o comunicante do mesmo fato (compromete a imparcialidade)."),
        ("re_autoridade_processante", "nome_autoridade_processante", "re_sindicado", "nome_sindicado",
         "O encarregado não pode ser o próprio sindicado."),
        ("re_autoridade_processante", "nome_autoridade_processante", "re_autoridade_delegante", "nome_autoridade_delegante",
         "A autoridade que instaura o processo (delegante) não pode ser, ao mesmo tempo, o encarregado."),
        ("re_testemunha", "nome_testemunha", "re_sindicado", "nome_sindicado",
         "Uma pessoa não pode figurar como testemunha e como sindicado no mesmo fato."),
    ]
    for re_a, nome_a, re_b, nome_b, mensagem in pares:
        if mesma_pessoa(dados.get(re_a), dados.get(nome_a), dados.get(re_b), dados.get(nome_b)):
            erros.append(mensagem)

    return erros


def validar_alertas_procedimentais(dados: dict) -> list[str]:
    """Avisos (não bloqueiam) sobre situações que exigem atenção do
    encarregado, mas que podem ter explicação legítima."""
    alertas: list[str] = []

    indice_testemunha = precedencia_posto(dados.get("posto_testemunha"))
    indice_encarregado = precedencia_posto(dados.get("posto_autoridade_processante"))
    if indice_testemunha is not None and indice_encarregado is not None and indice_testemunha > indice_encarregado:
        alertas.append(
            f"A testemunha ({dados.get('posto_testemunha')}) tem precedência hierárquica sobre o "
            f"encarregado ({dados.get('posto_autoridade_processante')}) - o encarregado não deve "
            "intimá-la diretamente; considere requisitar a oitiva à autoridade superior competente."
        )

    unidade_sindicado = dados.get("unidade_sindicado")
    unidade_processante = dados.get("unidade_autoridade_processante") or dados.get("unidade_comunicante")
    if unidade_sindicado and unidade_processante and unidade_sindicado.strip().casefold() != unidade_processante.strip().casefold():
        alertas.append(
            f"Unidade do sindicado ({unidade_sindicado}) difere da unidade da autoridade processante "
            f"({unidade_processante}) - confirme se há vínculo de jurisdição (ex.: adido) que justifique."
        )

    if dados.get("data_relatorio") and not dados.get("data_red_apresentada"):
        alertas.append(
            "Há data de relatório mas nenhuma data de apresentação da RED registrada - confirme se "
            "há Termo de Recusa/revelia nos autos (art. 41 do MAPPA) antes de concluir."
        )

    return alertas


def _para_inteiro(valor) -> int | None:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return None


def validar_numeracao_folhas(dados: dict) -> list[str]:
    """A numeração de folhas dos autos só cresce ao longo do processo -
    confere isso entre os pares de campos disponíveis. Ignora silenciosamente
    valores não numéricos (texto livre incorreto já é outro tipo de
    problema, não desta checagem)."""
    alertas: list[str] = []

    # Cada Termo de Abertura de Vista numera os autos "de 01 a N" (ambos os
    # TAVs começam na folha 01), então NÃO se compara folha-inicial de um com
    # folha-final do outro. O que só cresce é a folha FINAL / a contagem total
    # de folhas dos autos, conforme documentos vão sendo juntados.
    pares = [
        ("numero_folha_final_defesa_previa", "numero_folha_final_red",
         "a folha final da Vista Inicial (defesa prévia) ser menor ou igual à folha final da Vista Final (RED) - os autos só crescem"),
        ("numero_folhas_autos_defesa_previa", "numero_folhas_autos_red",
         "a contagem de folhas dos autos na Vista Inicial ser menor ou igual à da Vista Final (RED) - os autos só crescem"),
        ("numero_folhas_autos_red", "numero_folhas_autos_final",
         "a contagem de folhas dos autos na Vista Final (RED) ser menor ou igual à do Ofício de Remessa - os autos só crescem"),
    ]
    for campo_anterior, campo_posterior, descricao in pares:
        valor_anterior = _para_inteiro(dados.get(campo_anterior))
        valor_posterior = _para_inteiro(dados.get(campo_posterior))
        if valor_anterior is not None and valor_posterior is not None and valor_anterior > valor_posterior:
            alertas.append(
                f"Numeração de folhas fora de ordem: esperava-se {descricao} "
                f"({campo_anterior}={valor_anterior}, {campo_posterior}={valor_posterior})."
            )
    return alertas


def validar_impedimento(dados: dict) -> list[str]:
    if dados.get("parentesco_ou_inimizade"):
        obs = dados.get("observacoes_impedimento", "")
        return [
            "Impedimento declarado (parentesco ou inimizade entre autoridade "
            f"processante e sindicado) - princípio da imparcialidade violado. {obs}".strip()
        ]
    return []


# Ordem cronológica esperada dos marcos do PCD - cada par (anterior, posterior)
# só é conferido se AMBAS as datas estiverem presentes em `dados` (funciona em
# qualquer estágio do processo, não só na instauração).
_SEQUENCIA_DATAS_ESPERADA = [
    ("data_fato", "data_comunicacao", "o fato ocorrer antes da Comunicação Disciplinar"),
    ("data_comunicacao", "data_instauracao", "a Comunicação Disciplinar anteceder a instauração"),
    ("data_instauracao", "data_citacao", "a instauração anteceder a citação para defesa prévia"),
    ("data_citacao", "data_defesa_previa_apresentada", "a citação anteceder a defesa prévia apresentada"),
    ("data_citacao", "data_vista_final", "a citação inicial anteceder a abertura da vista final (RED)"),
    ("data_instauracao", "data_oitiva", "a instauração anteceder a data da oitiva"),
    ("data_oitiva", "data_vista_final", "a oitiva anteceder a abertura da vista final (RED)"),
    ("data_vista_final", "data_red_apresentada", "a abertura da vista final anteceder a RED apresentada"),
    ("data_vista_final", "data_relatorio", "a abertura da vista final anteceder o relatório"),
    ("data_red_apresentada", "data_relatorio", "a RED apresentada anteceder o relatório"),
    ("data_relatorio", "data_oficio_remessa", "o relatório anteceder o ofício de remessa"),
]

# Campos de data considerados para a regra CRONO-01 (o fato é sempre o
# primeiro evento do processo - "não existe processo sobre um fato do
# futuro"). Deliberadamente não inclui `data_nascimento_testemunha` (não é um
# evento do PROCESSO) nem `data_bie_conselho`/`data_reuniao` do CEDMU (podem
# preceder o fato em teoria, já que o Conselho é órgão permanente da
# Unidade, não criado para este caso específico).
_CAMPOS_DATA_POSTERIORES_AO_FATO = [
    "data_comunicacao", "data_instauracao", "data_citacao", "data_defesa_previa_apresentada",
    "data_oitiva", "data_notificacao_testemunha", "data_notificacao_sindicado",
    "data_vista_final", "data_red_apresentada", "data_relatorio", "data_oficio_remessa",
]


def validar_consistencia_datas(dados: dict) -> list[str]:
    """Confere a ordem cronológica lógica entre os marcos do processo.

    Retorna ALERTAS (não bloqueia nada) - datas fora de ordem quase sempre
    indicam erro de digitação, mas podem excepcionalmente ter explicação
    (ex.: diligência complementar), então não travam a geração de peças.
    """
    alertas: list[str] = []

    data_fato = dados.get("data_fato")
    if data_fato:
        for campo in _CAMPOS_DATA_POSTERIORES_AO_FATO:
            valor = dados.get(campo)
            if valor and valor < data_fato:
                alertas.append(
                    f"Datas fora de ordem: '{campo}' ({valor.isoformat()}) é anterior à data do fato "
                    f"({data_fato.isoformat()}) - não pode haver ato do processo antes do próprio fato."
                )

    for campo_anterior, campo_posterior, descricao in _SEQUENCIA_DATAS_ESPERADA:
        valor_anterior = dados.get(campo_anterior)
        valor_posterior = dados.get(campo_posterior)
        if valor_anterior and valor_posterior and valor_anterior > valor_posterior:
            alertas.append(
                f"Datas fora de ordem: esperava-se {descricao} ({campo_anterior}="
                f"{valor_anterior.isoformat()}, {campo_posterior}={valor_posterior.isoformat()})."
            )
    return alertas


def validar_processo(dados: dict) -> ResultadoValidacao:
    erros = validar_completude(dados)
    alertas: list[str] = []

    erros += validar_impedimento(dados)
    erros += validar_impedimentos_estruturais(dados)

    if not erros:
        erros_autoridade, alertas_autoridade = validar_autoridade_processante(dados)
        erros += erros_autoridade
        alertas += alertas_autoridade

        erros_precedencia, alertas_precedencia = validar_precedencia_hierarquica(dados)
        erros += erros_precedencia
        alertas += alertas_precedencia

    alertas += validar_consistencia_datas(dados)
    alertas += validar_alertas_procedimentais(dados)
    alertas += validar_numeracao_folhas(dados)

    return ResultadoValidacao(ok=not erros, erros=erros, alertas=alertas)
