"""Helpers de formatação de datas em português, compartilhados entre os
módulos de preparação de dados de cada documento."""
from __future__ import annotations

from datetime import date

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

# date.weekday(): 0=segunda ... 6=domingo
DIAS_SEMANA_PT = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira", 3: "quinta-feira",
    4: "sexta-feira", 5: "sábado", 6: "domingo",
}


def data_por_extenso(d: date) -> str:
    return f"{d.day:02d} de {MESES_PT[d.month]} de {d.year}"


def dia_semana_por_extenso(d: date) -> str:
    return DIAS_SEMANA_PT[d.weekday()]
