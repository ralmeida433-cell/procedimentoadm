"""Metadados de interface dos campos do formulário web.

Separado da lógica (app.py) de propósito: aqui ficam só textos de ajuda
(tooltips com base normativa no CEDM), listas de opções de dropdown e o
agrupamento lógico dos campos. Nada aqui altera regra de negócio - os
VALORES das opções de posto são exatamente os que o validador jurídico
(`schema.OFICIAIS` / `schema.GRADUADOS_ELEGIVEIS`) e os modelos .docx
esperam, para não quebrar a validação de competência nem a geração.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- dropdowns

# (valor gravado, rótulo exibido). O valor segue a nomenclatura canônica que
# o validador reconhece; o rótulo traz a forma abreviada da PMMG + extenso.
OPCOES_POSTO: list[tuple[str, str]] = [
    ("Soldado", "Sd PM — Soldado"),
    ("Cabo", "Cb PM — Cabo"),
    ("3º Sargento", "3º Sgt PM — 3º Sargento"),
    ("2º Sargento", "2º Sgt PM — 2º Sargento"),
    ("1º Sargento", "1º Sgt PM — 1º Sargento"),
    ("Subtenente", "Sub Ten PM — Subtenente"),
    ("Cadete", "Cadete PM"),
    ("Aspirante a Oficial", "Asp Of PM — Aspirante a Oficial"),
    ("2º Tenente", "2º Ten PM — 2º Tenente"),
    ("1º Tenente", "1º Ten PM — 1º Tenente"),
    ("Capitão", "Cap PM — Capitão"),
    ("Major", "Maj PM — Major"),
    ("Tenente-Coronel", "Ten Cel PM — Tenente-Coronel"),
    ("Coronel", "Cel PM — Coronel"),
]

_POSTOS_VALIDOS = {valor for valor, _ in OPCOES_POSTO}

# Reconhece a forma abreviada da PMMG (como aparece nos documentos reais -
# "1º Ten PM", "TEN CEL", "2.º Sgt PM" etc.) e normaliza para o valor
# canônico usado pelo validador e pelos <select> do formulário. Usado para
# corrigir o posto/graduação extraído de um documento existente (`/extrair`),
# que vem como texto livre e quase nunca já está na forma canônica.
# Ordem importa: padrões mais específicos (Ten Cel, Sub Ten) antes dos
# genéricos (Ten, Cel) para não casar errado.
_PADROES_POSTO = [
    (re.compile(r"ten[\s.\-]*cel|tenente[\s\-]*coronel", re.IGNORECASE), "Tenente-Coronel"),
    (re.compile(r"sub[\s.\-]*ten|subtenente", re.IGNORECASE), "Subtenente"),
    (re.compile(r"asp(irante)?[\s.\-]*(a[\s.\-]*)?of(icial)?", re.IGNORECASE), "Aspirante a Oficial"),
    (re.compile(r"1[º°.\s]*ten|1[º°.\s]*tenente", re.IGNORECASE), "1º Tenente"),
    (re.compile(r"2[º°.\s]*ten|2[º°.\s]*tenente", re.IGNORECASE), "2º Tenente"),
    (re.compile(r"cap(it[aã]o)?\b", re.IGNORECASE), "Capitão"),
    (re.compile(r"maj(or)?\b", re.IGNORECASE), "Major"),
    (re.compile(r"\bcel\b|coronel", re.IGNORECASE), "Coronel"),
    (re.compile(r"cadete", re.IGNORECASE), "Cadete"),
    (re.compile(r"1[º°.\s]*sgt|1[º°.\s]*sargento", re.IGNORECASE), "1º Sargento"),
    (re.compile(r"2[º°.\s]*sgt|2[º°.\s]*sargento", re.IGNORECASE), "2º Sargento"),
    (re.compile(r"3[º°.\s]*sgt|3[º°.\s]*sargento", re.IGNORECASE), "3º Sargento"),
    (re.compile(r"\bcb\b|cabo", re.IGNORECASE), "Cabo"),
    (re.compile(r"\bsd\b|soldado", re.IGNORECASE), "Soldado"),
]


def normalizar_posto(bruto: str | None) -> str | None:
    """Normaliza um posto/graduação em texto livre (ex.: extraído de um
    documento) para o valor canônico do sistema. Se já estiver no formato
    canônico, retorna sem alterar. Se não reconhecer nenhum padrão, retorna
    o valor original sem alteração (não inventa um posto que não identificou
    com segurança)."""
    if not bruto:
        return bruto
    if bruto in _POSTOS_VALIDOS:
        return bruto
    for padrao, canonico in _PADROES_POSTO:
        if padrao.search(bruto):
            return canonico
    return bruto


OPCOES_REGIAO: list[tuple[str, str]] = [
    (f"{n}ª RPM", f"{n}ª RPM — {n}ª Região da PMMG") for n in range(1, 20)
]

# Campo -> lista de opções (valor, rótulo)
CAMPOS_OPCOES: dict[str, list[tuple[str, str]]] = {
    "posto_graduacao_sindicado": OPCOES_POSTO,
    "posto_autoridade_processante": OPCOES_POSTO,
    "posto_autoridade_delegante": OPCOES_POSTO,
    "posto_comunicante": OPCOES_POSTO,
    "posto_testemunha": OPCOES_POSTO,
    "numero_regiao_pm": OPCOES_REGIAO,
}


# ---------------------------------------------------------------- tooltips

# Orientação normativa curta por campo (base: CEDM - Lei 14.310/2002 - e MAPPA).
TOOLTIPS: dict[str, str] = {
    # Dados do fato
    "reds": "REDS — Registro de Evento de Defesa Social que motivou a apuração, se houver. Nem todo PCD nasce de um REDS (pode originar de comunicação/observação interna) - deixe em branco se não existir, não é exigido pelo MAPPA.",
    "data_fato": "Data exata em que ocorreu a suposta transgressão disciplinar.",
    "hora_fato": "Hora aproximada do fato (formato HH:MM). Deixe em branco se não for possível precisar.",
    "cidade_fato": "Município onde o fato ocorreu.",
    "local_fato": "Local específico do fato (endereço, unidade, via etc.).",
    "resumo_fato": "Descreva a conduta com suas palavras (ex.: 'faltou ao serviço') e clique em 'Analisar com IA': o sistema reescreve o texto na redação oficial exigida pelos modelos e sugere a transgressão do CEDM correspondente, com o texto do inciso para você conferir. Evite juízo de valor; foque nos fatos.",
    "tipificacao_cedm": "Inciso e artigo do CEDM correspondentes à conduta (ex.: inciso I do art. 13). A tipificação atende ao princípio da legalidade.",
    # Sindicado
    "nome_sindicado": "Nome completo do militar sindicado, sem abreviações, conforme o sistema de gestão de pessoal.",
    "re_sindicado": "Número de matrícula (identificação) do sindicado.",
    "posto_graduacao_sindicado": "Posto ou graduação do sindicado na data do fato.",
    "unidade_sindicado": "Unidade de lotação do sindicado (ex.: 1º BPM).",
    # Comunicante
    "nome_comunicante": "Nome completo de quem elaborou a Comunicação Disciplinar.",
    "posto_comunicante": "Posto ou graduação do comunicante.",
    "re_comunicante": "Número de matrícula do comunicante.",
    "unidade_comunicante": "Unidade de lotação do comunicante.",
    "data_comunicacao": "Data em que a Comunicação Disciplinar foi apresentada (art. 46 do MAPPA: 5 dias úteis do conhecimento do fato).",
    # Autoridades / instauração
    "data_instauracao": "Data do despacho de instauração. Marco inicial do prazo de conclusão do PCD (15 dias corridos, prorrogáveis por 10).",
    "nome_autoridade_processante": "Nome completo do encarregado (autoridade processante) que conduzirá a apuração.",
    "posto_autoridade_processante": "Posto/graduação do encarregado. Deve ter precedência hierárquica sobre o sindicado (art. 70 do CEDM).",
    "re_autoridade_processante": "Número de matrícula do encarregado.",
    "unidade_autoridade_processante": "Unidade de lotação do encarregado.",
    "estavel_autoridade_processante": "Marque 'Sim' se o encarregado é oficial ou graduado estável. Requisito de competência para presidir o PCD (art. 70 do CEDM).",
    "nome_autoridade_delegante": "Nome completo da autoridade que detém a competência para instaurar (autoridade delegante). Sem ela, o ato é nulo.",
    "posto_autoridade_delegante": "Posto/graduação da autoridade delegante.",
    # Numeração / região
    "numero_processo": "Número sequencial do processo na unidade (controle interno).",
    "numero_regiao_pm": "RPM — Região da Polícia Militar responsável pela apuração.",
    "numero_batalhao_pm": "Número do Batalhão (ex.: 1 para 1º BPM).",
    "cidade_sede": "Município sede da unidade que instaura o processo.",
    "numero_comunicacao_disciplinar": "Número da Comunicação Disciplinar que originou o PCD.",
    "numero_folhas_comunicacao_disciplinar": "Quantidade de folhas da Comunicação Disciplinar anexada aos autos.",
    "numero_folhas_escala_servico": "Quantidade de folhas da escala de serviço anexa, quando houver.",
    # Ocorrências processuais
    "parentesco_ou_inimizade": "Marque 'Sim' se o encarregado tem parentesco, amizade íntima ou inimizade notória com o sindicado — hipótese de impedimento (deve declarar-se impedido).",
    "observacoes_impedimento": "Detalhe a situação de impedimento declarada, se houver.",
    "prorrogado": "Marque 'Sim' se o prazo de conclusão foi prorrogado por mais 10 dias corridos, a pedido ou por determinação da autoridade.",
    "data_hora_militar_fato": "Grupo Data-Hora (GDH) militar do fato. Pode deixar em branco: é gerado automaticamente a partir da Data e da Hora do Fato (ex.: 050820Mar26 - Qui). Preencha só se quiser sobrescrever.",
}


# ---------------------------------------------------------------- agrupamento

# Agrupamento lógico da etapa de INSTAURAÇÃO. Cada grupo lista as chaves na
# ordem em que devem aparecer. Campos não listados aqui caem num grupo final
# "Outros" automaticamente (rede de segurança para não perder campo nenhum).
GRUPOS_INSTAURACAO: list[tuple[str, list[str]]] = [
    ("Dados do Fato (ocorrência)", [
        "reds", "data_fato", "hora_fato", "cidade_fato", "local_fato",
        "resumo_fato", "tipificacao_cedm",
    ]),
    ("Envolvimento", [
        # Sindicado
        "nome_sindicado", "re_sindicado", "posto_graduacao_sindicado", "unidade_sindicado",
        # Comunicante
        "nome_comunicante", "posto_comunicante", "re_comunicante", "unidade_comunicante",
        "data_comunicacao",
    ]),
    ("Instauração (competência e delegação)", [
        "data_instauracao",
        "nome_autoridade_processante", "posto_autoridade_processante",
        "re_autoridade_processante", "unidade_autoridade_processante",
        "estavel_autoridade_processante",
        "nome_autoridade_delegante", "posto_autoridade_delegante",
    ]),
    ("Informações Adicionais", [
        "numero_processo", "numero_regiao_pm", "numero_batalhao_pm", "cidade_sede",
        "numero_comunicacao_disciplinar", "numero_folhas_comunicacao_disciplinar",
        "numero_folhas_escala_servico",
        "parentesco_ou_inimizade", "observacoes_impedimento", "prorrogado",
    ]),
]
