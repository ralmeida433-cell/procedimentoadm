"""Consulta ao especialista MAPPA (RAG) para o encarregado.

Busca os trechos mais relevantes nas referências do MAPPA (`indexador.py`)
e usa a API do OpenRouter (`pcd_automation.ia_cliente`) para redigir uma
resposta fundamentada, no mesmo espírito do modo CONSULTOR da skill
`especialista-mappa`: nunca responde sem se basear nos trechos
recuperados, e avisa quando as referências não cobrem a pergunta com
segurança.

Sem OPENROUTER_API_KEY configurada, a consulta ainda funciona - só não gera
a resposta em linguagem natural, mostrando apenas os trechos encontrados.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..ia_cliente import chamar_openrouter
from .indexador import Trecho, obter_indice

PROMPT_SISTEMA = """Você é o Especialista MAPPA, consultor de processos administrativos disciplinares \
da PMMG/CBMMG (MAPPA - Resolução Conjunta 4.220/2012 - e CEDM - Lei Estadual 14.310/2002).

Responda SOMENTE com base nos trechos de referência fornecidos a seguir. Cite o(s) artigo(s) e o \
arquivo de origem sempre que possível. Se os trechos fornecidos não cobrirem a pergunta com \
segurança, diga isso claramente em vez de arriscar um palpite - nunca invente prazo, artigo ou \
regra que não esteja nos trechos.

Ao dizer que NÃO tem a resposta, não sugira número de artigo nem diploma legal de memória. Diga o \
que falta ("o prazo não consta dos trechos recuperados") e pare aí. Apontar "consulte o art. X da \
Lei Y" sem ter o texto à vista é pior do que não responder: o encarregado toma como confirmação e \
vai citar isso no documento. Cada diploma tem numeração própria - o mesmo número de artigo existe \
no CPM, no CEDM e no MAPPA com conteúdos diferentes, então nomeie a lei apenas quando ela estiver \
identificada no trecho que você está citando. Seja direto e objetivo, como um parecer rápido para um \
encarregado no meio da elaboração de um processo administrativo.

Os trechos recuperados podem vir de processos diferentes (PCD, SAD, PAD, PADS, PAE etc.) que têm \
regras parecidas mas não idênticas - confira sempre a QUAL processo cada trecho se refere (pelo \
nome do arquivo e pelo conteúdo) antes de responder, e aplique apenas a regra do processo que o \
encarregado perguntou. Se dois trechos parecerem se contradizer, prefira o texto do capítulo \
específico do processo em questão (arquivo "capNN-...") sobre tabelas-resumo, e mencione a \
divergência ao encarregado em vez de escondê-la.

Quando redigir qualquer trecho de documento, siga a redação oficial da PMMG: texto impessoal e \
objetivo, sem juízo de valor; não use "o mesmo/a mesma" como pronome (ex.: "conduziu o mesmo" → \
"conduziu-o"); sem gerundismo ("vou estar enviando" → "enviarei"); horas no padrão "19h30min" (nunca \
"19:30" nem "19hs"); "Vossa Senhoria" para autoridades em geral e "Vossa Excelência" só para o \
Comandante-Geral e o Chefe do Gabinete Militar do Governador (nunca "Ilustríssimo/Digníssimo"); \
vocativo "Senhor [Posto] [Nome]," sem abreviar; abreviaturas de posto sem ponto (Cel, Ten Cel, Maj, \
Cap, 1º Ten, Subten, 1º Sgt, Cb); e, na primeira menção de uma sigla, escreva o termo por extenso \
seguido da sigla entre parênteses."""


@dataclass
class RespostaConsulta:
    pergunta: str
    trechos: list[Trecho] = field(default_factory=list)
    resposta: str | None = None
    erro: str | None = None


def _formatar_trechos(trechos: list[Trecho]) -> str:
    partes = [f"[Trecho {i} - {t.arquivo}]\n{t.texto}" for i, t in enumerate(trechos, start=1)]
    return "\n\n---\n\n".join(partes)


PROMPT_TERMOS = """Você traduz a descrição de um fato para os TERMOS TÉCNICOS que a lei usa, para \
permitir a busca em códigos e regulamentos militares (CPM, CEDM, MAPPA, RGPM).

A busca é literal: ela só encontra o que está escrito na lei. Quem descreve "tirou a farda e sujou" \
não acha nada, porque o Código escreve "despojar-se de uniforme por menosprezo ou vilipêndio".

Devolva os termos que provavelmente aparecem no TEXTO LEGAL sobre esse fato: verbos na forma da lei, \
substantivos técnicos e sinônimos jurídicos. Inclua também o nome do instituto, se reconhecer.

PROIBIDO: citar número de artigo, inciso ou lei. Você não sabe a numeração - devolve só palavras \
para a busca. Nada de explicação.

