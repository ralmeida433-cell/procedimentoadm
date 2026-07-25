from pathlib import Path

from pcd_automation.redacao import formatar_hora_br

from .campos_ata_cedmu import preparar_dados_ata_cedmu
from .campos_comunicacao import preparar_dados_comunicacao
from .campos_depoimento import preparar_dados_depoimento
from .campos_despacho import preparar_dados_despacho
from .campos_notificacao_sindicado import preparar_dados_notificacao_sindicado
from .campos_notificacao_testemunha import preparar_dados_notificacao_testemunha
from .campos_oficio import preparar_dados_oficio
from .campos_relatorio import preparar_dados_relatorio
from .campos_vista_final import preparar_dados_vista_final
from .campos_vista_inicial import preparar_dados_vista_inicial
from .preenchedor import preencher_docx

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_COMUNICACAO_DISCIPLINAR = _TEMPLATES_DIR / "comunicacao_disciplinar.docx"
TEMPLATE_DESPACHO_INSTAURACAO = _TEMPLATES_DIR / "despacho_instauracao.docx"
TEMPLATE_TERMO_VISTA_INICIAL = _TEMPLATES_DIR / "termo_abertura_vista_inicial.docx"
TEMPLATE_TERMO_VISTA_FINAL = _TEMPLATES_DIR / "termo_abertura_vista_final.docx"
TEMPLATE_NOTIFICACAO_TESTEMUNHA = _TEMPLATES_DIR / "notificacao_testemunha.docx"
TEMPLATE_NOTIFICACAO_SINDICADO_AUDICAO = _TEMPLATES_DIR / "notificacao_sindicado_audicao.docx"
TEMPLATE_TERMO_DEPOIMENTO = _TEMPLATES_DIR / "termo_depoimento_testemunha.docx"
TEMPLATE_RELATORIO_ENCARREGADO = _TEMPLATES_DIR / "relatorio_encarregado.docx"
TEMPLATE_OFICIO_REMESSA = _TEMPLATES_DIR / "oficio_remessa.docx"
TEMPLATE_ATA_CEDMU = _TEMPLATES_DIR / "ata_reuniao_cedmu.docx"


# Campos de hora que entram em texto corrido dos documentos - normalizados
# de forma centralizada para o padrão oficial da PMMG "XXhXXmin" (ex.: "8" ou
# "8:30" -> "08h00min"/"08h30min"), independentemente de como o usuário digitou.
# Os modelos já têm o campo de hora ISOLADO (sem sufixo " horas"/"h00min"), de
# modo que o valor formatado aqui é exatamente o que aparece no documento.
_CAMPOS_HORA = (
    "hora_fato", "hora_oitiva", "hora_inicio_depoimento", "hora_fim_depoimento",
    "hora_proxima_oitiva", "hora_inicio_reuniao", "hora_fim_reuniao",
)


def _normalizar_horas(dados: dict) -> dict:
    dados = dict(dados)
    for campo in _CAMPOS_HORA:
        if dados.get(campo):
            dados[campo] = formatar_hora_br(dados[campo])
    return dados


def _gerar(template: Path, preparar_dados, dados: dict, caminho_saida) -> list[str]:
    dados_template, pendentes_por_dado = preparar_dados(_normalizar_horas(dados))
    preencher_docx(template, dados_template, caminho_saida)
    return pendentes_por_dado


def gerar_comunicacao_disciplinar(dados: dict, caminho_saida) -> list[str]:
    """Gera a Comunicação Disciplinar preenchida (relato inicial que origina o PCD).

    Mesma semântica de retorno de `gerar_despacho_instauracao`.
    """
    return _gerar(TEMPLATE_COMUNICACAO_DISCIPLINAR, preparar_dados_comunicacao, dados, caminho_saida)


def gerar_despacho_instauracao(dados: dict, caminho_saida) -> list[str]:
    """Gera o Despacho de Instauração preenchido.

    Retorna a lista de campos que ficaram marcados como [PREENCHER: ...]
    por falta de dado na planilha - o encarregado deve completá-los no
    Word antes de assinar.
    """
    return _gerar(TEMPLATE_DESPACHO_INSTAURACAO, preparar_dados_despacho, dados, caminho_saida)


def gerar_termo_vista_inicial(dados: dict, caminho_saida) -> list[str]:
    """Gera o Termo de Abertura de Vista Inicial (defesa prévia) preenchido.

    Mesma semântica de retorno de `gerar_despacho_instauracao`.
    """
    return _gerar(TEMPLATE_TERMO_VISTA_INICIAL, preparar_dados_vista_inicial, dados, caminho_saida)


