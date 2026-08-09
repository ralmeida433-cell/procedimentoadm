"""Redação da conduta individualizada de cada militar, a partir da ocorrência.

A Proposta de Recompensa exige dizer o que CADA militar fez - um texto igual
para todos não individualiza nada e esvazia a proposta. Este módulo recebe a
base da ocorrência (histórico + equipe policial com as funções) e devolve a
conduta de cada um.

Onde o histórico não distingue quem fez o quê, a conduta é derivada da FUNÇÃO
que o militar exerceu na ocorrência (comandante de guarnição, motorista,
patrulheiro, P2...), que é informação real da base - não invenção. Quando nem
isso existe, o texto registra a atuação como conjunta, em vez de atribuir a um
militar um feito que o documento não sustenta: numa proposta de recompensa,
creditar a alguém ação que não praticou é o defeito mais grave possível.
"""
from __future__ import annotations

import json
import re

from .ia_cliente import chamar_openrouter_detalhado

PROMPT_SISTEMA = """Você assessora o proponente de uma Proposta de Recompensa da PMMG. A partir do \
histórico da ocorrência, redija a CONDUTA INDIVIDUALIZADA de cada policial militar da guarnição.

REGRAS:
1. Baseie-se no histórico fornecido. Não invente apreensão, prisão, perseguição, disparo, socorro \
nem qualquer fato que o histórico não mencione.
2. Quando o histórico ATRIBUIR expressamente uma ação a um militar, descreva essa ação para ele.
3. Quando o histórico NÃO distinguir quem fez o quê, derive a conduta da FUNÇÃO informada para \
aquele militar (ex.: comandante de guarnição -> coordenação da equipe e das decisões no local; \
motorista -> condução da viatura no deslocamento e apoio; patrulheiro -> abordagem e busca \
pessoal; P2 -> levantamento de informações). Descreva a participação dele NO FATO NARRADO, sem \
acrescentar acontecimento novo.
4. Se não houver função nem atribuição no histórico, escreva que o militar integrou a guarnição e \
atuou de forma conjunta na ocorrência, e nada além disso.
5. Cada militar recebe um texto DIFERENTE. É proibido repetir o mesmo parágrafo trocando o nome.
6. Redação oficial da PMMG: impessoal, objetiva, sem exagero elogioso; horas no padrão "21h30min"; \
sem "o mesmo/a mesma" como pronome; sem gerundismo. Um parágrafo por militar, entre 2 e 5 linhas.
7. Não repita a qualificação (nome, posto, matrícula) no início do texto - ela já consta do \
documento. Comece pela ação (ex.: "Coordenou o isolamento da área...").

Responda SOMENTE com um objeto JSON válido, sem markdown, no formato:
{"condutas": [{"indice": 0, "conduta": "..."}], "observacoes": ["..."]}
onde "indice" é a posição do militar na lista enviada, começando em 0."""


def _extrair_json(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip(), flags=re.IGNORECASE)
    return json.loads(texto)


def _descrever_militares(militares: list[dict]) -> str:
    linhas = []
    for i, m in enumerate(militares):
        funcao = (m.get("funcao") or "").strip() or "função não informada"
        linhas.append(
            f"[{i}] {m.get('posto') or ''} {m.get('nome') or '(sem nome)'} "
            f"(nº {m.get('numero') or 's/n'}) - função na ocorrência: {funcao}"
        )
    return "\n".join(linhas)


def redigir_condutas(ocorrencia: dict, militares: list[dict]) -> tuple[list[str], list[str]]:
    """Devolve (condutas_na_ordem_dos_militares, observacoes).

    Em caso de falha da IA, devolve textos derivados só da função - o documento
    sai preenchido de qualquer jeito, e a observação avisa o que aconteceu.
    """
    if not militares:
        return [], []

    oc = ocorrencia.get("ocorrencia") or {}
    historico = (oc.get("historico_sucinto") or "").strip()
    if not historico:
        return (
            [_conduta_de_reserva(m) for m in militares],
            ["A ocorrência não tem histórico registrado, então a conduta de cada militar foi "
             "derivada apenas da função informada. Revise antes de assinar."],
        )

    contexto = [f"Histórico da ocorrência: {historico}"]
    for rotulo, chave in (("Natureza", "natureza"), ("Local", "local"),
                          ("Município", "municipio"), ("Data", "data_fato"), ("Hora", "hora_fato")):
        if oc.get(chave):
            contexto.append(f"{rotulo}: {oc[chave]}")
    bens = ocorrencia.get("bens_envolvidos") or {}
    for grupo, itens in bens.items():
        if itens:
            contexto.append(f"{grupo.capitalize()}: {'; '.join(str(i) for i in itens)}")

    resposta = chamar_openrouter_detalhado(
        [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": "\n".join(contexto)
             + f"\n\nMilitares da guarnição:\n{_descrever_militares(militares)}"},
        ],
        max_tokens=4000,
        timeout=180,
        json_obrigatorio=True,
    )

    if resposta.erro:
        return (
            [_conduta_de_reserva(m) for m in militares],
            [f"Não foi possível redigir as condutas com IA ({resposta.erro}). O documento saiu com "
             "a conduta derivada da função de cada militar - revise e complete antes de assinar."],
        )

    try:
        dados = _extrair_json(resposta.conteudo)
    except json.JSONDecodeError:
        return (
            [_conduta_de_reserva(m) for m in militares],
            ["A IA não devolveu um JSON válido ao redigir as condutas. O documento saiu com a "
             "conduta derivada da função de cada militar - revise antes de assinar."],
        )

    condutas = [""] * len(militares)
    for item in dados.get("condutas") or []:
        if not isinstance(item, dict):
            continue
        try:
            indice = int(item.get("indice"))
        except (TypeError, ValueError):
            continue
        texto = " ".join(str(item.get("conduta") or "").split())
        if 0 <= indice < len(militares) and texto:
            condutas[indice] = texto

    observacoes = [str(o) for o in (dados.get("observacoes") or [])]
    faltando = [i for i, c in enumerate(condutas) if not c]
    for i in faltando:
        condutas[i] = _conduta_de_reserva(militares[i])
    if faltando:
        nomes = ", ".join(militares[i].get("nome") or f"militar {i+1}" for i in faltando)
        observacoes.append(
            f"A IA não redigiu a conduta de: {nomes}. Para esses, o texto foi derivado da função "
            "informada - revise com atenção."
        )
    if resposta.usou_reserva:
        observacoes.append(
            f"O modelo principal estava indisponível; as condutas foram redigidas pelo modelo "
            f"reserva {resposta.modelo_usado}, que é menor. Revise com atenção redobrada."
        )
    return condutas, observacoes


def _conduta_de_reserva(militar: dict) -> str:
    """Texto mínimo quando a IA não pôde redigir: derivado da função, sem
    afirmar nenhum feito específico."""
    funcao = (militar.get("funcao") or "").strip()
    if funcao:
        return (
            f"Integrou a guarnição empenhada na ocorrência, atuando na função de {funcao.lower()}. "
            "[COMPLETAR: detalhar a atuação individual conforme o histórico]"
        )
    return (
        "Integrou a guarnição empenhada na ocorrência, atuando de forma conjunta com os demais "
        "militares. [COMPLETAR: detalhar a atuação individual conforme o histórico]"
    )
