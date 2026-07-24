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

from dataclasses import dataclass, field

from ..ia_cliente import chamar_openrouter
from .indexador import Trecho, obter_indice

PROMPT_SISTEMA = """Você é o Especialista MAPPA, consultor de processos administrativos disciplinares \
da PMMG/CBMMG (MAPPA - Resolução Conjunta 4.220/2012 - e CEDM - Lei Estadual 14.310/2002).

Responda SOMENTE com base nos trechos de referência fornecidos a seguir. Cite o(s) artigo(s) e o \
arquivo de origem sempre que possível. Se os trechos fornecidos não cobrirem a pergunta com \
segurança, diga isso claramente em vez de arriscar um palpite - nunca invente prazo, artigo ou \
regra que não esteja nos trechos. Seja direto e objetivo, como um parecer rápido para um \
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


def buscar_trechos(pergunta: str, top_k: int = 10) -> list[Trecho]:
    return obter_indice().buscar(pergunta, top_k=top_k)


def responder(pergunta: str, top_k: int = 10) -> RespostaConsulta:
    pergunta = (pergunta or "").strip()
    resultado = RespostaConsulta(pergunta=pergunta)
    if not pergunta:
        resultado.erro = "Digite uma pergunta."
        return resultado

    trechos = buscar_trechos(pergunta, top_k=top_k)
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
