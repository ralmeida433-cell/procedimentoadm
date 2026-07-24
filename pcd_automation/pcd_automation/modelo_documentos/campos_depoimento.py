"""Deriva as variáveis do template `termo_depoimento_testemunha.docx`.

O teor do depoimento em si (o que a testemunha efetivamente respondeu) não
pode ser gerado pelo sistema - é sempre marcado [PREENCHER] quando ausente
e deve ser transcrito pelo encarregado durante a oitiva.
"""
from __future__ import annotations

from .formatacao import dia_semana_por_extenso


def preparar_dados_depoimento(dados: dict) -> tuple[dict, list[str]]:
    data_oitiva = dados["data_oitiva"]
    data_nascimento = dados.get("data_nascimento_testemunha")
    pendentes: list[str] = []

    def preencher_ou_marcar(campo: str, rotulo: str) -> str:
        valor = dados.get(campo)
        if valor:
            return str(valor)
        pendentes.append(rotulo)
        return f"[PREENCHER: {rotulo}]"

    variaveis = {
        "numero_ordem_testemunha": dados.get("numero_ordem_testemunha") or "1",
        "numero_batalhao_pm": preencher_ou_marcar("numero_batalhao_pm", "nº do Batalhão"),
        "numero_regiao_pm": preencher_ou_marcar("numero_regiao_pm", "nº da Região de Polícia Militar"),
        "cidade_sede": dados.get("cidade_sede") or dados.get("cidade_fato") or "[PREENCHER: cidade sede da unidade]",
        "data_oitiva_barra": f"{data_oitiva.day:02d}/{data_oitiva.month:02d}/{data_oitiva.year}",
        "dia_semana_oitiva": dia_semana_por_extenso(data_oitiva),
        "nome_autoridade_processante": dados["nome_autoridade_processante"],
        "posto_autoridade_processante": dados["posto_autoridade_processante"],
        "nome_testemunha_upper": preencher_ou_marcar("nome_testemunha", "nome da testemunha").upper(),
        "posto_testemunha": preencher_ou_marcar("posto_testemunha", "posto/graduação da testemunha"),
        "re_testemunha": preencher_ou_marcar("re_testemunha", "número de matrícula da testemunha"),
        "nome_pai_testemunha": preencher_ou_marcar("nome_pai_testemunha", "nome do pai da testemunha"),
        "nome_mae_testemunha": preencher_ou_marcar("nome_mae_testemunha", "nome da mãe da testemunha"),
        "idade_testemunha": preencher_ou_marcar("idade_testemunha", "idade da testemunha"),
        "sexo_testemunha": preencher_ou_marcar("sexo_testemunha", "sexo da testemunha"),
        "nacionalidade_testemunha": dados.get("nacionalidade_testemunha") or "Brasileira",
        "naturalidade_testemunha": preencher_ou_marcar("naturalidade_testemunha", "naturalidade da testemunha"),
        "estado_civil_testemunha": preencher_ou_marcar("estado_civil_testemunha", "estado civil da testemunha"),
        "cpf_testemunha": preencher_ou_marcar("cpf_testemunha", "CPF da testemunha"),
        "identidade_testemunha": preencher_ou_marcar("identidade_testemunha", "identidade da testemunha"),
        "local_trabalho_testemunha": preencher_ou_marcar(
            "local_trabalho_testemunha", "local de trabalho da testemunha"
        ),
        "telefone_celular_testemunha": preencher_ou_marcar(
            "telefone_celular_testemunha", "telefone celular da testemunha"
        ),
        "telefone_residencial_testemunha": dados.get("telefone_residencial_testemunha") or "Não possui",
        "telefone_comercial_testemunha": dados.get("telefone_comercial_testemunha") or "Não possui",
        "escolaridade_testemunha": preencher_ou_marcar("escolaridade_testemunha", "escolaridade da testemunha"),
        "numero_processo": preencher_ou_marcar("numero_processo", "número sequencial do processo"),
        "ano_processo": str(dados["data_instauracao"].year),
        "teor_depoimento": preencher_ou_marcar("teor_depoimento", "teor do depoimento prestado pela testemunha"),
        "hora_inicio_depoimento": preencher_ou_marcar("hora_inicio_depoimento", "hora de início do depoimento"),
        "hora_fim_depoimento": preencher_ou_marcar("hora_fim_depoimento", "hora de encerramento do depoimento"),
        "data_proxima_oitiva": dados.get("data_proxima_oitiva") or "a ser designado",
        "hora_proxima_oitiva": dados.get("hora_proxima_oitiva") or "a ser designado",
        "local_proxima_oitiva": dados.get("local_proxima_oitiva") or "a ser designado",
        "posto_graduacao_sindicado": dados["posto_graduacao_sindicado"],
        "nome_sindicado": dados["nome_sindicado"],
        "nome_defensor_sindicado": dados.get("nome_defensor_sindicado") or "Não constituído",
    }

    if data_nascimento:
        variaveis["data_nascimento_testemunha_barra"] = (
            f"{data_nascimento.day:02d}/{data_nascimento.month:02d}/{data_nascimento.year}"
        )
    else:
        pendentes.append("data de nascimento da testemunha")
        variaveis["data_nascimento_testemunha_barra"] = "[PREENCHER: data de nascimento da testemunha]"

    return variaveis, pendentes
