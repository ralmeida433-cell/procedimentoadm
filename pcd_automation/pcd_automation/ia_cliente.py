"""Cliente mínimo para a API do OpenRouter (tier gratuito), compartilhado
entre os módulos que geram texto via IA: consulta ao MAPPA (`rag.consulta`)
e o motor de extração de documentos (`extracao`).

Nota: o motor de geração já foi trocado do Google Gemini para o OpenRouter
porque, a partir de meados de 2026, o Google passou a emitir por padrão
chaves no novo formato "Auth key" (prefixo "AQ.") que retornam erro 401
(ACCESS_TOKEN_TYPE_UNSUPPORTED) de forma generalizada - problema conhecido,
do lado do Google, sem previsão de correção.

Nota 2: a lista de modelos ":free" da OpenRouter muda com frequência -
modelos são removidos ou viram pagos sem aviso (ex.: o antigo padrão
"meta-llama/llama-3.3-70b-instruct:free" foi descontinuado). Se MODELO_PADRAO
passar a dar erro 404, veja a lista atual em
https://openrouter.ai/models?max_price=0 e ajuste via MAPPA_MODELO no .env.
"""
from __future__ import annotations

import os

import requests

MODELO_PADRAO = os.environ.get("MAPPA_MODELO", "nvidia/nemotron-3-ultra-550b-a55b:free")
URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"


def chave_api_openrouter() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


def chamar_openrouter(
    mensagens: list[dict],
    *,
    max_tokens: int = 1024,
    modelo: str | None = None,
    timeout: int = 60,
    json_obrigatorio: bool = False,
) -> tuple[str | None, str | None]:
    """Chama o chat completions da OpenRouter. Retorna (conteúdo, erro) -
    exatamente um dos dois é None.

    `json_obrigatorio=True` pede à OpenRouter para forçar saída em JSON
    (response_format) e desliga o "reasoning" do modelo quando suportado -
    sem isso, modelos de raciocínio despejam a cadeia de pensamento em vez
    de responder só o JSON pedido no prompt."""
    chave_api = chave_api_openrouter()
    if not chave_api:
        return None, (
            "OPENROUTER_API_KEY não configurada. Configure a variável de ambiente para habilitar a IA "
            "(gratuita via OpenRouter, sem cartão - openrouter.ai/keys)."
        )

    corpo = {"model": modelo or MODELO_PADRAO, "messages": mensagens, "max_tokens": max_tokens}
    if json_obrigatorio:
        corpo["response_format"] = {"type": "json_object"}
        corpo["reasoning"] = {"enabled": False}

    try:
        resposta_http = requests.post(
            URL_OPENROUTER,
            headers={
                "Authorization": f"Bearer {chave_api}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/pcd-automation",
                "X-Title": "Assistente de PCD - PMMG",
            },
            json=corpo,
            timeout=timeout,
        )
        resposta_http.raise_for_status()
        dados = resposta_http.json()
        if "error" in dados:
            return None, f"A IA retornou um erro: {dados['error'].get('message', dados['error'])}"
        if not dados.get("choices"):
            return None, f"Resposta inesperada da IA (sem 'choices'): {str(dados)[:300]}"
        conteudo = (dados["choices"][0]["message"]["content"] or "").strip()
        if not conteudo:
            return None, "A IA não retornou texto (pode ter sido bloqueada por segurança)."
        return conteudo, None
    except Exception as exc:
        return None, f"Erro ao consultar a IA: {exc}"
