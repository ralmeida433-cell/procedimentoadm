"""Geração do documento oficial de Proposta de Recompensa (.docx).

Camada de serviço independente: recebe dados prontos (do formulário web, da
análise de REDS ou de qualquer outra origem) e produz o documento a partir do
template `modelo_documentos/templates/proposta_recompensa.docx`, que reproduz
fielmente o modelo oficial da PMMG (pasta `Modelo Processo-Procedimento/
PROPOSTA DE RECOMPENSA` - o .doc original nunca é alterado; ver
`modelo_documentos/gerar_template_recompensa.py`).

A IA fica totalmente fora daqui: quem chama decide de onde vêm os textos.
Esta camada só mapeia dados -> template e salva o arquivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from docxtpl import DocxTemplate

from pcd_automation.modelo_documentos.formatacao import MESES_PT

CAMINHO_TEMPLATE = Path(__file__).resolve().parent / "modelo_documentos" / "templates" / "proposta_recompensa.docx"

DIAS_SEMANA_PT = [
    "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
    "Sexta-feira", "Sábado", "Domingo",
]

# Os 8 requisitos do quadro "REQUISITOS PARA CONCESSÃO" do modelo oficial, na
# ordem das linhas da tabela (2-7 operacionais, 8-9 administrativos). As
# chaves são as usadas no JSON da análise de IA e nos checkboxes da tela.
REQUISITOS_RECOMPENSA: list[tuple[str, str]] = [
    ("acao_consciente", "Ação consciente e voluntária"),
    ("risco_vida", "Risco à vida ou à integridade física"),
    ("transcendencia", "Transcendência da ação em audácia e coragem com pleno sucesso"),
    ("inteligencia", "Inteligência e perspicácia no planejamento e na ação"),
    ("sem_conduta_negativa", "(*) Inexistência de conduta negativa ou ilícita"),
    ("repercussao_positiva", "(*) Repercussão positiva na comunidade (imprensa)"),
    ("inovacao_complexidade", "(*) Inovação/execução de atividade de extrema dificuldade"),
    ("atuacao_alem_unidade", "(*) Atuação destacada com reflexos além da Unidade"),
]


@dataclass
class MilitarProposta:
    numero: str
    posto: str
    nome: str
    unidade: str
    funcao: str
    individualizacao: str
    requisitos: dict = field(default_factory=dict)  # chave -> bool

    def para_contexto(self) -> dict:
        ctx = {
            "numero": self.numero or "[PREENCHER]",
            "posto_doc": f"{(self.posto or '[POSTO]').upper()} PM",
            "nome_upper": (self.nome or "[NOME]").upper(),
            "unidade": self.unidade or "[UNIDADE]",
            "funcao_upper": (self.funcao or "PATRULHEIRO").upper(),
            "individualizacao": self.individualizacao or "[PREENCHER: individualização da conduta]",
        }
        for n, (chave, _rotulo) in enumerate(REQUISITOS_RECOMPENSA, start=1):
            ctx[f"req{n}"] = "SIM" if self.requisitos.get(chave) else "NÃO"
        return ctx


def _data_extenso(d: date) -> str:
    # O modelo oficial escreve o mês com inicial maiúscula ("28 de Março de 2025").
    return f"{d.day} de {MESES_PT[d.month].capitalize()} de {d.year}"


def data_fato_linha(data_fato: date | None, texto_livre: str | None = None) -> str:
    """Linha do item '1. Data do Fato' no formato do modelo:
    'Dia 25 de Março de 2025 – Terça-feira.'"""
    if data_fato is None:
        return texto_livre or "[PREENCHER: data do fato]"
    return f"Dia {_data_extenso(data_fato)} – {DIAS_SEMANA_PT[data_fato.weekday()]}."


def montar_contexto(dados_doc: dict, militares: list[MilitarProposta]) -> dict:
    """Monta o contexto do template a partir dos dados do documento.

    `dados_doc` (todos texto, já revisados pelo usuário): linha_regiao,
    linha_unidade, cidade_sede, destinatario, tipo_recompensa,
    data_fato (date|None), local_fato_linha, descricao (parágrafos separados
    por linha em branco), proponente_assinatura, anexos (uma linha por item).
    """
    descricao = [p.strip() for p in (dados_doc.get("descricao") or "").split("\n\n") if p.strip()]
    if not descricao:
        descricao = [p.strip() for p in (dados_doc.get("descricao") or "").splitlines() if p.strip()]
    anexos = [l.strip() for l in (dados_doc.get("anexos") or "").splitlines() if l.strip()]
    return {
        "linha_regiao": (dados_doc.get("linha_regiao") or "[REGIÃO DE POLÍCIA MILITAR]").upper(),
        "linha_unidade": (dados_doc.get("linha_unidade") or "[UNIDADE]").upper(),
        "cidade_sede": dados_doc.get("cidade_sede") or "[CIDADE]",
        "data_documento_extenso": _data_extenso(dados_doc.get("data_documento") or date.today()),
        "destinatario": dados_doc.get("destinatario") or "[DESTINATÁRIO]",
        "anexo_descricao": dados_doc.get("anexo_descricao") or ("Reportagens e links" if anexos else "REDS da ocorrência"),
        "data_fato_linha": data_fato_linha(dados_doc.get("data_fato"), dados_doc.get("data_fato_texto")),
        "local_fato_linha": dados_doc.get("local_fato_linha") or "[PREENCHER: local do fato]",
        "descricao_paragrafos": descricao or ["[PREENCHER: descrição sucinta do ocorrido]"],
        "tipo_recompensa_upper": (dados_doc.get("tipo_recompensa") or "Elogio Individual").upper(),
        "proponente_assinatura": (dados_doc.get("proponente_assinatura") or "[NOME DO PROPONENTE, POSTO]").upper(),
        "anexos_linhas": anexos or ["REDS da ocorrência (anexar)"],
        "militares": [m.para_contexto() for m in militares],
    }


def gerar_documento_recompensa(contexto: dict, caminho_saida: Path) -> Path:
    """Renderiza o template oficial com o contexto e salva. A formatação do
    documento (fontes, tabelas, cabeçalho com brasão, margens) vem inteira do
    template - nada é montado em código."""
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    template = DocxTemplate(str(CAMINHO_TEMPLATE))
    template.render(contexto)
    template.save(str(caminho_saida))
    return caminho_saida
