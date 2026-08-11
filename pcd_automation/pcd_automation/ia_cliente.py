"""Cliente mínimo para a API do OpenRouter (tier gratuito), compartilhado
entre os módulos que geram texto via IA: consulta ao MAPPA (`rag.consulta`),
o motor de extração de documentos (`extracao`), a sugestão de tipificação
(`sugestao_fato`) e a análise de REDS (`webapp.modulos_extra`).

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

Nota 3: modelos gratuitos rodam em capacidade COMPARTILHADA e falham em
horário de pico com erros temporários do provedor ("ResourceExhausted:
Worker local total request limit reached", 429, 502/503). Isso não é defeito
da chave nem do texto enviado: é fila cheia. Por isso as chamadas caem
automaticamente para modelos reserva (ver MODELOS_RESERVA) antes de desistir.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import requests

MODELO_PADRAO = os.environ.get("MAPPA_MODELO", "nvidia/nemotron-3-ultra-550b-a55b:free")
URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

# Modelos usados quando o padrão está indisponível por capacidade. Ordem =
# preferência. Escolhidos por (a) responderem JSON estruturado corretamente e
# (b) contexto grande o bastante para um REDS ou um processo inteiro (262k).
# O primeiro é de outro provedor de propósito: quando a Nvidia está lotada,
# outro modelo Nvidia tende a estar lotado também.
# Ajustável por MAPPA_MODELOS_RESERVA (lista separada por vírgula) no .env.
_RESERVA_PADRAO = [
    "poolside/laguna-s-2.1:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-26b-a4b-it:free",
]
MODELOS_RESERVA = [
    m.strip() for m in (os.environ.get("MAPPA_MODELOS_RESERVA") or ",".join(_RESERVA_PADRAO)).split(",") if m.strip()
]

# Falhas que valem tentar em outro modelo (capacidade/indisponibilidade
# momentânea), em oposição a erro de chave, de cota da conta ou do pedido.
_PADRAO_TEMPORARIO = re.compile(
    r"resourceexhausted|worker local total request limit|too many requests|rate.?limit"
    r"|overloaded|capacity|temporarily unavailable|timed? ?out|bad gateway|service unavailable"
    r"|\b(429|502|503|504)\b",
    re.IGNORECASE,
)


@dataclass
class RespostaIA:
    conteudo: str | None = None
    erro: str | None = None
    modelo_usado: str | None = None
    usou_reserva: bool = False


def chave_api_openrouter() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


def _tentar_modelo(
    mensagens: list[dict], modelo: str, chave_api: str, *,
    max_tokens: int, timeout: int, json_obrigatorio: bool,
) -> tuple[str | None, str | None, bool]:
    """Uma tentativa em um modelo. Retorna (conteúdo, erro, erro_temporário)."""
    # O "reasoning" fica desligado SEMPRE, não só quando se pede JSON: o modelo
    # padrão é de raciocínio e, em respostas de texto corrido, chegou a devolver
    # a cadeia de pensamento em inglês no lugar da resposta ("The user is asking
    # if they can conduct..."). Num assistente que o encarregado consulta para
    # redigir documento, isso é resposta inutilizável.
    corpo = {
        "model": modelo,
        "messages": mensagens,
        "max_tokens": max_tokens,
        "reasoning": {"enabled": False},
    }
    if json_obrigatorio:
        corpo["response_format"] = {"type": "json_object"}

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
    except requests.Timeout:
        return None, f"Tempo esgotado ao consultar a IA ({modelo}).", True
    except Exception as exc:
        return None, f"Erro ao consultar a IA: {exc}", True

    if resposta_http.status_code != 200:
        temporario = resposta_http.status_code in (408, 409, 429, 500, 502, 503, 504)
        # A OpenRouter devolve 404 em dois casos MUITO diferentes: o modelo não
        # existe (permanente) ou o provedor upstream falhou naquele instante
        # ("Provider returned error" - transitório). Sem separar os dois, uma
        # falha passageira do provedor derrubava a consulta inteira sem sequer
        # tentar os modelos reserva, que foi o que aconteceu em uso real.
        if resposta_http.status_code == 404:
            corpo_erro = resposta_http.text.lower()
            temporario = "not a valid model" not in corpo_erro and "no endpoints" not in corpo_erro
        return None, f"A IA retornou erro HTTP {resposta_http.status_code} ({modelo}): {resposta_http.text[:200]}", temporario

    try:
        dados = resposta_http.json()
    except ValueError:
        return None, f"Resposta da IA não é JSON ({modelo}): {resposta_http.text[:200]}", True

    # A OpenRouter devolve erro do provedor no corpo, com HTTP 200 - é assim
    # que chega o estouro de capacidade dos modelos gratuitos.
    if "error" in dados:
        mensagem = str(dados["error"].get("message", dados["error"]) if isinstance(dados["error"], dict) else dados["error"])
        return None, f"A IA retornou um erro ({modelo}): {mensagem}", bool(_PADRAO_TEMPORARIO.search(mensagem))
    if not dados.get("choices"):
        return None, f"Resposta inesperada da IA ({modelo}, sem 'choices'): {str(dados)[:200]}", True

    conteudo = (dados["choices"][0]["message"]["content"] or "").strip()
    if not conteudo:
        return None, f"A IA não retornou texto ({modelo}) - pode ter sido bloqueada por segurança.", False
    return conteudo, None, False


def chamar_openrouter_detalhado(
    mensagens: list[dict],
    *,
    max_tokens: int = 1024,
    modelo: str | None = None,
    timeout: int = 60,
    json_obrigatorio: bool = False,
    usar_reserva: bool = True,
) -> RespostaIA:
    """Chama o chat completions da OpenRouter, caindo para modelos reserva
    quando o principal está indisponível por capacidade.

    Diferente de `chamar_openrouter`, informa QUAL modelo respondeu - útil
    para avisar na tela quando o texto não veio do modelo principal (os
    reservas são menores e a redação sai mais simples).

    `json_obrigatorio=True` pede à OpenRouter para forçar saída em JSON
    (response_format) e desliga o "reasoning" do modelo quando suportado -
    sem isso, modelos de raciocínio despejam a cadeia de pensamento em vez
    de responder só o JSON pedido no prompt.
    """
    chave_api = chave_api_openrouter()
    if not chave_api:
        return RespostaIA(erro=(
            "OPENROUTER_API_KEY não configurada. Configure a variável de ambiente para habilitar a IA "
            "(gratuita via OpenRouter, sem cartão - openrouter.ai/keys)."
        ))

    principal = modelo or MODELO_PADRAO
    fila = [principal] + ([m for m in MODELOS_RESERVA if m != principal] if usar_reserva else [])

    erros: list[str] = []
    for tentativa, modelo_atual in enumerate(fila):
        conteudo, erro, temporario = _tentar_modelo(
            mensagens, modelo_atual, chave_api,
            max_tokens=max_tokens, timeout=timeout, json_obrigatorio=json_obrigatorio,
        )
        if conteudo is not None:
            return RespostaIA(conteudo=conteudo, modelo_usado=modelo_atual, usou_reserva=tentativa > 0)
        erros.append(erro or "erro desconhecido")

        # Falha de credencial vale para todos os modelos - insistir só gasta
        # tempo e repete o mesmo erro.
        if re.search(r"HTTP 40[13]\b", erro or ""):
            break
        # Fora isso, seguimos para o próximo modelo mesmo em erro "permanente":
        # um 400 costuma ser recusa DAQUELE modelo (parâmetro não suportado,
        # limite próprio), não do pedido em si. Parar a fila por causa de um
        # modelo deixava o usuário sem resposta com outros dois disponíveis -
        # foi o que aconteceu em uso real, com a mensagem "1 modelo reserva,
        # sem sucesso" enquanto restavam dois intactos.
        if not temporario and tentativa == 0 and modelo is not None:
            # Exceção: modelo pedido explicitamente pelo chamador. Aí o erro é
            # sobre a escolha dele, e trocar por outro seria ignorar o pedido.
            break

    detalhe = erros[0] if erros else "erro desconhecido"
    # Só menciona os reservas se eles foram MESMO tentados: quando a fila para
    # cedo (credencial inválida, ou modelo escolhido pelo chamador), o laço não
    # chega neles,
    # e dizer que tentou 3 modelos mandaria o usuário procurar defeito onde
    # não há.
    reservas_tentadas = len(erros) - 1
    if reservas_tentadas > 0:
        detalhe += (
            f" | Também {'foi tentado' if reservas_tentadas == 1 else 'foram tentados'} "
            f"{reservas_tentadas} modelo(s) reserva, sem sucesso. Os modelos gratuitos rodam em "
            "capacidade compartilhada e lotam em horário de pico - tente de novo em alguns minutos."
        )
    return RespostaIA(erro=detalhe)


def chamar_openrouter(
    mensagens: list[dict],
    *,
    max_tokens: int = 1024,
    modelo: str | None = None,
    timeout: int = 60,
    json_obrigatorio: bool = False,
) -> tuple[str | None, str | None]:
    """Retorna (conteúdo, erro) - exatamente um dos dois é None. Mantém a
    assinatura antiga; use `chamar_openrouter_detalhado` para saber qual
    modelo respondeu."""
    resposta = chamar_openrouter_detalhado(
        mensagens, max_tokens=max_tokens, modelo=modelo, timeout=timeout,
        json_obrigatorio=json_obrigatorio,
    )
    return resposta.conteudo, resposta.erro
