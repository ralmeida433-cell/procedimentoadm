"""Tela de configurações: chave de API e escolha do modelo de IA.

Guarda a chave no arquivo `.env` da pasta do projeto (o mesmo que o sistema já
lê na inicialização) e aplica em memória na hora, para valer sem reiniciar.

Cuidados com o segredo, que é o ponto sensível desta tela:

- o campo é do tipo `password`, então não aparece na tela nem em gravação;
- a chave NUNCA é devolvida ao navegador. A tela mostra só o prefixo e os
  4 últimos caracteres ("sk-or-v1-…a1b2"), suficiente para o usuário conferir
  QUAL chave está salva sem expor a chave;
- o `.env` já está no .gitignore, então não vai para o repositório;
- a chave não entra em log nem em mensagem de erro.

Sobre "usar a IA paga do Google": o Gemini é alcançável pela própria OpenRouter
(google/gemini-*), com a mesma chave e o mesmo código. Isso evita a integração
direta com o Google AI Studio, que é justamente a que falhou neste projeto -
as chaves novas do Google (prefixo "AQ.") retornam 401 de forma generalizada, e
foi por isso que o sistema migrou para a OpenRouter.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, url_for

bp_config = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")

CAMINHO_ENV = Path(__file__).resolve().parents[2] / ".env"

# (valor, rótulo, observação). Só modelos verificados na OpenRouter.
MODELOS_OFERECIDOS = [
    ("nvidia/nemotron-3-ultra-550b-a55b:free",
     "Gratuito — Nemotron 3 Ultra (padrão)",
     "Sem custo. Roda em capacidade compartilhada: pode ficar lento ou indisponível em horário de pico."),
    ("google/gemini-2.5-flash-lite",
     "Pago — Google Gemini 2.5 Flash Lite",
     "IA paga do Google, cobrada pela OpenRouter: US$ 0,10 por milhão de tokens de entrada e US$ 0,40 de saída. "
     "Uma consulta típica custa fração de centavo. 1 milhão de tokens de contexto."),
    ("google/gemini-3.1-flash-lite",
     "Pago — Google Gemini 3.1 Flash Lite",
     "Geração mais recente: US$ 0,25 de entrada e US$ 1,50 de saída por milhão de tokens."),
    ("qwen/qwen3.7-flash",
     "Pago — Qwen 3.7 Flash (mais barato)",
     "US$ 0,03 de entrada e US$ 0,13 de saída por milhão de tokens, com 1 milhão de contexto."),
]


@bp_config.before_request
def _exigir_login_config():
    from pcd_automation.webapp.app import _exigir_login

    return _exigir_login()


def mascarar(chave: str | None) -> str:
    """Mostra só o suficiente para o usuário reconhecer a chave salva."""
    chave = (chave or "").strip()
    if not chave:
        return ""
    if len(chave) <= 12:
        return "•" * len(chave)
    return f"{chave[:9]}…{chave[-4:]}"


def _gravar_env(atualizacoes: dict[str, str]) -> None:
    """Atualiza as chaves no .env preservando o resto do arquivo (comentários e
    outras variáveis que o usuário tenha posto lá)."""
    linhas: list[str] = []
    if CAMINHO_ENV.exists():
        linhas = CAMINHO_ENV.read_text(encoding="utf-8").splitlines()

    restantes = dict(atualizacoes)
    saida: list[str] = []
    for linha in linhas:
        chave_linha = linha.split("=", 1)[0].strip() if "=" in linha else ""
        if chave_linha in restantes:
            saida.append(f"{chave_linha}={restantes.pop(chave_linha)}")
        else:
            saida.append(linha)
    for chave, valor in restantes.items():
        saida.append(f"{chave}={valor}")

    CAMINHO_ENV.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_ENV.write_text("\n".join(saida).strip() + "\n", encoding="utf-8")


def _testar_chave(chave: str, modelo: str) -> str | None:
    """Faz uma chamada mínima só para confirmar que a chave funciona. Devolve a
    mensagem de erro, ou None se deu certo.

    Vale o custo: salvar uma chave errada só apareceria depois, no meio de uma
    consulta, como falha genérica de IA.
    """
    from pcd_automation.ia_cliente import chamar_openrouter_detalhado

    anterior = os.environ.get("OPENROUTER_API_KEY")
    os.environ["OPENROUTER_API_KEY"] = chave
    try:
        resposta = chamar_openrouter_detalhado(
            [{"role": "user", "content": "responda apenas: ok"}],
            modelo=modelo, max_tokens=20, timeout=45, usar_reserva=False,
        )
        return resposta.erro
    finally:
        if anterior is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = anterior


def _contexto(**extra):
    from pcd_automation.ia_cliente import MODELO_PADRAO, MODELOS_RESERVA

    chave = os.environ.get("OPENROUTER_API_KEY")
    base = {
        "chave_configurada": bool(chave),
        "chave_mascarada": mascarar(chave),
        "modelo_atual": os.environ.get("MAPPA_MODELO") or MODELO_PADRAO,
        "modelos": MODELOS_OFERECIDOS,
        "reservas": MODELOS_RESERVA,
        "caminho_env": str(CAMINHO_ENV),
    }
    base.update(extra)
    return base


@bp_config.route("/", methods=["GET", "POST"])
def configuracoes():
    if request.method == "GET":
        return render_template("configuracoes.html", **_contexto())

    chave_nova = (request.form.get("chave_api") or "").strip()
    modelo = (request.form.get("modelo") or "").strip()
    chave_atual = os.environ.get("OPENROUTER_API_KEY") or ""

    # Campo em branco = manter a chave que já está salva. Sem isso, quem só
    # quisesse trocar o modelo apagaria a chave sem perceber.
    chave = chave_nova or chave_atual
    if not chave:
        return render_template("configuracoes.html", **_contexto(
            erro="Informe a chave da API para o sistema poder usar a IA."))

    if modelo and modelo not in {v for v, _, _ in MODELOS_OFERECIDOS}:
        return render_template("configuracoes.html", **_contexto(
            erro="Modelo não reconhecido."))

    erro_teste = _testar_chave(chave, modelo or _contexto()["modelo_atual"])
    if erro_teste:
        # A mensagem do provedor é mostrada, mas a chave nunca aparece nela:
        # `_tentar_modelo` só cita modelo e status.
        return render_template("configuracoes.html", **_contexto(
            erro=f"A chave não funcionou nesse modelo. Resposta do provedor: {erro_teste}"))

    atualizacoes = {"OPENROUTER_API_KEY": chave}
    if modelo:
        atualizacoes["MAPPA_MODELO"] = modelo
    _gravar_env(atualizacoes)

    # Aplica agora, para valer sem reiniciar o servidor.
    os.environ["OPENROUTER_API_KEY"] = chave
    if modelo:
        os.environ["MAPPA_MODELO"] = modelo
        import pcd_automation.ia_cliente as ia
        ia.MODELO_PADRAO = modelo

    return redirect(url_for(".configuracoes", salvo=1))
