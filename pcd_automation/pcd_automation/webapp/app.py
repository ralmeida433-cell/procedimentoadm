"""Interface web local do assistente de PCD.

Reaproveita 100% as mesmas funções de `gerador_portarias` e a mesma
persistência de estado (`pcd_automation.interativo.estado`) usadas pelo
assistente de terminal (`python main.py novo` / `continuar`) - os dois
front-ends são intercambiáveis: um PCD começado pelo terminal pode ser
continuado pela página web e vice-versa.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import shutil
import tempfile
from datetime import date
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from pcd_automation import extracao, sugestao_fato
from pcd_automation.gerador_portarias.planilha import CAMPOS_INFO, converter_valor
from pcd_automation.gestao_prazos import gerar_alertas_processo
from pcd_automation.interativo import estado
from pcd_automation.interativo.perguntas import ETAPAS, Etapa, indice_etapa, processo_concluido, proxima_etapa
from pcd_automation.rag import consulta as rag_consulta
from pcd_automation.redacao import formatar_hora_br, validar_texto
from pcd_automation.schema import CAMPOS_OBRIGATORIOS_INSTAURACAO
from pcd_automation.validador_juridico import (
    validar_alertas_procedimentais,
    validar_consistencia_datas,
    validar_numeracao_folhas,
    validar_processo,
)
from pcd_automation.webapp.campos_ui import CAMPOS_OPCOES, GRUPOS_INSTAURACAO, TOOLTIPS, normalizar_posto
from pcd_automation.webapp.cidades_mg import CIDADES_MG
from pcd_automation.webapp.unidades_pmmg import UNIDADES_PMMG

# Campos de posto/graduação sujeitos a normalização (abreviado -> forma canônica)
# quando vêm de texto livre extraído de um documento (`/extrair`).
_CAMPOS_POSTO = {chave for chave in CAMPOS_OPCOES if chave.startswith("posto_")}

# Valores que a IA às vezes escreve por extenso em vez de omitir o campo,
# apesar da instrução em contrário - tratados como "não encontrado".
_VALORES_NAO_ENCONTRADO = {
    "não informado", "nao informado", "não informado no texto", "nao informado no texto",
    "não consta", "nao consta", "não encontrado", "nao encontrado", "n/a", "não disponível",
}

bp = Blueprint("pcd", __name__)


# ---------------------------------------------------------------- autenticação
#
# Proteção simples por senha única (ferramenta de um usuário só). A senha vem
# da variável de ambiente PCD_SENHA:
#   - se PCD_SENHA ESTIVER definida, todas as páginas exigem login;
#   - se NÃO estiver (ex.: uso local no seu PC), o app fica aberto, como antes.
# Ou seja: no servidor (PythonAnywhere) você DEFINE PCD_SENHA para ativar o
# login; no seu computador, sem definir nada, continua sem senha.
#
# É uma proteção básica (uma senha compartilhada), adequada para uso pessoal /
# de treino - NÃO é um controle de acesso multiusuário com perfis. Para dados
# reais de PCD, isso exigiria infraestrutura oficial da PMMG.

def _senha_configurada() -> str | None:
    senha = os.environ.get("PCD_SENHA")
    return senha if senha else None


@bp.before_request
def _exigir_login():
    if _senha_configurada() is None:
        return  # sem senha definida -> app aberto (uso local)
    # Rotas liberadas mesmo sem login: a própria tela de login e os estáticos.
    if request.endpoint in ("pcd.login", "static"):
        return
    if not session.get("autenticado"):
        return redirect(url_for("pcd.login", proxima=request.full_path))


@bp.route("/login", methods=["GET", "POST"])
def login():
    senha_correta = _senha_configurada()
    if senha_correta is None:
        # Login não se aplica (app aberto) - manda pro painel.
        return redirect(url_for("pcd.dashboard"))

    erro = None
    if request.method == "POST":
        informada = request.form.get("senha") or ""
        # Comparação em tempo constante para não vazar o tamanho/conteúdo da senha.
        if hmac.compare_digest(informada, senha_correta):
            session["autenticado"] = True
            proxima = request.form.get("proxima") or url_for("pcd.dashboard")
            # Evita open-redirect: só aceita caminhos internos.
            if not proxima.startswith("/"):
                proxima = url_for("pcd.dashboard")
            return redirect(proxima)
        erro = "Senha incorreta."

    proxima = request.args.get("proxima") or url_for("pcd.dashboard")
    return render_template("login.html", erro=erro, proxima=proxima)


@bp.route("/logout")
def logout():
    session.pop("autenticado", None)
    return redirect(url_for("pcd.login"))


CAMPOS_LONGOS = {
    "resumo_fato", "analise_fatos_e_provas", "alegacoes_defesa_analise",
    "teor_depoimento", "observacoes_impedimento", "outras_provas",
}

# Campos de hora: no formulário viram um seletor de horário (HH:MM) e no
# documento saem no padrão oficial "XXhXXmin" (a formatação é feita na geração).
CAMPOS_HORA = {
    "hora_fato", "hora_oitiva", "hora_inicio_depoimento", "hora_fim_depoimento",
    "hora_proxima_oitiva", "hora_inicio_reuniao", "hora_fim_reuniao",
}


def _hora_para_input(valor) -> str:
    """Converte um valor de hora salvo (em qualquer forma) para 'HH:MM', que é
    o que o <input type=time> espera. Ex.: '8' -> '08:00', '1502' -> '15:02'."""
    fmt = formatar_hora_br(valor)  # -> 'XXhXXmin' ou ''
    if fmt and len(fmt) == 8 and fmt[2] == "h" and fmt.endswith("min"):
        return f"{fmt[:2]}:{fmt[3:5]}"
    return ""


# Campos de cidade: no formulário ganham autocompletar com os 853 municípios
# de MG (via <datalist> nativo). É só sugestão - o usuário pode digitar
# qualquer valor (ex.: uma cidade de outro estado na naturalidade).
CAMPOS_CIDADE = {"cidade_fato", "cidade_sede", "cidade_reuniao", "naturalidade_testemunha"}

# Campos de unidade: autocompletar com a base de unidades da PMMG (sugestão;
# aceita texto livre para frações específicas fora da lista).
CAMPOS_UNIDADE = {
    "unidade_sindicado", "unidade_comunicante", "unidade_autoridade_processante", "unidade_testemunha",
}

# Campos de texto livre em que vale checar a redação oficial (avisos, não erros).
CAMPOS_REDACAO = CAMPOS_LONGOS | {
    "resumo_fato", "local_fato", "incidentes_processuais", "teor_depoimento",
}


def _avisos_redacao(dados: dict) -> list[str]:
    avisos: list[str] = []
    for chave in CAMPOS_REDACAO:
        valor = dados.get(chave)
        if isinstance(valor, str) and valor.strip():
            rotulo = CAMPOS_INFO.get(chave, (chave, ""))[0]
            for msg in validar_texto(valor):
                avisos.append(f"{rotulo}: {msg}")
    return avisos


@bp.app_context_processor
def _injetar_globals():
    return {
        "etapas_todas": ETAPAS,
        "login_ativo": _senha_configurada() is not None,
        "cidades_mg": CIDADES_MG,
        "unidades_pmmg": UNIDADES_PMMG,
    }


def _diretorio_base() -> Path:
    return Path(current_app.config["DIRETORIO_BASE"])


# ---------------------------------------------------------------- conversão

def _valor_formulario(chave: str, form):
    _, tipo = CAMPOS_INFO.get(chave, (chave, "texto"))
    bruto = (form.get(chave) or "").strip()
    if not bruto:
        return None
    if tipo == "data":
        try:
            return date.fromisoformat(bruto)
        except ValueError:
            return None
    if tipo == "sim_nao":
        return converter_valor("sim_nao", bruto)
    return converter_valor("texto", bruto)


def _processar_formulario(etapa: Etapa, form) -> dict:
    return {chave: _valor_formulario(chave, form) for chave in etapa.campos_obrigatorios + etapa.campos_opcionais}


def _campos_faltando(etapa: Etapa, dados: dict) -> list[str]:
    faltando = []
    for chave in etapa.campos_obrigatorios:
        if dados.get(chave) in (None, ""):
            rotulo, _ = CAMPOS_INFO.get(chave, (chave, "texto"))
            faltando.append(rotulo)
    return faltando


def _valor_para_input(chave: str, dados: dict) -> str:
    valor = dados.get(chave)
    _, tipo = CAMPOS_INFO.get(chave, (chave, "texto"))
    if valor in (None, ""):
        return ""
    if chave in CAMPOS_HORA:
        return _hora_para_input(valor)
    if tipo == "data" and isinstance(valor, date):
        return valor.isoformat()
    if tipo == "sim_nao":
        return "S" if valor else "N"
    return str(valor)


def _tipo_para_template(chave: str, tipo: str) -> str:
    if chave in CAMPOS_HORA:
        return "hora"
    if chave in CAMPOS_CIDADE:
        return "cidade"
    if chave in CAMPOS_UNIDADE:
        return "unidade"
    if chave in CAMPOS_OPCOES:
        return "select"
    return "texto_longo" if chave in CAMPOS_LONGOS else tipo


def _campo_dict(chave: str, obrigatorio: bool, dados: dict) -> dict:
    rotulo, tipo = CAMPOS_INFO.get(chave, (chave, "texto"))
    valor = _valor_para_input(chave, dados)
    opcoes = CAMPOS_OPCOES.get(chave)
    # Preserva valor antigo que não esteja na lista (ex.: rascunho digitado à mão)
    valor_fora_da_lista = bool(opcoes) and valor and valor not in {v for v, _ in opcoes}
    return {
        "chave": chave,
        "rotulo": rotulo,
        "tipo": _tipo_para_template(chave, tipo),
        "valor": valor,
        "obrigatorio": obrigatorio,
        "tooltip": TOOLTIPS.get(chave, ""),
        "opcoes": opcoes,
        "valor_fora_da_lista": valor_fora_da_lista,
    }


def _grupos_para_template(etapa: Etapa, dados: dict) -> list[dict]:
    """Organiza os campos da etapa em grupos lógicos para exibição.

    A etapa de instauração usa o agrupamento nomeado (Dados do Fato /
    Envolvimento / Instauração / Adicionais); as demais etapas caem no
    padrão obrigatórios/opcionais. Nenhum campo é descartado - o que não
    estiver mapeado vai para um grupo "Outros".
    """
    obrigatorios = set(etapa.campos_obrigatorios)
    todos = etapa.campos_obrigatorios + etapa.campos_opcionais

    if etapa.id == "instauracao":
        grupos: list[dict] = []
        mapeados: set[str] = set()
        for titulo, chaves in GRUPOS_INSTAURACAO:
            campos = [_campo_dict(c, c in obrigatorios, dados) for c in chaves if c in todos]
            mapeados.update(c for c in chaves if c in todos)
            if campos:
                grupos.append({"titulo": titulo, "campos": campos})
        restantes = [c for c in todos if c not in mapeados]
        if restantes:
            grupos.append({
                "titulo": "Outros",
                "campos": [_campo_dict(c, c in obrigatorios, dados) for c in restantes],
            })
        return grupos

    grupos = [{
        "titulo": "Campos obrigatórios",
        "campos": [_campo_dict(c, True, dados) for c in etapa.campos_obrigatorios],
    }]
    if etapa.campos_opcionais:
        grupos.append({
            "titulo": "Campos opcionais",
            "campos": [_campo_dict(c, False, dados) for c in etapa.campos_opcionais],
        })
    return grupos


def _campos_preenchidos(dados: dict) -> list[tuple[str, str]]:
    linhas = []
    for chave, valor in dados.items():
        if valor in (None, ""):
            continue
        rotulo, tipo = CAMPOS_INFO.get(chave, (chave, "texto"))
        if tipo == "sim_nao":
            valor_fmt = "Sim" if valor else "Não"
        elif isinstance(valor, date):
            valor_fmt = valor.strftime("%d/%m/%Y")
        else:
            valor_fmt = str(valor)
        linhas.append((rotulo, valor_fmt))
    return linhas


def _resultado_para_template(resultado) -> dict:
    documentos = []
    for campo in (
        "caminho_comunicacao", "caminho_despacho", "caminho_termo",
        "caminho_notificacao_testemunha", "caminho_notificacao_sindicado",
    ):
        valor = getattr(resultado, campo, None)
        if valor:
            documentos.append(Path(valor).name)
    prazo = getattr(resultado, "prazo_conclusao", None) or getattr(resultado, "prazo_defesa", None)
    return {
        "ok": resultado.ok,
        "erros": resultado.erros,
        "documentos": documentos,
        "prazo": prazo,
        "alertas": getattr(resultado, "alertas", None) or [],
        "pendentes": getattr(resultado, "campos_manuais_pendentes", None) or [],
        "processo_id": getattr(resultado, "processo_id", None),
    }


# ---------------------------------------------------------------- dashboard

@bp.route("/")
def dashboard():
    diretorio_base = _diretorio_base()
    rascunhos = []
    for chave in estado.listar_rascunhos(diretorio_base):
        dados = estado.carregar_rascunho(diretorio_base, chave) or {}
        rascunhos.append({"chave": chave, "reds": dados.get("reds"), "nome": dados.get("nome_sindicado")})

    processos = []
    for diretorio in estado.listar_processos_em_andamento(diretorio_base):
        carregado = estado.carregar_estado_processo(diretorio)
        if carregado is None:
            continue
        dados, etapa_ate = carregado
        indice_atual = indice_etapa(etapa_ate)
        concluido = processo_concluido(indice_atual, dados)
        processos.append({
            "id": diretorio.name,
            "reds": dados.get("reds"),
            "nome": dados.get("nome_sindicado"),
            "etapa_atual": ETAPAS[indice_atual].titulo,
            "etapa_atual_id": ETAPAS[indice_atual].id,
            "concluido": concluido,
        })

    return render_template("dashboard.html", rascunhos=rascunhos, processos=processos)


@bp.route("/rascunho/<chave>/excluir", methods=["GET", "POST"])
def excluir_rascunho(chave):
    diretorio_base = _diretorio_base()
    dados = estado.carregar_rascunho(diretorio_base, chave)
    if dados is None:
        abort(404)

    if request.method == "POST":
        estado.remover_rascunho(diretorio_base, chave)
        return redirect(url_for(".dashboard"))

    rotulo = f"{dados.get('reds') or '(sem REDS ainda)'} - {dados.get('nome_sindicado') or '(sem nome ainda)'}"
    return render_template(
        "confirmar_exclusao.html",
        titulo="Excluir rascunho",
        rotulo_alvo=rotulo,
        descricao="Este PCD ainda não foi instaurado - nenhum documento oficial existe para ele ainda. "
                   "Só os dados digitados até agora serão perdidos.",
        documentos=[],
        action=url_for(".excluir_rascunho", chave=chave),
        voltar=url_for(".dashboard"),
    )


@bp.route("/processo/<processo_id>/excluir", methods=["GET", "POST"])
def excluir_processo(processo_id):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    carregado = estado.carregar_estado_processo(diretorio_processo)
    if carregado is None:
        abort(404)

    if request.method == "POST":
        shutil.rmtree(diretorio_processo)
        return redirect(url_for(".dashboard"))

    documentos = sorted(p.name for p in diretorio_processo.glob("*.docx"))
    return render_template(
        "confirmar_exclusao.html",
        titulo="Excluir processo",
        rotulo_alvo=processo_id,
        descricao="Esta ação apaga a pasta inteira do processo, incluindo TODOS os documentos .docx "
                   "já gerados e assinados. Não há como desfazer.",
        documentos=documentos,
        action=url_for(".excluir_processo", processo_id=processo_id),
        voltar=url_for(".dashboard"),
    )


# ---------------------------------------------------------------- instauração (rascunho)

@bp.route("/novo")
def novo():
    diretorio_base = _diretorio_base()
    chave = f"rascunho-{uuid4().hex[:8]}"
    estado.salvar_rascunho(diretorio_base, chave, {})
    return redirect(url_for(".editar_rascunho", chave=chave))


@bp.route("/rascunho/<chave>", methods=["GET", "POST"])
def editar_rascunho(chave):
    diretorio_base = _diretorio_base()
    dados_existentes = estado.carregar_rascunho(diretorio_base, chave)
    if dados_existentes is None:
        abort(404)
    etapa = ETAPAS[0]

    if request.method == "POST":
        dados = {**dados_existentes, **_processar_formulario(etapa, request.form)}
        faltando = _campos_faltando(etapa, dados)
        estado.salvar_rascunho(diretorio_base, chave, dados)
        if faltando:
            return render_template(
                "formulario.html", etapa=etapa, grupos=_grupos_para_template(etapa, dados),
                erros=[f"Campo obrigatório: {r}" for r in faltando],
                action=url_for(".editar_rascunho", chave=chave), titulo="Novo PCD - Instauração",
            )
        return redirect(url_for(".preview_rascunho", chave=chave))

    grupos = _grupos_para_template(etapa, dados_existentes)
    return render_template(
        "formulario.html", etapa=etapa, grupos=grupos, erros=[],
        action=url_for(".editar_rascunho", chave=chave), titulo="Novo PCD - Instauração",
    )


@bp.route("/rascunho/<chave>/preview")
def preview_rascunho(chave):
    diretorio_base = _diretorio_base()
    dados = estado.carregar_rascunho(diretorio_base, chave)
    if dados is None:
        abort(404)
    resultado_validacao = validar_processo(dados)
    return render_template(
        "preview.html", titulo="Conferir antes de instaurar", linhas=_campos_preenchidos(dados),
        erros=resultado_validacao.erros, alertas=resultado_validacao.alertas, pode_confirmar=resultado_validacao.ok,
        avisos_redacao=_avisos_redacao(dados),
        action=url_for(".instaurar", chave=chave), voltar=url_for(".editar_rascunho", chave=chave),
    )


@bp.route("/rascunho/<chave>/instaurar", methods=["POST"])
def instaurar(chave):
    diretorio_base = _diretorio_base()
    dados = estado.carregar_rascunho(diretorio_base, chave)
    if dados is None:
        abort(404)
    etapa = ETAPAS[0]
    resultado = etapa.funcao(dados, diretorio_base)

    processo_id = None
    proxima = None
    if resultado.ok:
        estado.remover_rascunho(diretorio_base, chave)
        estado.salvar_estado_processo(resultado.diretorio, dados, etapa_concluida_ate="instauracao")
        processo_id = resultado.processo_id
        proxima = proxima_etapa(0, dados)

    return render_template(
        "resultado.html", processo_id=processo_id, titulo="Instauração",
        resultado=_resultado_para_template(resultado), proxima=proxima,
    )


# ---------------------------------------------------------------- etapas seguintes

@bp.route("/processo/<processo_id>")
def status_processo(processo_id):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    carregado = estado.carregar_estado_processo(diretorio_processo)
    if carregado is None:
        abort(404)
    dados, etapa_ate = carregado
    indice_atual = indice_etapa(etapa_ate)
    proxima = proxima_etapa(indice_atual, dados)
    documentos = sorted(p.name for p in diretorio_processo.glob("*.docx"))

    alertas_prazo = (
        gerar_alertas_processo(dados)
        + validar_consistencia_datas(dados)
        + validar_alertas_procedimentais(dados)
        + validar_numeracao_folhas(dados)
    )

    return render_template(
        "status.html", processo_id=processo_id, etapa_atual_titulo=ETAPAS[indice_atual].titulo,
        proxima=proxima, documentos=documentos, concluido=(proxima is None),
        linhas=_campos_preenchidos(dados), alertas_prazo=alertas_prazo,
    )


@bp.route("/processo/<processo_id>/etapa/<etapa_id>", methods=["GET", "POST"])
def formulario_etapa(processo_id, etapa_id):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    carregado = estado.carregar_estado_processo(diretorio_processo)
    if carregado is None:
        abort(404)
    dados, etapa_ate = carregado
    etapa = ETAPAS[indice_etapa(etapa_id)]

    if request.method == "POST":
        dados_atualizados = {**dados, **_processar_formulario(etapa, request.form)}
        faltando = _campos_faltando(etapa, dados_atualizados)
        estado.salvar_estado_processo(diretorio_processo, dados_atualizados, etapa_concluida_ate=etapa_ate)
        if faltando:
            return render_template(
                "formulario.html", etapa=etapa, grupos=_grupos_para_template(etapa, dados_atualizados),
                erros=[f"Campo obrigatório: {r}" for r in faltando],
                action=url_for(".formulario_etapa", processo_id=processo_id, etapa_id=etapa_id), titulo=etapa.titulo,
            )
        return redirect(url_for(".preview_etapa", processo_id=processo_id, etapa_id=etapa_id))

    grupos = _grupos_para_template(etapa, dados)
    return render_template(
        "formulario.html", etapa=etapa, grupos=grupos, erros=[],
        action=url_for(".formulario_etapa", processo_id=processo_id, etapa_id=etapa_id), titulo=etapa.titulo,
    )


@bp.route("/processo/<processo_id>/etapa/<etapa_id>/preview")
def preview_etapa(processo_id, etapa_id):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    carregado = estado.carregar_estado_processo(diretorio_processo)
    if carregado is None:
        abort(404)
    dados, _ = carregado
    etapa = ETAPAS[indice_etapa(etapa_id)]
    return render_template(
        "preview.html", titulo=f"Conferir antes de gerar - {etapa.titulo}", linhas=_campos_preenchidos(dados),
        erros=[], alertas=[], pode_confirmar=True,
        avisos_redacao=_avisos_redacao(dados),
        action=url_for(".executar_etapa", processo_id=processo_id, etapa_id=etapa_id),
        voltar=url_for(".formulario_etapa", processo_id=processo_id, etapa_id=etapa_id),
    )


@bp.route("/processo/<processo_id>/etapa/<etapa_id>/executar", methods=["POST"])
def executar_etapa(processo_id, etapa_id):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    carregado = estado.carregar_estado_processo(diretorio_processo)
    if carregado is None:
        abort(404)
    dados, etapa_ate_anterior = carregado
    etapa = ETAPAS[indice_etapa(etapa_id)]
    resultado = etapa.funcao(dados, diretorio_base)

    etapa_ate_final = etapa_id if resultado.ok else etapa_ate_anterior
    estado.salvar_estado_processo(diretorio_processo, dados, etapa_concluida_ate=etapa_ate_final)

    indice_atual = indice_etapa(etapa_id)
    proxima = proxima_etapa(indice_atual, dados) if resultado.ok else None

    return render_template(
        "resultado.html", processo_id=processo_id, titulo=etapa.titulo,
        resultado=_resultado_para_template(resultado), proxima=proxima,
    )


@bp.route("/processo/<processo_id>/download/<path:nome_arquivo>")
def download(processo_id, nome_arquivo):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    if estado.carregar_estado_processo(diretorio_processo) is None:
        abort(404)
    return send_from_directory(diretorio_processo, nome_arquivo, as_attachment=True)


@bp.route("/processo/<processo_id>/visualizar/<path:nome_arquivo>")
def visualizar_documento(processo_id, nome_arquivo):
    diretorio_base = _diretorio_base()
    diretorio_processo = diretorio_base / processo_id
    if estado.carregar_estado_processo(diretorio_processo) is None:
        abort(404)
    caminho_arquivo = diretorio_processo / nome_arquivo
    if not caminho_arquivo.is_file():
        abort(404)

    conteudo_html = None
    erro = None
    try:
        import mammoth

        with open(caminho_arquivo, "rb") as arquivo:
            conteudo_html = mammoth.convert_to_html(arquivo).value
    except Exception as exc:
        erro = f"Não foi possível gerar a prévia deste documento: {exc}"

    return render_template(
        "visualizar_documento.html",
        processo_id=processo_id,
        nome_arquivo=nome_arquivo,
        conteudo_html=conteudo_html,
        erro=erro,
        url_download=url_for(".download", processo_id=processo_id, nome_arquivo=nome_arquivo),
        url_voltar=url_for(".status_processo", processo_id=processo_id),
    )


@bp.route("/consultar", methods=["GET", "POST"])
def consultar():
    pergunta = ""
    resultado = None
    if request.method == "POST":
        pergunta = (request.form.get("pergunta") or "").strip()
        if pergunta:
            resultado = rag_consulta.responder(pergunta)
    return render_template("consultar.html", pergunta=pergunta, resultado=resultado)


# ------------------------------------------------- análise do resumo do fato (IA)

@bp.route("/analisar-fato", methods=["POST"])
def analisar_fato():
    """Analisa a descrição livre do fato e devolve, em JSON, o texto reescrito
    na redação oficial e as transgressões do CEDM compatíveis. É consultivo: o
    formulário só preenche os campos se o encarregado clicar em aplicar."""
    descricao = ((request.get_json(silent=True) or {}).get("descricao") or "").strip()
    r = sugestao_fato.analisar(descricao)
    return jsonify(
        {
            "erro": r.erro,
            "resumo_fato": r.resumo_fato,
            "dados_faltantes": r.dados_faltantes,
            "observacoes": r.observacoes,
            "avisos_redacao": r.avisos_redacao,
            "tipificacoes": [
                {
                    "tipificacao": t.tipificacao,
                    # Texto que efetivamente vai para o campo e para o documento.
                    "texto_documento": t.transgressao.texto_para_documento,
                    "natureza": t.transgressao.natureza,
                    "texto_legal": t.transgressao.texto,
                    "justificativa": t.justificativa,
                    "confianca": t.confianca,
                }
                for t in r.tipificacoes
            ],
            "candidatas": [
                {
                    "tipificacao": c.tipificacao,
                    "texto_documento": c.texto_para_documento,
                    "natureza": c.natureza,
                    "texto_legal": c.texto,
                }
                for c in r.candidatas
            ],
        }
    )


# ---------------------------------------------------------------- extração de documentos (IA)

@bp.route("/extrair", methods=["GET", "POST"])
def extrair():
    if request.method == "GET":
        return render_template("extrair.html", erro=None)

    arquivo = request.files.get("arquivo")
    if arquivo is None or not arquivo.filename:
        return render_template("extrair.html", erro="Selecione um arquivo (PDF, DOCX ou imagem).")

    nome_seguro = secure_filename(arquivo.filename)
    sufixo = Path(nome_seguro).suffix.lower()
    if sufixo not in extracao.EXTENSOES_SUPORTADAS:
        return render_template(
            "extrair.html",
            erro=f"Extensão '{sufixo}' não suportada. Aceitos: {', '.join(sorted(extracao.EXTENSOES_SUPORTADAS))}.",
        )

    with tempfile.TemporaryDirectory() as diretorio_temp:
        caminho_temp = Path(diretorio_temp) / (nome_seguro or f"upload{sufixo}")
        arquivo.save(caminho_temp)
        try:
            texto = extracao.extrair_texto(caminho_temp)
        except Exception as exc:
            return render_template("extrair.html", erro=f"Falha ao ler o arquivo: {exc}")

    resultado = extracao.classificar_e_extrair(texto)
    if resultado.erro:
        return render_template("extrair.html", erro=resultado.erro)

    campos_validos = {
        chave: (normalizar_posto(valor) if chave in _CAMPOS_POSTO else valor)
        for chave, valor in resultado.campos.items()
        if valor and str(valor).strip().lower() not in _VALORES_NAO_ENCONTRADO
    }
    campos_exibicao = [
        (CAMPOS_INFO.get(chave, (chave, ""))[0], valor) for chave, valor in campos_validos.items()
    ]
    # Campos que o schema considera obrigatórios para instaurar (REDS não entra aqui - é
    # opcional na prática, nem todo PCD nasce de um REDS) e que a IA não encontrou no texto.
    campos_criticos_faltando = [
        CAMPOS_INFO.get(chave, (chave, ""))[0]
        for chave in CAMPOS_OBRIGATORIOS_INSTAURACAO
        if chave not in campos_validos
    ]

    return render_template(
        "extrair_resultado.html",
        nome_arquivo=arquivo.filename,
        tipo_documento=resultado.tipo_documento,
        confianca_tipo=resultado.confianca_tipo,
        ambiguidades=resultado.ambiguidades,
        campos_exibicao=campos_exibicao,
        campos_criticos_faltando=campos_criticos_faltando,
        campos_json=json.dumps(campos_validos, ensure_ascii=False),
    )


@bp.route("/extrair/confirmar", methods=["POST"])
def extrair_confirmar():
    try:
        campos_extraidos = json.loads(request.form.get("campos_json") or "{}")
    except json.JSONDecodeError:
        campos_extraidos = {}

    dados: dict = {}
    for chave, valor_bruto in campos_extraidos.items():
        if chave not in CAMPOS_INFO:
            continue  # campo que a IA inventou fora do schema - ignorado, não é gravado
        _, tipo = CAMPOS_INFO[chave]
        if tipo == "data":
            try:
                dados[chave] = date.fromisoformat(str(valor_bruto))
            except ValueError:
                continue  # data em formato inesperado - fica em branco para o usuário preencher
        else:
            dados[chave] = converter_valor("texto", valor_bruto)

    diretorio_base = _diretorio_base()
    chave_rascunho = f"rascunho-{uuid4().hex[:8]}"
    estado.salvar_rascunho(diretorio_base, chave_rascunho, dados)
    return redirect(url_for(".editar_rascunho", chave=chave_rascunho))


def criar_app(diretorio_base: Path | str) -> Flask:
    app = Flask(__name__)
    app.config["DIRETORIO_BASE"] = Path(diretorio_base)
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB - limite de upload em /extrair
    # Chave para assinar os cookies de sessão (login). Idealmente vem de
    # PCD_SECRET_KEY (fixa entre reinícios); se ausente, gera uma aleatória -
    # funciona, mas desloga todo mundo a cada reinício do servidor.
    app.config["SECRET_KEY"] = os.environ.get("PCD_SECRET_KEY") or secrets.token_hex(32)
    app.register_blueprint(bp)
    return app
