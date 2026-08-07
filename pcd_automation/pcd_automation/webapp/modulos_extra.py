"""Módulos adicionais de procedimentos: Recompensa, RIP, SAD e APF.

Arquivo separado de propósito: o módulo de PCD (app.py) está validado e não
deve ser alterado. Este blueprint só ADICIONA telas novas - nenhuma rota,
lógica de estado ou template do PCD é tocado. A integração com o app é feita
por duas linhas aditivas em criar_app() (registro do blueprint) e uma seção
nova no dashboard.html.

Escopo atual: formulários de ENTRADA de dados com persistência em JSON
(`processos/_modulos/<modulo>/<id>.json`). A Proposta de Recompensa também
GERA o documento oficial (.docx) a partir do modelo da PMMG - ver
`gerador_recompensa.py` e o fluxo de análise de REDS abaixo. RIP/SAD/APF
seguem só com registro de dados até haver modelo oficial de cada um.

Autofill inteligente e editável: não existe cadastro de usuário logado (o
login do app é uma senha única, sem perfis), então o auto-preenchimento usa
duas fontes: a data de hoje (campos marcados autofill="hoje") e o último
registro salvo do mesmo módulo (autofill="ultimo" - ex.: o proponente/
encarregado que você usou da última vez). Nenhum campo fica bloqueado:
tudo permanece editável, porque o processo é dinâmico.
"""
from __future__ import annotations

import json
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint, abort, current_app, redirect, render_template, request,
    send_from_directory, url_for,
)
from werkzeug.utils import secure_filename

from pcd_automation.extracao import EXTENSOES_SUPORTADAS, extrair_texto
from pcd_automation.gerador_recompensa import (
    REQUISITOS_RECOMPENSA, MilitarProposta, gerar_documento_recompensa, montar_contexto,
)
from pcd_automation.gerador_acidente_viatura import gerar_documentos as gerar_documentos_acidente
from pcd_automation.ia_cliente import RespostaIA, chamar_openrouter_detalhado
from pcd_automation.webapp.campos_ui import OPCOES_POSTO, normalizar_posto

bp_modulos = Blueprint("modulos", __name__, url_prefix="/modulos")


@bp_modulos.before_request
def _exigir_login_modulos():
    # Mesma regra de login do PCD (senha única opcional via PCD_SENHA).
    # Import tardio para não criar import circular com app.py.
    from pcd_automation.webapp.app import _exigir_login

    return _exigir_login()


# ---------------------------------------------------------------- definições
#
# Cada módulo é declarativo: seções -> campos. Tipos aceitos pelo template
# modulo_form.html: texto, texto_longo, data, hora, posto (select de
# posto/graduação), unidade (autocomplete PMMG), select (com "opcoes").
# autofill: "hoje" (data atual) | "ultimo" (copia do último registro salvo).