def gerar_termo_vista_final(dados: dict, caminho_saida) -> list[str]:
    """Gera o Termo de Abertura de Vista Final (RED) preenchido.

    Mesma semântica de retorno de `gerar_despacho_instauracao`.
    """
    return _gerar(TEMPLATE_TERMO_VISTA_FINAL, preparar_dados_vista_final, dados, caminho_saida)


def gerar_notificacao_testemunha(dados: dict, caminho_saida) -> list[str]:
    """Gera a Notificação de Comparecimento de Testemunha (convoca para a oitiva).

    Mesma semântica de retorno de `gerar_despacho_instauracao`.
    """
    return _gerar(TEMPLATE_NOTIFICACAO_TESTEMUNHA, preparar_dados_notificacao_testemunha, dados, caminho_saida)


def gerar_notificacao_sindicado_audicao(dados: dict, caminho_saida) -> list[str]:
    """Gera a Notificação do Sindicado/Defensor para conhecimento da audição de testemunhas.

    Mesma semântica de retorno de `gerar_despacho_instauracao`.
    """
    return _gerar(
        TEMPLATE_NOTIFICACAO_SINDICADO_AUDICAO, preparar_dados_notificacao_sindicado, dados, caminho_saida
    )


def gerar_termo_depoimento(dados: dict, caminho_saida) -> list[str]:
    """Gera o Termo de Depoimento da testemunha preenchido.

    Mesma semântica de retorno de `gerar_despacho_instauracao`. O teor do
    depoimento em si sempre fica marcado [PREENCHER] quando ausente.
    """
    return _gerar(TEMPLATE_TERMO_DEPOIMENTO, preparar_dados_depoimento, dados, caminho_saida)


def gerar_relatorio_encarregado(dados: dict, caminho_saida) -> list[str]:
    """Gera o Relatório do Encarregado preenchido.

    Mesma semântica de retorno de `gerar_despacho_instauracao`. As seções
    de análise/parecer (julgamento do encarregado) sempre ficam marcadas
    [PREENCHER] quando ausentes.
    """
    return _gerar(TEMPLATE_RELATORIO_ENCARREGADO, preparar_dados_relatorio, dados, caminho_saida)


def gerar_oficio_remessa(dados: dict, caminho_saida) -> list[str]:
    """Gera o Ofício de Remessa preenchido (remessa dos autos concluídos).

    Mesma semântica de retorno de `gerar_despacho_instauracao`.
    """
    return _gerar(TEMPLATE_OFICIO_REMESSA, preparar_dados_oficio, dados, caminho_saida)


def gerar_ata_cedmu(dados: dict, caminho_saida) -> list[str]:
    """Gera a Ata de Reunião do CEDMU preenchida (parecer do Conselho de Ética
    e Disciplina Militares da Unidade sobre um procedimento já concluído).

    Mesma semântica de retorno de `gerar_despacho_instauracao`. As seções de
    fundamentação e o parecer (julgamento do Conselho) sempre ficam marcadas
    [PREENCHER] quando ausentes - o sistema nunca fabrica esse conteúdo.
    """
    return _gerar(TEMPLATE_ATA_CEDMU, preparar_dados_ata_cedmu, dados, caminho_saida)


__all__ = [
    "gerar_ata_cedmu",
    "gerar_comunicacao_disciplinar",
    "gerar_despacho_instauracao",
    "gerar_termo_vista_inicial",
    "gerar_termo_vista_final",
    "gerar_notificacao_testemunha",
    "gerar_notificacao_sindicado_audicao",
    "gerar_termo_depoimento",
    "gerar_relatorio_encarregado",
    "gerar_oficio_remessa",
    "preparar_dados_comunicacao",
    "preparar_dados_despacho",
    "preparar_dados_vista_inicial",
    "preparar_dados_vista_final",
    "preparar_dados_notificacao_testemunha",
    "preparar_dados_notificacao_sindicado",
    "preparar_dados_depoimento",
    "preparar_dados_relatorio",
    "preparar_dados_oficio",
    "preparar_dados_ata_cedmu",
    "preencher_docx",
    "TEMPLATE_COMUNICACAO_DISCIPLINAR",
    "TEMPLATE_DESPACHO_INSTAURACAO",
    "TEMPLATE_TERMO_VISTA_INICIAL",
    "TEMPLATE_TERMO_VISTA_FINAL",
    "TEMPLATE_NOTIFICACAO_TESTEMUNHA",
    "TEMPLATE_NOTIFICACAO_SINDICADO_AUDICAO",
    "TEMPLATE_TERMO_DEPOIMENTO",
    "TEMPLATE_RELATORIO_ENCARREGADO",
    "TEMPLATE_OFICIO_REMESSA",
    "TEMPLATE_ATA_CEDMU",
]
