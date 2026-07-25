"""Validação e formatação de redação oficial da PMMG.

Baseado nas regras de redação de documentos institucionais da PMMG
(MEGDI / MIV - Res. 5.450/2025): impessoalidade, vícios de linguagem
banidos, pronomes de tratamento, Grupo Data-Hora (GDH) e formatação de
horas.

Uso principal: `validar_texto(texto)` devolve uma lista de AVISOS de
redação (não bloqueia nada - apenas alerta o encarregado sobre desvios
antes de ele assinar). E `formatar_gdh` / `formatar_hora` ajudam a produzir
data/hora no padrão militar correto.
"""
from __future__ import annotations

import re
from datetime import date, datetime

# ------------------------------------------------------------ Grupo Data-Hora

MESES_GDH = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
# datetime.weekday(): segunda=0 ... domingo=6
SEMANA_GDH = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]


def formatar_gdh(momento: datetime | date, *, com_hora: bool = True, com_semana: bool = True) -> str:
    """Formata no padrão militar Grupo Data-Hora: `DDHHMMMesAA - Sem`.

    Ex.: 02/03/2024 15h02 (sábado) -> "021502Mar24 - Sab".
    - com_hora=False  -> "02Mar24 - Sab"
    - com_semana=False -> "021502Mar24"
    - ambos False      -> "02Mar24" (raiz)
    """
    dd = f"{momento.day:02d}"
    mes = MESES_GDH[momento.month - 1]
    aa = f"{momento.year % 100:02d}"
    hhmm = ""
    if com_hora and isinstance(momento, datetime):
        hhmm = f"{momento.hour:02d}{momento.minute:02d}"
    base = f"{dd}{hhmm}{mes}{aa}"
    if com_semana:
        return f"{base} - {SEMANA_GDH[momento.weekday()]}"
    return base


def formatar_hora(hora: int, minuto: int = 0) -> str:
    """Formata hora fora do GDH no padrão abreviado: `19h30min`, `19h00min`.

    Zero hora vai no singular ("0h00min"; por extenso seria "0 hora").
    """
    return f"{hora}h{minuto:02d}min"


def formatar_hora_br(valor) -> str:
    """Normaliza uma hora digitada de várias formas para o padrão oficial da
    PMMG em texto corrido: `XXhXXmin` (hora com 2 dígitos, minuto com 2
    dígitos), ex.: "8" -> "08h00min", "8:30" -> "08h30min", "1502" ->
    "15h02min", "8h30" -> "08h30min".

    Aceita: só a hora ("8", "08"), HH:MM ("08:30"), HHhMM/HHhMMmin
    ("8h30", "08h30min"), 4 dígitos do GDH ("0830"), e formas com texto
    ("8 horas"). Valor vazio volta vazio; valor irreconhecível volta como
    está (para não corromper um dado inesperado silenciosamente).
    """
    if valor is None:
        return valor
    s = str(valor).strip().lower()
    if not s:
        return s

    # Já em XXhXXmin ou HHhMM(min) - normaliza o zero à esquerda da hora.
    m = re.fullmatch(r"(\d{1,2})h(\d{2})(?:min)?", s)
    if m:
        return f"{int(m.group(1)):02d}h{m.group(2)}min"
    # HH:MM
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m:
        return f"{int(m.group(1)):02d}h{m.group(2)}min"
    # 4 dígitos contínuos (GDH): HHMM
    m = re.fullmatch(r"(\d{2})(\d{2})", s)
    if m:
        return f"{m.group(1)}h{m.group(2)}min"
    # Só a hora (com ou sem "horas"/"h" solto): usa minuto 00.
    m = re.match(r"(\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):02d}h00min"
    return str(valor).strip()


# ------------------------------------------------------------ validação de texto

# Cada regra: (padrão compilado, mensagem de aviso). O texto é analisado e,
# para cada regra que casar, é gerado um aviso (uma vez por regra por campo).
_REGRAS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(?<![0-9A-Za-zÀ-ÿ])[oa]s?\s+mesm[oa]s?\b", re.IGNORECASE),
        "evite 'o mesmo/a mesma' como pronome para substituir pessoa/substantivo "
        "(ex.: 'conduziu o mesmo' → 'conduziu-o'). Uso vedado na redação oficial.",
    ),
    (
        re.compile(r"\b(?:vou|vai|vamos|vão|irei|irá|iremos)\s+estar\s+\w+ndo\b", re.IGNORECASE),
        "evite gerundismo (ex.: 'vou estar enviando' → 'enviarei' / 'envio').",
    ),
    (
        re.compile(r"\b(?:estarei|estará|estaremos|estaria|estariam)\s+\w+ndo\b", re.IGNORECASE),
        "evite gerundismo (ex.: 'estarei enviando' → 'enviarei').",
    ),
    (
        re.compile(r"\b\d{1,2}:\d{2}\b"),
        "hora com dois-pontos é vedada; use o padrão '19h30min' (ou por extenso '19 horas').",
    ),
    (
        re.compile(r"\b\d{1,2}\s*hs\b", re.IGNORECASE),
        "'hs' é vedado; use '19h30min' ou por extenso '19 horas'.",
    ),
    (
        re.compile(r"\b\d{1,2}\s+h\b", re.IGNORECASE),
        "não separe a hora da abreviatura com espaço ('21 h' é incorreto); use '21h00min'.",
    ),
    (
        re.compile(r"\b\d{1,2}h(?![0-9]|oras|min)", re.IGNORECASE),
        "hora abreviada sem minutos é incorreta; use '19h00min' (ou por extenso '19 horas').",
    ),
    (
        re.compile(r"\b(?:ilustr[ií]ssimo|dign[ií]ssimo|mui\s+digno)\b", re.IGNORECASE),
        "'Ilustríssimo/Digníssimo/Mui Digno' foram abolidos; use 'Vossa Senhoria'.",
    ),
    (
        re.compile(r"\bsr[a]?\.", re.IGNORECASE),
        "não abrevie o pronome de tratamento no vocativo ('Sr.' → 'Senhor'; 'Sra.' → 'Senhora').",
    ),
    (
        # zero à esquerda em unidade (05), exceto datas formatadas: "05/03",
        # "05:30", "05h" e datas por extenso "08 de maio de 2013".
        re.compile(r"(?<![\d/:h.-])0[1-9]\b(?![\d/:h.]|\s+de\s)"),
        "não use zero à esquerda em unidades (ex.: '5' e não '05'), exceto em datas formatadas.",
    ),
]


def validar_texto(texto: str) -> list[str]:
    """Devolve avisos de redação oficial para um trecho de texto livre.

    São AVISOS, não erros - servem para o encarregado revisar antes de assinar.
    """
    if not texto or not texto.strip():
        return []
    avisos: list[str] = []
    for padrao, mensagem in _REGRAS:
        m = padrao.search(texto)
        if m:
            trecho = m.group(0).strip()
            avisos.append(f"“{trecho}”: {mensagem}")

    # Parágrafo inteiro em caixa alta (linguagem agressiva na redação oficial).
    corpo = texto.strip()
    if len(corpo) >= 40 and corpo == corpo.upper() and any(c.isalpha() for c in corpo):
        avisos.append("evite escrever o trecho inteiro em CAIXA ALTA - vedado na redação oficial.")

    return avisos