MODULOS: dict[str, dict] = {
    "recompensa": {
        "titulo": "Proposta de Recompensa",
        "descricao": "Indicação de militar para elogio, nota do mérito ou dispensa do serviço.",
        "campos_resumo": ["nome_proposto", "tipo_recompensa"],
        "secoes": [
            {"titulo": "Dados do Proponente (quem indica)", "campos": [
                {"chave": "posto_proponente", "rotulo": "Posto/Graduação do Proponente", "tipo": "posto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_proponente", "rotulo": "Número de Matrícula do Proponente", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "nome_proponente", "rotulo": "Nome do Proponente", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "unidade_proponente", "rotulo": "Unidade do Proponente", "tipo": "unidade", "obrigatorio": True, "autofill": "ultimo"},
            ]},
            {"titulo": "Dados do Proposto (quem recebe)", "campos": [
                {"chave": "posto_proposto", "rotulo": "Posto/Graduação do Proposto", "tipo": "posto", "obrigatorio": True},
                {"chave": "numero_proposto", "rotulo": "Número de Matrícula do Proposto", "tipo": "texto", "obrigatorio": True},
                {"chave": "nome_proposto", "rotulo": "Nome do Proposto", "tipo": "texto", "obrigatorio": True},
                {"chave": "unidade_proposto", "rotulo": "Unidade do Proposto", "tipo": "unidade", "obrigatorio": True},
            ]},
            {"titulo": "Dados da Recompensa", "campos": [
                {"chave": "reds_recompensa", "rotulo": "Nº do REDS relacionado", "tipo": "texto", "obrigatorio": False,
                 "tooltip": "REDS da ocorrência que motivou a proposta, se houver. Pode ser preenchido automaticamente pela análise de REDS com IA."},
                {"chave": "tipo_recompensa", "rotulo": "Tipo de Recompensa", "tipo": "select", "obrigatorio": True,
                 "opcoes": ["Elogio Individual", "Elogio Coletivo", "Nota do Mérito", "Dispensa do Serviço"]},
                {"chave": "sintese_justificativa", "rotulo": "Síntese do Fato / Justificativa", "tipo": "texto_longo", "obrigatorio": True,
                 "tooltip": "Descreva objetivamente o fato meritório que fundamenta a recompensa."},
                {"chave": "data_proposta", "rotulo": "Data da Proposta", "tipo": "data", "obrigatorio": True, "autofill": "hoje"},
            ]},
        ],
    },
    "rip": {
        "titulo": "RIP - Relatório de Investigação Preliminar",
        "descricao": "Apuração preliminar e sumária de fato, antes de eventual processo disciplinar.",
        "campos_resumo": ["resumo_fato_rip", "numero_portaria_rip"],
        "secoes": [
            {"titulo": "Dados da Portaria/Determinação", "campos": [
                {"chave": "numero_portaria_rip", "rotulo": "Número da Portaria/Determinação", "tipo": "texto", "obrigatorio": True},
                {"chave": "data_instauracao_rip", "rotulo": "Data de Instauração", "tipo": "data", "obrigatorio": True},
                {"chave": "nome_autoridade_delegante_rip", "rotulo": "Nome da Autoridade Delegante", "tipo": "texto", "obrigatorio": True},
                {"chave": "posto_autoridade_delegante_rip", "rotulo": "Posto da Autoridade Delegante", "tipo": "posto", "obrigatorio": True},
            ]},
            {"titulo": "Oficial/Praça Investigador", "campos": [
                {"chave": "posto_investigador", "rotulo": "Posto/Graduação do Investigador", "tipo": "posto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_investigador", "rotulo": "Número de Matrícula do Investigador", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "nome_investigador", "rotulo": "Nome do Investigador", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "unidade_investigador", "rotulo": "Unidade do Investigador", "tipo": "unidade", "obrigatorio": True, "autofill": "ultimo"},
            ]},
            {"titulo": "Fato Gerador", "campos": [
                {"chave": "resumo_fato_rip", "rotulo": "Resumo do Fato a Apurar", "tipo": "texto_longo", "obrigatorio": True,
                 "tooltip": "Fato a ser apurado preliminarmente - objetivo, sem juízo de valor."},
            ]},
            {"titulo": "Envolvidos Preliminares", "campos": [
                {"chave": "envolvidos_rip", "rotulo": "Envolvidos (nome e qualificação básica, um por linha)", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Militares ou civis possivelmente envolvidos. Ex.: Sd PM Fulano de Tal, nº 123.456-7, 10º BPM."},
            ]},
        ],
    },
    "sad": {
        "titulo": "SAD - Sindicância Administrativa Disciplinar",
        "descricao": "Sindicância do Capítulo VIII do MAPPA (portaria, sindicado e objeto).",
        "campos_resumo": ["nome_sindicado_sad", "numero_portaria_sad"],
        "secoes": [
            {"titulo": "Dados da Portaria", "campos": [
                {"chave": "numero_portaria_sad", "rotulo": "Número da Portaria", "tipo": "texto", "obrigatorio": True},
                {"chave": "data_portaria_sad", "rotulo": "Data da Portaria", "tipo": "data", "obrigatorio": True},
                {"chave": "nome_autoridade_instauradora_sad", "rotulo": "Nome da Autoridade Instauradora", "tipo": "texto", "obrigatorio": True},
                {"chave": "posto_autoridade_instauradora_sad", "rotulo": "Posto da Autoridade Instauradora", "tipo": "posto", "obrigatorio": True},
            ]},
            {"titulo": "Dados do Encarregado (sindicante)", "campos": [
                {"chave": "posto_encarregado_sad", "rotulo": "Posto/Graduação do Encarregado", "tipo": "posto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_encarregado_sad", "rotulo": "Número de Matrícula do Encarregado", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "nome_encarregado_sad", "rotulo": "Nome do Encarregado", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "unidade_encarregado_sad", "rotulo": "Unidade do Encarregado", "tipo": "unidade", "obrigatorio": True, "autofill": "ultimo"},
            ]},
            {"titulo": "Dados do Sindicado", "campos": [
                {"chave": "posto_sindicado_sad", "rotulo": "Posto/Graduação do Sindicado", "tipo": "posto", "obrigatorio": True},
                {"chave": "numero_sindicado_sad", "rotulo": "Número de Matrícula do Sindicado", "tipo": "texto", "obrigatorio": True},
                {"chave": "nome_sindicado_sad", "rotulo": "Nome do Sindicado", "tipo": "texto", "obrigatorio": True},
                {"chave": "unidade_sindicado_sad", "rotulo": "Unidade do Sindicado", "tipo": "unidade", "obrigatorio": True},
            ]},
            {"titulo": "Objeto da Sindicância", "campos": [
                {"chave": "descricao_transgressao_sad", "rotulo": "Transgressão Disciplinar em Tese (descrição)", "tipo": "texto_longo", "obrigatorio": True},
                {"chave": "referencia_cedm_sad", "rotulo": "Referência ao CEDM (artigo/inciso)", "tipo": "texto", "obrigatorio": False,
                 "tooltip": "Ex.: art. 13, inciso XX, do CEDM (Lei 14.310/2002). Arts. 13/14/15 = natureza grave/média/leve."},
            ]},
        ],
    },
    "apf": {
        "titulo": "APF - Auto de Prisão em Flagrante",
        "descricao": "Registro dos dados do flagrante: partes, dinâmica e materiais apreendidos.",
        "campos_resumo": ["nome_conduzido_apf", "data_fato_apf"],
        "secoes": [
            {"titulo": "Dados Básicos", "campos": [
                {"chave": "data_fato_apf", "rotulo": "Data do Fato", "tipo": "data", "obrigatorio": True},
                {"chave": "hora_fato_apf", "rotulo": "Hora do Fato", "tipo": "hora", "obrigatorio": True},
                {"chave": "local_fato_apf", "rotulo": "Local do Fato", "tipo": "texto", "obrigatorio": True},
            ]},
            {"titulo": "Qualificação das Partes", "campos": [
                {"chave": "nome_condutor_apf", "rotulo": "Nome do Condutor", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "posto_condutor_apf", "rotulo": "Posto/Graduação do Condutor", "tipo": "posto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_condutor_apf", "rotulo": "Número de Matrícula do Condutor", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "testemunhas_apf", "rotulo": "Testemunhas (nome e qualificação, uma por linha)", "tipo": "texto_longo", "obrigatorio": False},
                {"chave": "nome_conduzido_apf", "rotulo": "Nome do Conduzido/Flagranteado", "tipo": "texto", "obrigatorio": True},
                {"chave": "qualificacao_conduzido_apf", "rotulo": "Qualificação do Conduzido (documentos, filiação, endereço)", "tipo": "texto_longo", "obrigatorio": False},
            ]},
            {"titulo": "Dinâmica do Fato", "campos": [
                {"chave": "dinamica_fato_apf", "rotulo": "Relato da Prisão (dinâmica do fato)", "tipo": "texto_longo", "obrigatorio": True},
            ]},
            {"titulo": "Materiais Apreendidos", "campos": [
                {"chave": "materiais_apreendidos_apf", "rotulo": "Materiais Apreendidos (um por linha)", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Armas, equipamentos ou objetos vinculados ao flagrante, com identificação (nº de série etc.)."},
            ]},
        ],
    },
    # Sindicância de acidente com viatura - arts. 321 a 324 do MAPPA (Cap. IX).
    # Gera as 7 peças (ver gerador_acidente_viatura).
    "acidente_viatura": {
        "titulo": "Acidente com Viatura",
        "descricao": "Sindicância para apuração de acidente com viatura (arts. 321-324 do MAPPA). "
                     "Gera as 7 peças do procedimento, da portaria à solução.",
        "campos_resumo": ["numero_portaria", "descricao_viatura"],
        "gera_documentos": True,
        "secoes": [
            {"titulo": "Portaria e Unidade", "campos": [
                {"chave": "unidade", "rotulo": "Unidade/UDI", "tipo": "unidade", "obrigatorio": True, "autofill": "ultimo",
                 "tooltip": "Unidade ou Unidade de Direção Intermediária onde corre a sindicância (ex.: 1ª Cia Ind / 3º BPM)."},
                {"chave": "cidade_sede", "rotulo": "Cidade do quartel", "tipo": "cidade", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_portaria", "rotulo": "Número da Portaria", "tipo": "texto", "obrigatorio": True,
                 "tooltip": "Ex.: 101.3/2026."},
                {"chave": "data_portaria", "rotulo": "Data da Portaria", "tipo": "data", "obrigatorio": True, "autofill": "hoje"},
                {"chave": "data_recibo_portaria", "rotulo": "Data do recibo da portaria pelo sindicante", "tipo": "data", "obrigatorio": False,
                 "tooltip": "Marco inicial do prazo de 30 dias corridos (arts. 273/274 do MAPPA). Deixe em branco se ainda não houve recibo."},
                {"chave": "prorrogado", "rotulo": "Prazo prorrogado por 10 dias?", "tipo": "select", "obrigatorio": False,
                 "opcoes": ["Não", "Sim"]},
            ]},
            {"titulo": "Autoridade Delegante", "campos": [
                {"chave": "nome_delegante", "rotulo": "Nome da Autoridade Delegante", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "posto_delegante", "rotulo": "Posto/Graduação da Autoridade Delegante", "tipo": "posto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_delegante", "rotulo": "Número de Matrícula da Autoridade Delegante", "tipo": "texto", "obrigatorio": False, "autofill": "ultimo"},
                {"chave": "cargo_delegante", "rotulo": "Cargo da Autoridade Delegante", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo",
                 "tooltip": "Ex.: Comandante da 1ª Cia Ind PM. Entra na abertura da portaria e na assinatura da solução."},
            ]},
            {"titulo": "Sindicante (encarregado)", "campos": [
                {"chave": "nome_sindicante", "rotulo": "Nome do Sindicante", "tipo": "texto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "posto_sindicante", "rotulo": "Posto/Graduação do Sindicante", "tipo": "posto", "obrigatorio": True, "autofill": "ultimo"},
                {"chave": "numero_sindicante", "rotulo": "Número de Matrícula do Sindicante", "tipo": "texto", "obrigatorio": False, "autofill": "ultimo"},
            ]},
            {"titulo": "Envolvido / Responsável pela viatura", "campos": [
                {"chave": "nome_envolvido", "rotulo": "Nome do Envolvido/Responsável", "tipo": "texto", "obrigatorio": True},
                {"chave": "posto_envolvido", "rotulo": "Posto/Graduação do Envolvido", "tipo": "posto", "obrigatorio": False},
                {"chave": "numero_envolvido", "rotulo": "Número de Matrícula do Envolvido", "tipo": "texto", "obrigatorio": False},
                {"chave": "sem_carater_disciplinar", "rotulo": "Sindicância SEM caráter disciplinar?", "tipo": "select", "obrigatorio": False,
                 "opcoes": ["Não", "Sim"],
                 "tooltip": "Marque Sim quando a apuração for exclusivamente do dano (ex.: culpa exclusiva de terceiro civil). "
                            "Nesse caso o art. 324, §2º, do MAPPA dispensa a notificação para defesa prévia, e essa peça não é gerada."},
                {"chave": "houve_vitima", "rotulo": "Houve vítima?", "tipo": "select", "obrigatorio": True,
                 "opcoes": ["Não houve vítima", "Vítima civil", "Vítima militar (passageiro ou pedestre)",
                            "Vítima militar condutor da viatura"],
                 "tooltip": "Define se, além desta sindicância, é obrigatório instaurar IPM (art. 322, I a IV, do MAPPA). O sistema avisa após gerar."},
            ]},
            {"titulo": "Viatura e Dano", "campos": [
                {"chave": "descricao_viatura", "rotulo": "Descrição da Viatura/Material", "tipo": "texto", "obrigatorio": True,
                 "tooltip": "Ex.: VTR 12345, Chevrolet Spin, placa ABC-1D23, patrimônio nº 000000."},
                {"chave": "valor_prejuizo", "rotulo": "Valor do Prejuízo/Avaria", "tipo": "texto", "obrigatorio": False,
                 "tooltip": "Se já houver avaliação prévia. Ex.: R$ 1.200,00."},
                {"chave": "data_fato", "rotulo": "Data do Fato", "tipo": "data", "obrigatorio": True},
                {"chave": "hora_fato", "rotulo": "Hora do Fato", "tipo": "hora", "obrigatorio": False},
                {"chave": "local_fato", "rotulo": "Local do Fato", "tipo": "texto", "obrigatorio": True},
                {"chave": "historico_fato", "rotulo": "Histórico Sucinto do Fato", "tipo": "texto_longo", "obrigatorio": True,
                 "tooltip": "Descreva cronologicamente o que ocorreu, de forma objetiva e impessoal."},
            ]},
            {"titulo": "Instrução (termo de abertura e depoimento)", "campos": [
                {"chave": "data_abertura", "rotulo": "Data do Termo de Abertura", "tipo": "data", "obrigatorio": False},
                {"chave": "documentos_juntados", "rotulo": "Documentos juntados na abertura", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Ex.: cópia do REDS, ficha da viatura, laudo de avaria, escala de serviço."},
                {"chave": "numero_folhas_autos", "rotulo": "Nº de folhas dos autos (notificação)", "tipo": "texto", "obrigatorio": False},
                {"chave": "data_notificacao", "rotulo": "Data da Notificação do sindicado", "tipo": "data", "obrigatorio": False},
                {"chave": "nome_depoente", "rotulo": "Nome do Depoente", "tipo": "texto", "obrigatorio": False},
                {"chave": "posto_depoente", "rotulo": "Posto/Graduação do Depoente", "tipo": "posto", "obrigatorio": False},
                {"chave": "numero_depoente", "rotulo": "Número de Matrícula do Depoente", "tipo": "texto", "obrigatorio": False},
                {"chave": "data_depoimento", "rotulo": "Data do Depoimento", "tipo": "data", "obrigatorio": False},
                {"chave": "hora_depoimento", "rotulo": "Hora do Depoimento", "tipo": "hora", "obrigatorio": False},
                {"chave": "teor_circunstancias", "rotulo": "Depoimento — circunstâncias do fato", "tipo": "texto_longo", "obrigatorio": False},
                {"chave": "teor_cautela", "rotulo": "Depoimento — cautela e estado de conservação da viatura", "tipo": "texto_longo", "obrigatorio": False},
                {"chave": "teor_nexo", "rotulo": "Depoimento — nexo de causalidade", "tipo": "texto_longo", "obrigatorio": False},
            ]},
            {"titulo": "Relatório Final", "campos": [
                {"chave": "diligencias", "rotulo": "Diligências realizadas (seção 2)", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Juntada de termos, laudos, notas fiscais, perícias."},
                {"chave": "analise_merito", "rotulo": "Análise do mérito (seção 3)", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Culpa, dolo, caso fortuito, força maior ou desgaste natural do material. É juízo do sindicante — o sistema não redige por você."},
                {"chave": "conclusao_parecer", "rotulo": "Conclusão e parecer (seção 4)", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Há ou não responsabilidade pecuniária/disciplinar e necessidade de ressarcimento ao erário."},
                {"chave": "data_relatorio", "rotulo": "Data do Relatório", "tipo": "data", "obrigatorio": False},
            ]},
            {"titulo": "Encerramento e Solução", "campos": [
                {"chave": "data_encerramento", "rotulo": "Data do Termo de Encerramento", "tipo": "data", "obrigatorio": False},
                {"chave": "numero_folhas_autos_final", "rotulo": "Nº total de folhas dos autos", "tipo": "texto", "obrigatorio": False},
                {"chave": "texto_solucao", "rotulo": "Decisão da autoridade delegante", "tipo": "texto_longo", "obrigatorio": False,
                 "tooltip": "Homologar, reformar ou determinar novas diligências, com fundamentação. Ato privativo da autoridade."},
                {"chave": "encaminhamentos", "rotulo": "Encaminhamentos administrativos/financeiros", "tipo": "texto_longo", "obrigatorio": False},
                {"chave": "data_solucao", "rotulo": "Data da Solução", "tipo": "data", "obrigatorio": False},
            ]},
        ],
    },
}


def _campos_do_modulo(definicao: dict) -> list[dict]:
    return [campo for secao in definicao["secoes"] for campo in secao["campos"]]


# ---------------------------------------------------------------- persistência

def _diretorio_modulo(modulo_id: str) -> Path:
    return Path(current_app.config["DIRETORIO_BASE"]) / "_modulos" / modulo_id


def _caminho_registro(modulo_id: str, registro_id: str) -> Path:
    return _diretorio_modulo(modulo_id) / f"{registro_id}.json"


def _salvar_registro(modulo_id: str, registro_id: str, dados: dict, criado_em: str | None = None) -> None:
    caminho = _caminho_registro(modulo_id, registro_id)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    agora = datetime.now().isoformat(timespec="seconds")
    payload = {"criado_em": criado_em or agora, "atualizado_em": agora, "dados": dados}
    caminho.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _carregar_registro(modulo_id: str, registro_id: str) -> dict | None:
    caminho = _caminho_registro(modulo_id, registro_id)
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def _listar_registros(modulo_id: str) -> list[dict]:
    pasta = _diretorio_modulo(modulo_id)
    if not pasta.exists():
        return []
    registros = []
    for caminho in pasta.glob("*.json"):
        try:
            payload = json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        payload["id"] = caminho.stem
        registros.append(payload)
    registros.sort(key=lambda r: r.get("criado_em") or "", reverse=True)
    return registros


# ---------------------------------------------------------------- form helpers

def _definicao_ou_404(modulo_id: str) -> dict:
    definicao = MODULOS.get(modulo_id)
    if definicao is None:
        abort(404)
    return definicao


def _valores_do_form(definicao: dict, form) -> dict:
    return {c["chave"]: (form.get(c["chave"]) or "").strip() for c in _campos_do_modulo(definicao)}


def _obrigatorios_faltando(definicao: dict, valores: dict) -> list[str]:
    return [c["rotulo"] for c in _campos_do_modulo(definicao) if c.get("obrigatorio") and not valores.get(c["chave"])]


def _valores_autofill(modulo_id: str, definicao: dict) -> tuple[dict, list[str]]:
    """Pré-preenche um formulário novo: data de hoje (autofill="hoje") e os
    dados do último registro salvo deste módulo (autofill="ultimo"). Tudo
    permanece editável - isto só poupa digitação, não trava nada."""
    valores: dict = {}
    prefilled: list[str] = []
    registros = _listar_registros(modulo_id)
    ultimo = registros[0]["dados"] if registros else {}
    for campo in _campos_do_modulo(definicao):
        origem = campo.get("autofill")
        if origem == "hoje":
            valores[campo["chave"]] = date.today().isoformat()
            prefilled.append(campo["rotulo"])
        elif origem == "ultimo" and ultimo.get(campo["chave"]):
            valores[campo["chave"]] = ultimo[campo["chave"]]
            prefilled.append(campo["rotulo"])
    return valores, prefilled


def _resumo_registro(definicao: dict, dados: dict) -> str:
    partes = [dados.get(chave) for chave in definicao["campos_resumo"] if dados.get(chave)]
    return " — ".join(str(p) for p in partes) or "(sem dados)"


# ---------------------------------------------------------------- rotas

@bp_modulos.route("/<modulo_id>")
def lista(modulo_id):
    definicao = _definicao_ou_404(modulo_id)
    registros = [
        {"id": r["id"], "resumo": _resumo_registro(definicao, r.get("dados") or {}), "criado_em": r.get("criado_em")}
        for r in _listar_registros(modulo_id)
    ]
    documentos = listar_documentos_recompensa() if modulo_id == "recompensa" else []
    return render_template(
        "modulo_lista.html", modulo_id=modulo_id, definicao=definicao,
        registros=registros, documentos=documentos,
    )


@bp_modulos.route("/<modulo_id>/novo", methods=["GET", "POST"])
def novo(modulo_id):
    definicao = _definicao_ou_404(modulo_id)

    if request.method == "POST":
        valores = _valores_do_form(definicao, request.form)
        faltando = _obrigatorios_faltando(definicao, valores)
        if faltando:
            return render_template(
                "modulo_form.html", modulo_id=modulo_id, definicao=definicao, valores=valores,
                prefilled=[], erros=[f"Campo obrigatório: {r}" for r in faltando],
                action=url_for(".novo", modulo_id=modulo_id), opcoes_posto=OPCOES_POSTO,
            )
        _salvar_registro(modulo_id, uuid4().hex[:8], valores)
        return redirect(url_for(".lista", modulo_id=modulo_id))

    valores, prefilled = _valores_autofill(modulo_id, definicao)
    return render_template(
        "modulo_form.html", modulo_id=modulo_id, definicao=definicao, valores=valores,
        prefilled=prefilled, erros=[], action=url_for(".novo", modulo_id=modulo_id),
        opcoes_posto=OPCOES_POSTO,
    )


@bp_modulos.route("/<modulo_id>/<registro_id>", methods=["GET", "POST"])
def editar(modulo_id, registro_id):
    definicao = _definicao_ou_404(modulo_id)
    payload = _carregar_registro(modulo_id, registro_id)
    if payload is None:
        abort(404)

    if request.method == "POST":
        valores = _valores_do_form(definicao, request.form)
        faltando = _obrigatorios_faltando(definicao, valores)
        if faltando:
            return render_template(
                "modulo_form.html", modulo_id=modulo_id, definicao=definicao, valores=valores,
                prefilled=[], erros=[f"Campo obrigatório: {r}" for r in faltando],
                action=url_for(".editar", modulo_id=modulo_id, registro_id=registro_id),
                opcoes_posto=OPCOES_POSTO,
            )
        _salvar_registro(modulo_id, registro_id, valores, criado_em=payload.get("criado_em"))
        return redirect(url_for(".lista", modulo_id=modulo_id))

    return render_template(
        "modulo_form.html", modulo_id=modulo_id, definicao=definicao, valores=payload.get("dados") or {},
        prefilled=[], erros=[], action=url_for(".editar", modulo_id=modulo_id, registro_id=registro_id),
        opcoes_posto=OPCOES_POSTO,
    )


@bp_modulos.route("/<modulo_id>/<registro_id>/excluir", methods=["GET", "POST"])
def excluir(modulo_id, registro_id):
    definicao = _definicao_ou_404(modulo_id)
    payload = _carregar_registro(modulo_id, registro_id)
    if payload is None:
        abort(404)

    if request.method == "POST":
        _caminho_registro(modulo_id, registro_id).unlink(missing_ok=True)
        return redirect(url_for(".lista", modulo_id=modulo_id))

    return render_template(
        "confirmar_exclusao.html",
        titulo=f"Excluir registro - {definicao['titulo']}",
        rotulo_alvo=_resumo_registro(definicao, payload.get("dados") or {}),
        descricao="Este registro ainda não gerou documento oficial - apenas os dados digitados serão perdidos.",
        documentos=[],
        action=url_for(".excluir", modulo_id=modulo_id, registro_id=registro_id),
        voltar=url_for(".lista", modulo_id=modulo_id),
    )


# ------------------------------------------- análise de REDS -> propostas (IA)
#
# O encarregado carrega o PDF do REDS; a IA extrai os dados da ocorrência e
# INDIVIDUALIZA a conduta de cada militar empenhado (um REDS quase sempre tem
# mais de um militar, e a recompensa exige dizer o que CADA UM fez). O sistema
# então cria uma proposta pré-preenchida por militar selecionado. Mesmo
# princípio do resto do sistema: a IA não inventa dado que não esteja no
# texto, e tudo o que ela redigir passa pela revisão do usuário na tela antes
# de virar registro.

PROMPT_REDS = """Você analisa um REDS (Registro de Eventos de Defesa Social) da PMMG para subsidiar \
PROPOSTAS DE RECOMPENSA aos policiais militares que atuaram na ocorrência.

TAREFA 1 - Extraia os dados da ocorrência: número do REDS, data do fato (formato ISO aaaa-mm-dd), \
hora, município, local e um resumo objetivo do que aconteceu. NUNCA invente um dado que não esteja \
no texto - se não encontrar, OMITA o campo do JSON.

TAREFA 2 - Identifique CADA policial militar que atuou na ocorrência (normalmente no histórico e no \
campo de militares empenhados/responsáveis), com posto/graduação, nome completo, número de matrícula \
e unidade, quando constarem do texto. NÃO OMITA NENHUM militar empenhado - numa proposta de \
recompensa, militar esquecido é militar sem elogio; confira a lista completa antes de responder. Não \
inclua vítimas, autores, testemunhas civis nem militares apenas citados sem atuação.

TAREFA 3 - INDIVIDUALIZE a conduta: para cada militar, descreva em "conduta_individual" o que ELE \
especificamente fez segundo o histórico (quem abordou, quem conteve o agressor, quem prestou os \
primeiros socorros, quem negociou, quem localizou o material...). Se o histórico não distinguir as \
ações entre os militares, diga expressamente que a atuação foi conjunta - não distribua ações \
inventadas.

TAREFA 4 - Para cada militar, redija "sintese_proposta": um parágrafo em redação oficial impessoal \
da PMMG, pronto para fundamentar a proposta de recompensa, combinando o fato e a conduta individual \
daquele militar. Restrições: sem juízo de valor exagerado, sem inventar circunstância que não esteja \
no texto; horas no formato XXhXXmin (nunca "19:30" nem "19hs"); não use "o mesmo/a mesma" como \
pronome; sem gerundismo.

TAREFA 5 - Identifique a FUNÇÃO de cada militar na ocorrência, escolhendo a mais específica que o \
texto sustentar: "Comandante da operação", "Comandante de guarnição", "Motorista", "Patrulheiro", \
"P2", "ROCCA", "CPU", "ROTAM", "POP", ou outra função que o REDS evidencie. Se não houver como saber, \
use "Patrulheiro".

TAREFA 6 - Avalie, para cada militar, os requisitos de concessão de recompensa do modelo oficial da \
PMMG, devolvendo true/false em "requisitos" com ESTAS chaves exatas:
- "acao_consciente": ação consciente e voluntária;
- "risco_vida": risco à vida ou à integridade física;
- "transcendencia": transcendência da ação em audácia e coragem com obtenção de pleno sucesso;
- "inteligencia": inteligência e perspicácia no planejamento e na ação;
- "sem_conduta_negativa": inexistência de conduta negativa ou ilícita NA OCORRÊNCIA (a ficha \
disciplinar não está no REDS - avalie só o que o texto mostra);
- "repercussao_positiva": repercussão positiva na comunidade/imprensa - só true se o texto mencionar \
divulgação ou repercussão;
- "inovacao_complexidade": inovação ou execução de atividade de extremo grau de dificuldade;
- "atuacao_alem_unidade": atuação destacada com efeitos além da Unidade.
Marque true SOMENTE com base no que o REDS sustenta para AQUELE militar - requisito sem evidência é false.

TAREFA 7 - Redija em "descricao_administrativa" a seção "Descrição sucinta do ocorrido" do documento \
oficial: uma lista de 3 a 6 parágrafos em narrativa ADMINISTRATIVA de alto nível (não é cópia do \
histórico do REDS nem linguagem policial de boletim). Organize cronologicamente: contexto e \
planejamento; desenvolvimento da ação; resultado operacional (prisões e apreensões, com quantidades \
exatas do REDS); impacto para a comunidade e repercussão institucional. Impessoal, sem exageros, sem \
inventar fato, horas no formato XXhXXmin.

Liste em "observacoes" qualquer ressalva (trechos ilegíveis, militar sem matrícula no texto, dúvida \
sobre quem fez o quê).

Responda SOMENTE com um objeto JSON válido, sem markdown, exatamente neste formato:
{"reds": "...", "data_fato": "aaaa-mm-dd", "hora_fato": "...", "municipio": "...", "local_fato": "...", \
"natureza": "...", "resumo_ocorrencia": "...", "descricao_administrativa": ["...", "..."], \
"militares": [{"posto": "...", "nome": "...", "numero": "...", "unidade": "...", "funcao": "...", \
"conduta_individual": "...", "sintese_proposta": "...", "requisitos": {"acao_consciente": true, \
"risco_vida": false, "transcendencia": false, "inteligencia": false, "sem_conduta_negativa": true, \
"repercussao_positiva": false, "inovacao_complexidade": false, "atuacao_alem_unidade": false}}], \
"observacoes": ["..."]}
"""


def _extrair_json_ia(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip(), flags=re.IGNORECASE)
    return json.loads(texto)


# Matrícula de militar no padrão da PMMG ("130.555-1"). Usada como contagem
# independente de quantos militares o REDS menciona - é o cross-check
# determinístico contra a IA omitir alguém da lista.
_RE_MATRICULA = re.compile(r"\b\d{3}\.\d{3}-\d\b")


def _chamar_analise_reds(texto: str) -> tuple[dict | None, str | None, RespostaIA]:
    resposta = chamar_openrouter_detalhado(
        [
            {"role": "system", "content": PROMPT_REDS},
            {"role": "user", "content": f"Texto extraído do REDS:\n\n{texto[:150000]}"},
        ],
        # Um REDS de operação grande pode ter 15+ militares, cada um com
        # individualização + requisitos - a resposta é longa.
        max_tokens=16000,
        timeout=240,
        json_obrigatorio=True,
    )
    if resposta.erro:
        return None, resposta.erro, resposta
    try:
        return _extrair_json_ia(resposta.conteudo), None, resposta
    except json.JSONDecodeError:
        return None, f"A IA não retornou um JSON válido. Resposta bruta: {resposta.conteudo[:400]}", resposta


def analisar_reds_texto(texto: str) -> tuple[dict | None, str | None]:
    """Analisa o texto extraído de um REDS. Retorna (resultado, erro) -
    exatamente um dos dois é None.

    Trava anti-omissão: o modelo gratuito às vezes deixa um militar de fora
    da lista. Como cada militar empenhado aparece no REDS com a matrícula no
    padrão NNN.NNN-N, contamos as matrículas distintas do texto; se a IA
    devolver menos militares que isso, a análise é refeita uma vez (fica com
    a resposta mais completa) e, persistindo a diferença, o usuário é
    avisado nas observações - numa proposta de recompensa, militar esquecido
    é militar sem elogio."""
    if not texto.strip():
        return None, (
            "Não foi possível extrair nenhum texto do arquivo (pode estar em branco, corrompido ou "
            "o OCR não reconheceu nada)."
        )

    esperado = len(set(_RE_MATRICULA.findall(texto)))
    dados, erro, resposta = _chamar_analise_reds(texto)
    if erro:
        return None, erro

    if resposta.usou_reserva:
        dados.setdefault("observacoes", []).append(
            f"O modelo principal estava indisponível (capacidade do tier gratuito); a análise foi "
            f"feita pelo modelo reserva {resposta.modelo_usado}, que é menor. Revise os textos com "
            "atenção redobrada ou refaça a análise mais tarde."
        )

    if esperado and len(dados.get("militares") or []) < esperado:
        segunda, erro2, _ = _chamar_analise_reds(texto)
        if erro2 is None and len(segunda.get("militares") or []) > len(dados.get("militares") or []):
            dados = segunda
        if len(dados.get("militares") or []) < esperado:
            dados.setdefault("observacoes", []).append(
                f"O texto do REDS menciona {esperado} matrículas de militares, mas a análise "
                f"individualizou {len(dados.get('militares') or [])}. Confira se algum militar "
                "empenhado ficou de fora e acrescente-o manualmente."
            )

    # Normaliza o posto de cada militar para o valor canônico dos <select>.
    for militar in dados.get("militares") or []:
        if isinstance(militar, dict) and militar.get("posto"):
            militar["posto"] = normalizar_posto(str(militar["posto"]))
    return dados, None


@bp_modulos.route("/recompensa/reds", methods=["GET", "POST"])
def reds_recompensa():
    """Upload do REDS (PDF/DOCX/imagem) e análise por IA para propor
    recompensas com a conduta individualizada de cada militar."""
    if request.method == "GET":
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, requisitos_lista=REQUISITOS_RECOMPENSA, resultado=None, erro=None)

    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, requisitos_lista=REQUISITOS_RECOMPENSA, resultado=None, erro="Selecione o arquivo do REDS (PDF, DOCX ou imagem).")

    nome_seguro = secure_filename(arquivo.filename)
    sufixo = Path(nome_seguro).suffix.lower()
    if sufixo not in EXTENSOES_SUPORTADAS:
        return render_template(
            "modulo_reds.html", resultado=None,
            erro=f"Extensão não suportada: {sufixo or '(sem extensão)'} (aceitos: {', '.join(sorted(EXTENSOES_SUPORTADAS))}).",
        )

    caminho_temp = Path(tempfile.mkdtemp(prefix="reds_")) / nome_seguro
    try:
        arquivo.save(caminho_temp)
        texto = extrair_texto(caminho_temp)
    except Exception as exc:
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, requisitos_lista=REQUISITOS_RECOMPENSA, resultado=None, erro=f"Falha ao ler o arquivo: {exc}")
    finally:
        caminho_temp.unlink(missing_ok=True)
        caminho_temp.parent.rmdir()

    resultado, erro = analisar_reds_texto(texto)
    if erro:
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, requisitos_lista=REQUISITOS_RECOMPENSA, resultado=None, erro=erro)
    if not resultado.get("militares"):
        erro = (
            "A IA não identificou nenhum policial militar atuando na ocorrência. Confira se o arquivo "
            "é mesmo um REDS legível" + (
                " Observações: " + "; ".join(str(o) for o in resultado.get("observacoes") or [])
                if resultado.get("observacoes") else "."
            )
        )
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, requisitos_lista=REQUISITOS_RECOMPENSA, resultado=None, erro=erro)
    return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, requisitos_lista=REQUISITOS_RECOMPENSA, resultado=resultado, erro=None)


def _militares_do_form(form) -> list[dict]:
    """Lê os militares selecionados/revisados na tela de análise do REDS."""
    try:
        total = int(form.get("total") or 0)
    except ValueError:
        total = 0
    militares = []
    for i in range(total):
        if not form.get(f"sel-{i}"):
            continue
        requisitos = {chave: bool(form.get(f"m-{i}-req-{chave}")) for chave, _ in REQUISITOS_RECOMPENSA}
        militares.append({
            "posto": (form.get(f"m-{i}-posto") or "").strip(),
            "numero": (form.get(f"m-{i}-numero") or "").strip(),
            "nome": (form.get(f"m-{i}-nome") or "").strip(),
            "unidade": (form.get(f"m-{i}-unidade") or "").strip(),
            "funcao": (form.get(f"m-{i}-funcao") or "").strip(),
            "sintese": (form.get(f"m-{i}-sintese") or "").strip(),
            "requisitos": requisitos,
        })
    return militares


def _criar_registros_recompensa(form, militares: list[dict]) -> int:
    """Cria um registro de Proposta de Recompensa por militar (persistência
    JSON do módulo, mesma dos formulários manuais)."""
    definicao = MODULOS["recompensa"]
    valores_base, _ = _valores_autofill("recompensa", definicao)
    for m in militares:
        dados = dict(valores_base)
        dados.update({
            "posto_proposto": m["posto"],
            "numero_proposto": m["numero"],
            "nome_proposto": m["nome"],
            "unidade_proposto": m["unidade"],
            "sintese_justificativa": m["sintese"],
            "reds_recompensa": (form.get("reds") or "").strip(),
            "tipo_recompensa": (form.get("tipo_recompensa") or "").strip() or "Elogio Individual",
            "data_proposta": date.today().isoformat(),
        })
        _salvar_registro("recompensa", uuid4().hex[:8], dados)
    return len(militares)


@bp_modulos.route("/recompensa/reds/criar", methods=["POST"])
def criar_propostas_reds():
    """Cria uma Proposta de Recompensa por militar selecionado na tela de
    análise do REDS e, se pedido, gera também o documento oficial (.docx)."""
    militares = _militares_do_form(request.form)
    _criar_registros_recompensa(request.form, militares)

    if request.form.get("gerar_documento") and militares:
        data_fato = None
        try:
            data_fato = date.fromisoformat(request.form.get("data_fato") or "")
        except ValueError:
            pass
        dados_doc = {
            "linha_regiao": request.form.get("linha_regiao"),
            "linha_unidade": request.form.get("linha_unidade"),
            "cidade_sede": request.form.get("cidade_sede"),
            "destinatario": request.form.get("destinatario"),
            "tipo_recompensa": request.form.get("tipo_recompensa"),
            "data_fato": data_fato,
            "data_fato_texto": request.form.get("data_fato"),
            "local_fato_linha": request.form.get("local_fato_linha"),
            "descricao": request.form.get("descricao"),
            "proponente_assinatura": request.form.get("proponente_assinatura"),
            "anexos": request.form.get("anexos"),
        }
        objetos = [
            MilitarProposta(
                numero=m["numero"], posto=m["posto"], nome=m["nome"], unidade=m["unidade"],
                funcao=m["funcao"], individualizacao=m["sintese"], requisitos=m["requisitos"],
            )
            for m in militares
        ]
        contexto = montar_contexto(dados_doc, objetos)
        reds_slug = re.sub(r"[^A-Za-z0-9]+", "_", request.form.get("reds") or "sem_reds").strip("_")
        nome_arquivo = f"proposta_recompensa_{reds_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        gerar_documento_recompensa(contexto, _diretorio_modulo("recompensa") / "documentos" / nome_arquivo)

    return redirect(url_for(".lista", modulo_id="recompensa"))


@bp_modulos.route("/recompensa/documentos/<path:nome_arquivo>")
def baixar_documento_recompensa(nome_arquivo):
    return send_from_directory(
        _diretorio_modulo("recompensa") / "documentos", nome_arquivo, as_attachment=True
    )


def listar_documentos_recompensa() -> list[str]:
    pasta = _diretorio_modulo("recompensa") / "documentos"
    if not pasta.exists():
        return []
    return sorted((p.name for p in pasta.glob("*.docx")), reverse=True)


# ------------------------------- sindicância de acidente com viatura (Cap. IX)

def _pasta_documentos_registro(modulo_id: str, registro_id: str) -> Path:
    """Cada sindicância tem sua própria pasta de peças - ao contrário da
    Recompensa, que gera um documento avulso por proposta. Aqui são 7 peças de
    UM mesmo procedimento, e misturá-las com as de outro seria confusão de
    autos."""
    return _diretorio_modulo(modulo_id) / "documentos" / registro_id


@bp_modulos.route("/acidente_viatura/<registro_id>/gerar", methods=["POST"])
def gerar_acidente_viatura(registro_id):
    payload = _carregar_registro("acidente_viatura", registro_id)
    if payload is None:
        abort(404)
    dados = payload.get("dados") or {}
    pasta = _pasta_documentos_registro("acidente_viatura", registro_id)
    resultado = gerar_documentos_acidente(dados, pasta)
    return render_template(
        "modulo_resultado.html",
        modulo_id="acidente_viatura",
        registro_id=registro_id,
        definicao=MODULOS["acidente_viatura"],
        resultado=resultado,
    )


@bp_modulos.route("/acidente_viatura/<registro_id>/documentos/<path:nome_arquivo>")
def baixar_documento_acidente(registro_id, nome_arquivo):
    return send_from_directory(
        _pasta_documentos_registro("acidente_viatura", registro_id), nome_arquivo, as_attachment=True
    )


def listar_documentos_registro(modulo_id: str, registro_id: str) -> list[str]:
    pasta = _pasta_documentos_registro(modulo_id, registro_id)
    if not pasta.exists():
        return []
    return sorted(p.name for p in pasta.glob("*.docx"))
