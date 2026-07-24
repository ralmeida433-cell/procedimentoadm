"""Deriva as variáveis do template `termo_abertura_vista_inicial.docx`
(estágio de defesa prévia, logo após a instauração).
"""
from __future__ import annotations

from .campos_vista_comum import preparar_dados_vista


def preparar_dados_vista_inicial(dados: dict) -> tuple[dict, list[str]]:
    return preparar_dados_vista(
        dados,
        campo_data_evento="data_citacao",
        campo_folhas_total="numero_folhas_autos_defesa_previa",
        campo_folha_inicial="numero_folha_inicial_defesa_previa",
        campo_folha_final="numero_folha_final_defesa_previa",
        rotulo_estagio="defesa prévia",
    )
