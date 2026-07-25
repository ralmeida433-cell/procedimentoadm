"""Análise assistida do resumo do fato (redação + tipificação sugerida).

O encarregado descreve o fato como quiser ("faltou ao serviço", "chegou
atrasado na formatura") e este módulo devolve:

1. o mesmo fato reescrito na redação oficial exigida pelos modelos .docx
   (particípio, impessoal, sem juízo de valor);
2. a(s) transgressão(ões) do CEDM compatíveis, com o texto literal do inciso
   e a justificativa.

Duas travas, porque tipificar é ato do encarregado e não do sistema:

- a IA escolhe apenas entre as transgressões recuperadas de
  `transgressoes_cedm` (conjunto fechado, texto literal da lei). Se devolver
  artigo/inciso fora dessa lista, a sugestão é descartada em vez de exibida -
  é o que impede citar dispositivo inexistente num documento disciplinar;
- o resultado é SUGESTÃO. Quem grava em `resumo_fato` e `tipificacao_cedm` é o
  encarregado, ao conferir o texto legal e aceitar.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .ia_cliente import chamar_openrouter
from .redacao import validar_texto
from .transgressoes_cedm import Transgressao, buscar_candidatas, por_tipificacao

# Quanto da interpretação oficial de cada inciso vai no prompt. O suficiente
# para a IA captar o alcance do dispositivo sem estourar o contexto com 46
# comentários inteiros.
_LIMITE_COMENTARIO = 900

PROMPT_SISTEMA = """Você assessora o encarregado de um Processo de Comunicação Disciplinar (PCD) da \
PMMG/CBMMG na redação do resumo do fato e na indicação da transgressão disciplinar do CEDM \
(Lei Estadual 14.310/2002).

TAREFA 1 - Reescrever o fato descrito pelo encarregado na redação oficial da PMMG, respeitando \
rigorosamente estas restrições, porque o texto será inserido no meio de frases já impressas nos \
modelos oficiais ("...por volta das 8h20min, teria o comunicado ___." e "...o militar supracitado, \
___."):
- comece por VERBO NO PARTICÍPIO, em letra minúscula (ex.: "deixado de comparecer...", "chegado \
atrasado...", "utilizado...");
- NÃO inicie com maiúscula, NÃO termine com ponto, NÃO repita data, hora, cidade nem o nome/posto do \
militar (esses dados já constam da frase e de outros campos);
- texto impessoal e objetivo, descrevendo só a CONDUTA, sem juízo de valor, sem adjetivar e sem \
concluir culpa (o fato é apurado, não julgado);
- use "teria"/"em tese" apenas se necessário - a frase do modelo já traz "teria";
- proibido: "o mesmo"/"a mesma" como pronome, gerundismo ("vou estar enviando"), horas com \
dois-pontos ou "hs" (use "8h20min");
- não invente circunstância que o encarregado não informou (se ele não disse que houve justificativa, \
não escreva que não houve).

TAREFA 2 - Indicar a transgressão disciplinar aplicável ESCOLHENDO EXCLUSIVAMENTE entre os incisos da \
lista fornecida. É proibido citar artigo ou inciso que não esteja na lista, mesmo que você acredite \
que exista outro mais adequado. Se nenhum da lista servir, devolva "tipificacoes": [] e explique em \
"observacoes". Indique no máximo 3, da mais adequada para a menos adequada, e para cada uma diga por \
que a conduta se encaixa no texto do inciso.

TAREFA 3 - Listar em "dados_faltantes" o que o encarregado ainda precisa esclarecer para sustentar \
essa tipificação (ex.: se a falta ao serviço estava prevista em escala antecipada, se houve \
justificativa apresentada), e em "observacoes" qualquer ressalva relevante.

