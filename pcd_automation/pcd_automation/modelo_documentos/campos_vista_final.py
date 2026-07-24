"""Deriva as variáveis do template `termo_abertura_vista_final.docx`
(estágio RED - Razões Escritas de Defesa Final, ao final da instrução).
"""
from __future__ import annotations

from .campos_vista_comum import preparar_dados_vista


def preparar_dados_vista_final(dados: dict) -> tuple[dict, list[str]]:
    return preparar_dados_vista(
        dados,
        campo_data_evento="data_vista_final",
        campo_folhas_total="numero_folhas_autos_red",
        campo_folha_inicial="numero_folha_inicial_red",
        campo_folha_final="numero_folha_final_red",
        rotulo_estagio="RED",
    )
