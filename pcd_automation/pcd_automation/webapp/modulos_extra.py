"""Módulos adicionais de procedimentos: Recompensa, RIP, SAD e APF.

Arquivo separado de propósito: o módulo de PCD (app.py) está validado e não
deve ser alterado. Este blueprint só ADICIONA telas novas - nenhuma rota,
lógica de estado ou template do PCD é tocado. A integração com o app é feita
por duas linhas aditivas em criar_app() (registro do blueprint) e uma seção
nova no dashboard.html.

Escopo atual: formulários de ENTRADA de dados com persistência em JSON
(`processos/_modulos/<modulo>/<id>.json`) - ainda não geram documento .docx
(não há modelos oficiais desses procedimentos no projeto; quando houver,
a geração pluga aqui sem mexer no PCD).

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

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from pcd_automation.extracao import EXTENSOES_SUPORTADAS, extrair_texto
from pcd_automation.ia_cliente import chamar_openrouter
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
    return render_template("modulo_lista.html", modulo_id=modulo_id, definicao=definicao, registros=registros)


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
e unidade, quando constarem do texto. Não inclua vítimas, autores, testemunhas civis nem militares \
apenas citados sem atuação.

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

Liste em "observacoes" qualquer ressalva (trechos ilegíveis, militar sem matrícula no texto, dúvida \
sobre quem fez o quê).

Responda SOMENTE com um objeto JSON válido, sem markdown, exatamente neste formato:
{"reds": "...", "data_fato": "aaaa-mm-dd", "hora_fato": "...", "municipio": "...", "local_fato": "...", \
"resumo_ocorrencia": "...", "militares": [{"posto": "...", "nome": "...", "numero": "...", \
"unidade": "...", "conduta_individual": "...", "sintese_proposta": "..."}], "observacoes": ["..."]}
"""


def _extrair_json_ia(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip(), flags=re.IGNORECASE)
    return json.loads(texto)


def analisar_reds_texto(texto: str) -> tuple[dict | None, str | None]:
    """Analisa o texto extraído de um REDS. Retorna (resultado, erro) -
    exatamente um dos dois é None."""
    if not texto.strip():
        return None, (
            "Não foi possível extrair nenhum texto do arquivo (pode estar em branco, corrompido ou "
            "o OCR não reconheceu nada)."
        )
    conteudo, erro = chamar_openrouter(
        [
            {"role": "system", "content": PROMPT_REDS},
            {"role": "user", "content": f"Texto extraído do REDS:\n\n{texto[:150000]}"},
        ],
        max_tokens=6000,
        timeout=120,
        json_obrigatorio=True,
    )
    if erro:
        return None, erro
    try:
        dados = _extrair_json_ia(conteudo)
    except json.JSONDecodeError:
        return None, f"A IA não retornou um JSON válido. Resposta bruta: {conteudo[:400]}"

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
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, resultado=None, erro=None)

    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, resultado=None, erro="Selecione o arquivo do REDS (PDF, DOCX ou imagem).")

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
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, resultado=None, erro=f"Falha ao ler o arquivo: {exc}")
    finally:
        caminho_temp.unlink(missing_ok=True)
        caminho_temp.parent.rmdir()

    resultado, erro = analisar_reds_texto(texto)
    if erro:
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, resultado=None, erro=erro)
    if not resultado.get("militares"):
        erro = (
            "A IA não identificou nenhum policial militar atuando na ocorrência. Confira se o arquivo "
            "é mesmo um REDS legível" + (
                " Observações: " + "; ".join(str(o) for o in resultado.get("observacoes") or [])
                if resultado.get("observacoes") else "."
            )
        )
        return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, resultado=None, erro=erro)
    return render_template("modulo_reds.html", opcoes_posto=OPCOES_POSTO, resultado=resultado, erro=None)


@bp_modulos.route("/recompensa/reds/criar", methods=["POST"])
def criar_propostas_reds():
    """Cria uma Proposta de Recompensa por militar selecionado na tela de
    análise do REDS, com os textos já revisados/editados pelo usuário."""
    definicao = MODULOS["recompensa"]
    # Proponente: mesmo autofill do formulário novo (último registro salvo).
    valores_base, _ = _valores_autofill("recompensa", definicao)

    try:
        total = int(request.form.get("total") or 0)
    except ValueError:
        total = 0

    criados = 0
    for i in range(total):
        if not request.form.get(f"sel-{i}"):
            continue
        dados = dict(valores_base)
        dados.update({
            "posto_proposto": (request.form.get(f"m-{i}-posto") or "").strip(),
            "numero_proposto": (request.form.get(f"m-{i}-numero") or "").strip(),
            "nome_proposto": (request.form.get(f"m-{i}-nome") or "").strip(),
            "unidade_proposto": (request.form.get(f"m-{i}-unidade") or "").strip(),
            "sintese_justificativa": (request.form.get(f"m-{i}-sintese") or "").strip(),
            "reds_recompensa": (request.form.get("reds") or "").strip(),
            "tipo_recompensa": dados.get("tipo_recompensa") or "Elogio Individual",
            "data_proposta": date.today().isoformat(),
        })
        _salvar_registro("recompensa", uuid4().hex[:8], dados)
        criados += 1

    return redirect(url_for(".lista", modulo_id="recompensa"))