Responda SOMENTE com um objeto JSON: {"termos": ["...", "..."]}   (no máximo 12 termos)"""


def expandir_consulta(pergunta: str) -> tuple[str, list[str]]:
    """Acrescenta à pergunta os termos técnicos que a lei usaria.

    O índice é BM25, ou seja, casamento de palavras. Uma pergunta em linguagem
    corrente ("tirou a farda e defecou nela") não casa com o texto legal
    ("despojar-se de uniforme, por menosprêzo ou vilipêndio") e a busca volta
    vazia - foi o que aconteceu num caso real, em que o dispositivo estava
    indexado e mesmo assim não foi encontrado.

    A tradução gera apenas PALAVRAS DE BUSCA. Number de artigo continua vindo
    exclusivamente do trecho recuperado: expandir a busca aumenta o alcance sem
    abrir espaço para o modelo citar de memória.

    Devolve (consulta_expandida, termos_acrescentados). Se a expansão falhar,
    devolve a pergunta original - a busca segue como antes.
    """
    pergunta = (pergunta or "").strip()
    if len(pergunta) < 10:
        return pergunta, []
    conteudo, erro = chamar_openrouter(
        [{"role": "system", "content": PROMPT_TERMOS}, {"role": "user", "content": pergunta}],
        max_tokens=300,
        timeout=45,
        json_obrigatorio=True,
    )
    if erro or not conteudo:
        return pergunta, []
    try:
        bruto = re.sub(r"^```(?:json)?\s*|\s*```$", "", conteudo.strip(), flags=re.IGNORECASE)
        termos = [str(t).strip() for t in (json.loads(bruto).get("termos") or []) if str(t).strip()]
    except (json.JSONDecodeError, AttributeError):
        return pergunta, []
    # Descarta o que vier com número de artigo, por segurança.
    termos = [t for t in termos if not re.search(r"art\.?\s*\d|\bn[ºo°]\s*\d", t, re.IGNORECASE)][:12]
    if not termos:
        return pergunta, []
    return pergunta + " " + " ".join(termos), termos


def buscar_trechos(pergunta: str, top_k: int = 10, expandir: bool = False) -> list[Trecho]:
    consulta = expandir_consulta(pergunta)[0] if expandir else pergunta
    return obter_indice().buscar(consulta, top_k=top_k)


def _consulta_de_busca(mensagens: list[dict], janela: int = 3) -> str:
    """Monta o texto usado para BUSCAR os trechos, juntando as últimas
    perguntas do usuário.

    Numa conversa, a pergunta de acompanhamento costuma ser curta demais para
    achar qualquer coisa sozinha ("e o prazo?", "e se for grave?"). Buscar só
    com ela devolveria trecho irrelevante e a resposta sairia errada. Juntando
    as perguntas anteriores, a busca mantém o assunto.
    """
    perguntas = [
        str(m.get("texto") or "").strip()
        for m in mensagens
        if m.get("papel") == "usuario" and str(m.get("texto") or "").strip()
    ]
    return " ".join(perguntas[-janela:])


def responder_conversa(mensagens: list[dict], top_k: int = 10) -> RespostaConsulta:
    """Responde mantendo o contexto da conversa.

    `mensagens` é a conversa inteira, em ordem: [{"papel": "usuario"|"assistente",
    "texto": "..."}]. A última precisa ser do usuário.
    """
    ultima = ""
    for m in reversed(mensagens or []):
        if m.get("papel") == "usuario":
            ultima = str(m.get("texto") or "").strip()
            break

    resultado = RespostaConsulta(pergunta=ultima)
    if not ultima:
        resultado.erro = "Digite uma pergunta."
        return resultado

    trechos = buscar_trechos(_consulta_de_busca(mensagens), top_k=top_k, expandir=True)
    resultado.trechos = trechos
    if not trechos:
        resultado.erro = (
            "Nenhum trecho relevante foi encontrado nas referências do MAPPA para essa pergunta."
        )
        return resultado

    historico = [
        {"role": "user" if m.get("papel") == "usuario" else "assistant",
         "content": str(m.get("texto") or "")}
        for m in mensagens
        if str(m.get("texto") or "").strip()
    ]
    # Os trechos entram logo antes da última pergunta, para o modelo respondê-la
    # olhando as referências recuperadas AGORA, e não as de uma pergunta anterior.
    conteudo_final = historico[-1]["content"]
    historico[-1] = {
        "role": "user",
        "content": (
            f"Trechos de referência recuperados para esta pergunta:\n\n{_formatar_trechos(trechos)}\n\n"
            f"Pergunta do encarregado: {conteudo_final}"
        ),
    }

    resposta, erro = chamar_openrouter(
        [{"role": "system", "content": PROMPT_SISTEMA}] + historico,
        max_tokens=1024,
    )
    resultado.resposta = resposta
    resultado.erro = erro
    return resultado


def responder(pergunta: str, top_k: int = 10) -> RespostaConsulta:
    pergunta = (pergunta or "").strip()
    resultado = RespostaConsulta(pergunta=pergunta)
    if not pergunta:
        resultado.erro = "Digite uma pergunta."
        return resultado

    trechos = buscar_trechos(pergunta, top_k=top_k, expandir=True)
    resultado.trechos = trechos
    if not trechos:
        resultado.erro = "Nenhum trecho relevante foi encontrado nas referências do MAPPA para essa pergunta."
        return resultado

    resposta, erro = chamar_openrouter(
        [
            {"role": "system", "content": PROMPT_SISTEMA},
            {
                "role": "user",
                "content": (
                    f"Trechos de referência:\n\n{_formatar_trechos(trechos)}\n\n"
                    f"Pergunta do encarregado: {pergunta}"
                ),
            },
        ],
        max_tokens=1024,
    )
    resultado.resposta = resposta
    resultado.erro = erro
    return resultado
