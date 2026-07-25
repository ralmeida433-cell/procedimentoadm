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

Faça as tarefas nesta ordem: escolha primeiro a transgressão (TAREFA 2) e só então redija o resumo \
(TAREFA 1), para que a descrição do fato e a tipificação usem o mesmo vocabulário.

TAREFA 1 - Reescrever o fato descrito pelo encarregado na redação oficial da PMMG. Esse texto vai \
DIRETO para o Despacho de Instauração, para os Termos de Vista e para o Relatório do Encarregado - \
tem de estar pronto para assinatura, não pode ser um eco da anotação informal que o encarregado \
digitou.

Encaixe (o texto entra no meio de frases já impressas nos modelos: "...por volta das 8h20min, teria o \
comunicado ___." e "...o militar supracitado, ___."):
- comece por VERBO NO PARTICÍPIO, em letra minúscula ("deixado de comparecer...", "chegado \
atrasado...", "utilizado...");
- NÃO inicie com maiúscula, NÃO termine com ponto, NÃO repita data, hora, cidade nem o nome/posto do \
militar (já constam da frase e de outros campos);
- não use "teria"/"em tese" - a frase do modelo já traz "teria".

Qualidade da redação:
- troque a linguagem coloquial pela terminologia oficial ("faltou" -> "deixado de comparecer"; \
"brigou com" -> "envolvido em desentendimento com"; "xingou" -> "dirigido palavras ofensivas a");
- descreva a conduta com as palavras do inciso que você escolheu na TAREFA 2, para que o fato e a \
tipificação se sustentem mutuamente;
- uma frase completa e articulada, não um fragmento telegráfico: conduta + as circunstâncias de modo, \
lugar e serviço QUE O ENCARREGADO INFORMOU;
- fidelidade: não descarte nenhuma circunstância que ele informou. Se ele disse "sem apresentar \
justificativa", "na presença de subordinados" ou "estando de folga", isso entra no texto;
- impessoal e objetivo, sem juízo de valor, sem adjetivar e sem concluir culpa (o fato é apurado, não \
julgado);
- proibido: "o mesmo"/"a mesma" como pronome, gerundismo ("vou estar enviando"), horas com \
dois-pontos ou "hs" (use "8h20min").

Limite absoluto: NÃO invente circunstância que o encarregado não informou. Pode explicitar o que já \
está contido no próprio tipo legal (quem falta ao serviço tinha um serviço a cumprir), mas nada além \
disso - se ele não disse que houve ou não justificativa, não escreva nem uma coisa nem outra; se o \
dado importa, peça-o em "dados_faltantes".

Cuidado ao aproveitar as palavras do inciso: copie os termos que descrevem a CONDUTA, nunca os \
elementos valorativos ou normativos que ainda dependem de prova - "injustificadamente", "sem \
autorização", "indevidamente", "sem justa causa", "deliberadamente". Escreva "chegado atrasado à \
formatura", não "chegado injustificadamente atrasado", a menos que o encarregado tenha afirmado o \
fato correspondente. Afirmar isso no resumo é antecipar o julgamento do que o processo ainda vai \
apurar - e é contraditório pedir o mesmo dado em "dados_faltantes".

Exemplos do nível de redação esperado:
- "faltou ao serviço" -> "deixado de comparecer ao serviço para o qual estava escalado"
- "chegou atrasado na formatura" -> "chegado atrasado à formatura da guarda, ato de serviço de que \
deveria participar"
- "dormiu no serviço de guarda" -> "dormido durante o serviço de guarda que desempenhava"
- "tava fazendo bico de segurança numa festa" -> "exercido, em caráter privado, atividade de \
segurança em evento festivo"

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