Responda SOMENTE com um objeto JSON válido, sem markdown, exatamente neste formato:
{"resumo_fato": "...", "tipificacoes": [{"artigo": 13, "inciso": "XX", "justificativa": "...", \
"confianca": "alta|media|baixa"}], "dados_faltantes": ["..."], "observacoes": ["..."]}
"""


@dataclass
class TipificacaoSugerida:
    transgressao: Transgressao
    justificativa: str
    confianca: str

    @property
    def tipificacao(self) -> str:
        return self.transgressao.tipificacao


@dataclass
class ResultadoSugestao:
    descricao_original: str
    resumo_fato: str | None = None
    tipificacoes: list[TipificacaoSugerida] = field(default_factory=list)
    dados_faltantes: list[str] = field(default_factory=list)
    observacoes: list[str] = field(default_factory=list)
    avisos_redacao: list[str] = field(default_factory=list)
    candidatas: list[Transgressao] = field(default_factory=list)
    erro: str | None = None


def _formatar_candidatas(candidatas: list[Transgressao]) -> str:
    partes = []
    for t in candidatas:
        partes.append(
            f"- art. {t.artigo}, inciso {t.inciso} (natureza {t.natureza}): \"{t.texto}\"\n"
            f"  Interpretação oficial (ICCPM/BM 01/14): {t.comentario[:_LIMITE_COMENTARIO]}"
        )
    return "\n".join(partes)


def _normalizar_resumo(texto: str) -> str:
    """Ajusta o texto da IA ao encaixe exigido pelos modelos: sem ponto final e
    sem maiúscula inicial (é continuação de uma frase já impressa)."""
    texto = " ".join((texto or "").split()).strip().rstrip(".")
    if texto and not texto.split()[0].isupper():
        texto = texto[0].lower() + texto[1:]
    return texto


def _extrair_json(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip(), flags=re.IGNORECASE)
    return json.loads(texto)


def _ler_tipificacoes(bruto, candidatas: list[Transgressao], resultado: ResultadoSugestao) -> None:
    """Converte as tipificações devolvidas pela IA, descartando qualquer uma
    que não esteja no conjunto fechado de candidatas."""
    permitidas = {(t.artigo, t.inciso) for t in candidatas}
    for item in bruto or []:
        if not isinstance(item, dict):
            continue
        try:
            artigo = int(item.get("artigo"))
        except (TypeError, ValueError):
            continue
        inciso = str(item.get("inciso") or "").strip().upper()
        transgressao = por_tipificacao(artigo, inciso)
        if transgressao is None or (artigo, inciso) not in permitidas:
            resultado.observacoes.append(
                f"A IA sugeriu \"art. {artigo}, inciso {inciso or '?'}\", que não consta da lista de "
                "incisos analisados - sugestão descartada para não citar dispositivo indevido."
            )
            continue
        resultado.tipificacoes.append(
            TipificacaoSugerida(
                transgressao=transgressao,
                justificativa=" ".join(str(item.get("justificativa") or "").split()),
                confianca=str(item.get("confianca") or "").strip().lower() or "não informada",
            )
        )


def analisar(descricao: str, limite_candidatas: int = 8) -> ResultadoSugestao:
    """Analisa a descrição livre do fato e devolve resumo reescrito +
    tipificações sugeridas. Sem chave de IA configurada, ainda devolve as
    transgressões candidatas (triagem lexical), que já orientam o encarregado."""
    descricao = (descricao or "").strip()
    resultado = ResultadoSugestao(descricao_original=descricao)
    if len(descricao) < 5:
        resultado.erro = "Descreva o fato em algumas palavras (ex.: 'faltou ao serviço da escala do dia')."
        return resultado

    candidatas = buscar_candidatas(descricao, limite=limite_candidatas)
    resultado.candidatas = candidatas
    if not candidatas:
        resultado.erro = (
            "Nenhuma transgressão do CEDM foi encontrada para essa descrição. Descreva a conduta com "
            "outras palavras (ex.: 'faltou ao serviço', 'chegou atrasado', 'dormiu em serviço')."
        )
        return resultado

    conteudo, erro = chamar_openrouter(
        [
            {"role": "system", "content": PROMPT_SISTEMA},
            {
                "role": "user",
                "content": (
                    f"Fato descrito pelo encarregado:\n{descricao}\n\n"
                    f"Incisos do CEDM entre os quais você DEVE escolher:\n{_formatar_candidatas(candidatas)}"
                ),
            },
        ],
        max_tokens=2000,
        timeout=120,
        json_obrigatorio=True,
    )
    if erro:
        resultado.erro = erro
        return resultado

    try:
        dados = _extrair_json(conteudo)
    except json.JSONDecodeError:
        resultado.erro = f"A IA não retornou um JSON válido. Resposta bruta: {conteudo[:400]}"
        return resultado

    resultado.resumo_fato = _normalizar_resumo(dados.get("resumo_fato") or "") or None
    resultado.dados_faltantes = [str(x) for x in (dados.get("dados_faltantes") or [])]
    resultado.observacoes = [str(x) for x in (dados.get("observacoes") or [])]
    _ler_tipificacoes(dados.get("tipificacoes"), candidatas, resultado)

    if resultado.resumo_fato:
        resultado.avisos_redacao = validar_texto(resultado.resumo_fato)

    if any(t.transgressao.natureza == "grave" for t in resultado.tipificacoes):
        resultado.observacoes.append(
            "Transgressão de natureza grave: continua sendo apurada em PCD, mas se o militar estiver "
            "no conceito \"C\" ou o fato afetar a honra pessoal, o pundonor militar ou o decoro da "
            "classe, pode caber PAD/PADS (art. 64 ou art. 34 do CEDM). A definição do processo é da "
            "autoridade instauradora."
        )

    return resultado
