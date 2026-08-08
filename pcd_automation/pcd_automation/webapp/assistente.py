"""Assistente MAPPA flutuante - endpoint de conversa.

Blueprint próprio, separado do PCD: a integração com o app é uma linha aditiva
em `criar_app()`. O widget que consome este endpoint vive em `base.html`, então
fica disponível em todas as telas do sistema.

O histórico da conversa é mantido no NAVEGADOR e reenviado a cada pergunta.
Duas razões: o app é multi-página (cada navegação recarrega tudo, e uma
conversa guardada só na memória do servidor se perderia de vista ou exigiria
sessão com estado), e assim a conversa acompanha o usuário enquanto ele
transita entre os módulos.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from pcd_automation.rag import consulta as rag_consulta

bp_assistente = Blueprint("assistente", __name__, url_prefix="/assistente")

# Limites de segurança: a conversa vem do navegador, então não pode ser aceita
# sem teto - histórico gigante estouraria o contexto do modelo e o custo da
# chamada. 20 mensagens cobrem com folga uma consulta com acompanhamentos.
MAX_MENSAGENS = 20
MAX_CARACTERES = 4000


@bp_assistente.before_request
def _exigir_login_assistente():
    from pcd_automation.webapp.app import _exigir_login

    return _exigir_login()


@bp_assistente.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    brutas = payload.get("mensagens")
    if not isinstance(brutas, list):
        return jsonify({"erro": "Formato inválido: 'mensagens' deve ser uma lista."}), 400

    mensagens = []
    for item in brutas[-MAX_MENSAGENS:]:
        if not isinstance(item, dict):
            continue
        papel = "usuario" if item.get("papel") == "usuario" else "assistente"
        texto = str(item.get("texto") or "").strip()[:MAX_CARACTERES]
        if texto:
            mensagens.append({"papel": papel, "texto": texto})

    if not mensagens:
        return jsonify({"erro": "Digite uma pergunta."}), 400

    resultado = rag_consulta.responder_conversa(mensagens)
    return jsonify({
        "resposta": resultado.resposta,
        "erro": resultado.erro,
        # Só os nomes dos arquivos: a resposta já cita os artigos, e o texto
        # integral dos trechos deixaria o balão do chat ilegível. Quem quiser
        # ler o trecho inteiro usa a tela de Consulta.
        "fontes": sorted({t.arquivo for t in resultado.trechos}),
    })
