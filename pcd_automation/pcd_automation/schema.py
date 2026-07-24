"""Esquema canônico de dados de um PCD, compartilhado por todos os módulos.

As chaves abaixo são o contrato entre a planilha de controle (openpyxl),
o validador jurídico, o gerador de prazos e o preenchedor de documentos.
Se a planilha usar cabeçalhos diferentes, ajuste o mapeamento em
`gerador_portarias.planilha`, não os nomes aqui.
"""
from __future__ import annotations

OFICIAIS = {
    "Coronel", "Tenente-Coronel", "Major", "Capitão",
    "1º Tenente", "2º Tenente", "Aspirante a Oficial",
}

GRADUADOS_ELEGIVEIS = {"Subtenente", "1º Sargento", "2º Sargento", "3º Sargento"}

# Ordem hierárquica (do menos para o mais graduado) - mesma ordem usada nos
# dropdowns de posto/graduação (`webapp.campos_ui.OPCOES_POSTO`). Usada para
# comparar precedência hierárquica entre dois militares (ex.: encarregado
# deve ter precedência sobre o sindicado - art. 62, ICCPM/BM 01/2014,
# interpretativo do art. 38 do MAPPA; comunicante deve ter precedência sobre
# o comunicado - art. 35 do MAPPA).
ORDEM_POSTOS = [
    "Soldado", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento", "Subtenente",
    "Cadete", "Aspirante a Oficial", "2º Tenente", "1º Tenente", "Capitão", "Major",
    "Tenente-Coronel", "Coronel",
]
_INDICE_POSTO = {posto: indice for indice, posto in enumerate(ORDEM_POSTOS)}


def precedencia_posto(posto: str) -> int | None:
    """Índice de precedência hierárquica do posto/graduação (maior = mais
    graduado). None se o posto não for reconhecido - quem chama decide como
    tratar (normalmente: não valida, já que outro erro já vai acusar posto
    inválido)."""
    return _INDICE_POSTO.get(posto)

CAMPOS_OBRIGATORIOS_INSTAURACAO = [
    "nome_sindicado",
    "re_sindicado",
    "posto_graduacao_sindicado",
    "unidade_sindicado",
    "data_fato",
    "resumo_fato",
    "nome_autoridade_processante",
    "posto_autoridade_processante",
    "re_autoridade_processante",
    "nome_autoridade_delegante",
    "posto_autoridade_delegante",
    "data_instauracao",
    # quem comunicou a transgressão (Comunicação Disciplinar, anexa ao despacho)
    "nome_comunicante",
    "posto_comunicante",
    "re_comunicante",
    "unidade_comunicante",
    "data_comunicacao",
]

CAMPOS_OPCIONAIS = [
    # REDS (Registro de Evento de Defesa Social) nem sempre existe - muitos PCDs nascem de
    # observação/comunicação interna, sem despacho de uma central de emergência. Não é exigido
    # pelo MAPPA, por isso não trava a instauração (ver gerador_portarias.instaurar.gerar_processo_id,
    # que já usa "SEMREDS" como fallback quando ausente).
    "reds",
    "numero_processo",
    "estavel_autoridade_processante",
    "parentesco_ou_inimizade",
    "observacoes_impedimento",
    "prorrogado",
    "data_conclusao_real",
    "testemunhas_acusacao",
    "testemunhas_defesa",
    # campos específicos do Despacho de Instauração (modelo_documentos)
    "numero_regiao_pm",       # ex.: "5" -> "5ª Região de Polícia Militar"
    "numero_batalhao_pm",     # ex.: "34" -> "34º Batalhão de Polícia Militar"
    "unidade_autoridade_processante",  # ex.: "34º BPM" (forma abreviada, usada em texto corrido)
    "numero_comunicacao_disciplinar",
    "numero_folhas_comunicacao_disciplinar",  # fls. da Comunicação Disciplinar anexa ao despacho
    "cidade_fato",
    "hora_fato",
    "tipificacao_cedm",
    "cidade_sede",
    # campos específicos do Termo de Abertura de Vista Inicial (defesa prévia)
    # - cada estágio tem sua própria data de citação e sua própria contagem
    #   de folhas dos autos, que cresce conforme o processo avança - por
    #   isso não são compartilhados com os campos do Vista Final abaixo.
    "data_citacao",                        # data em que o sindicado foi citado para a defesa prévia
    "numero_folhas_autos_defesa_previa",
    "numero_folha_inicial_defesa_previa",
    "numero_folha_final_defesa_previa",
    "data_defesa_previa_apresentada",
    # campos específicos do Termo de Abertura de Vista Final (RED)
    "data_vista_final",                    # data de abertura da vista final (RED)
    "numero_folhas_autos_red",
    "numero_folha_inicial_red",
    "numero_folha_final_red",
    "data_red_apresentada",
    # Os modelos de Vista Inicial/Final têm blancos SEPARADOS para o
    # número do inciso e do artigo do CEDM (não um campo único de citação
    # como em outros documentos) - por isso não reaproveitam
    # tipificacao_cedm, que continua sendo o campo usado pelo Despacho e
    # pelo Relatório (cujos modelos aceitam a citação como texto único).
    "numero_inciso_cedm",
    "numero_artigo_cedm",
    # campos específicos da Comunicação Disciplinar
    "numero_folhas_escala_servico",
    "local_fato",
    "nome_testemunha",
    "posto_testemunha",
    "re_testemunha",
    "unidade_testemunha",
    "bens_documentos_relacionados",
    # campos específicos da oitiva (Notificação de Testemunha / Notificação do Sindicado)
    "data_oitiva",
    "hora_oitiva",
    "endereco_sede",
    "data_notificacao_testemunha",
    "data_notificacao_sindicado",
    # campos específicos do Termo de Depoimento (qualificação completa da testemunha)
    "numero_ordem_testemunha",
    "nome_pai_testemunha",
    "nome_mae_testemunha",
    "idade_testemunha",
    "data_nascimento_testemunha",
    "sexo_testemunha",
    "nacionalidade_testemunha",
    "naturalidade_testemunha",
    "estado_civil_testemunha",
    "cpf_testemunha",
    "identidade_testemunha",
    "local_trabalho_testemunha",
    "telefone_celular_testemunha",
    "telefone_residencial_testemunha",
    "telefone_comercial_testemunha",
    "escolaridade_testemunha",
    "teor_depoimento",
    "hora_inicio_depoimento",
    "hora_fim_depoimento",
    "nome_defensor_sindicado",
    "data_proxima_oitiva",
    "hora_proxima_oitiva",
    "local_proxima_oitiva",
    # campos específicos do Relatório do Encarregado
    # Seções 2 (fatos/provas), 3 (alegações de defesa) e o parecer (seção 6)
    # são análise e julgamento jurídico do encarregado e não são adivinhados
    # pelo sistema - ficam marcados [PREENCHER] quando ausentes.
    "data_hora_militar_fato",
    "em_servico_sindicado",
    "numero_folha_depoimento_testemunha",
    "objetos_apreendidos",
    "outras_provas",
    "analise_fatos_e_provas",
    "alegacoes_defesa_analise",
    "incidentes_processuais",
    "data_relatorio",
    # campos específicos do Ofício de Remessa
    "numero_oficio_remessa",
    "data_oficio_remessa",
    "numero_folhas_autos_final",
]

# Campos que, se ausentes, geram um marcador "[PREENCHER: ...]" no documento
# em vez de impedir a instauração - exigem redação/julgamento jurídico do
# encarregado e não devem ser adivinhados pelo sistema.
CAMPOS_REDACAO_MANUAL = ["tipificacao_cedm"]
