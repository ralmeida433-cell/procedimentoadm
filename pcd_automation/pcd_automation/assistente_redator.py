"""Especialidade de redação técnico-policial do Assistente.

O assistente tem duas especialidades:

- CONSULTOR (`rag.consulta`): responde dúvidas sobre o MAPPA a partir das
  referências indexadas;
- REDATOR (este módulo): ajuda a produzir e revisar o texto dos documentos,
  em especial o Relatório Conclusivo de Levantamento Inicial (LI).

A separação existe porque as duas tarefas têm exigências opostas. O consultor
PRECISA se limitar aos trechos recuperados. O redator trabalha sobre o texto
que o encarregado forneceu - e por isso a trava principal aqui é outra: ele não
pode acrescentar fato nenhum que o encarregado não tenha informado.

`[FUNDAMENTAR]` é a exceção e volta a usar o índice do MAPPA: fundamentação
jurídica é justamente o que não pode sair da memória do modelo. Artigo citado
de cabeça, em documento assinado, é o defeito mais grave que este sistema
poderia produzir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .ia_cliente import chamar_openrouter_detalhado
from .rag.consulta import buscar_trechos

MARCA_FALTANTE = "[INFORMAÇÃO NÃO INFORMADA]"

# Regras que valem para todos os modos.
PROMPT_BASE = f"""Você é o Assistente de Redação Técnico-Policial da PMMG. Auxilia o encarregado a \
elaborar, revisar e aprimorar documentos correcionais e operacionais - em especial o Relatório \
Conclusivo de Levantamento Inicial (LI), do art. 100 do MAPPA.

REGRAS INVIOLÁVEIS:
1. NUNCA INVENTE FATOS. Não crie nomes, datas, horários, postos/graduações, unidades, números de \
documento, provas, diligências nem artigos de lei. Se faltar dado essencial para a frase ficar \
completa, escreva exatamente {MARCA_FALTANTE} no lugar e siga em frente - jamais preencha com um \
valor plausível.
2. NEUTRALIDADE. O fato é apurado, não julgado. Não afirme culpa nem use adjetivos que a antecipem. \
Empregue "em tese", "segundo relatado", "conforme documento anexado", "teria". Não conclua que o \
militar praticou a conduta: descreva o que as provas indicam.
3. PRECEDÊNCIA HIERÁRQUICA. Qualifique os envolvidos com posto/graduação, número e nome completo, \
respeitando a cadeia de comando. No corpo do texto use "nº 123.456-7, Capitão PM FULANO DE TAL"; \
em assinatura use "FULANO DE TAL, CAPITÃO PM".
4. REDAÇÃO OFICIAL DA PMMG: impessoal e objetiva; horas no padrão "19h30min" (nunca "19:30" nem \
"19hs"); sem "o mesmo/a mesma" como pronome; sem gerundismo; siglas por extenso na primeira menção.

Base normativa aplicável: MAPPA (Resolução Conjunta nº 4.220/2012), CEDM (Lei Estadual nº \
14.310/2002) e Estatuto dos Militares de Minas Gerais (Lei Estadual nº 5.301/1969).

Se o encarregado não forneceu dados suficientes para a tarefa pedida, diga o que falta em vez de \
completar por conta própria."""

_INSTRUCOES = {
    "RESUMIR": (
        "TAREFA: produzir uma síntese objetiva e cronológica da ocorrência a partir do texto "
        "fornecido. Ordene os acontecimentos no tempo, elimine repetição e o que não for relevante "
        "para a apuração. Não acrescente circunstância que não esteja no texto."
    ),
    "REDIGIR": (
        "TAREFA: redigir o Relatório Conclusivo de Levantamento Inicial com base nos dados "
        "fornecidos, nesta estrutura:\n"
        "1. IDENTIFICAÇÃO (unidade, registro do LI, autoridade mandante, encarregado, envolvidos)\n"
        "2. HISTÓRICO / ORIGEM\n"
        "3. DILIGÊNCIAS REALIZADAS (cronológicas)\n"
        "4. ANÁLISE DOS FATOS E FUNDAMENTAÇÃO (confronto entre as provas e a versão dos envolvidos; "
        "indícios mínimos de autoria e materialidade; enquadramento em tese)\n"
        "5. CONCLUSÃO E PARECER (parecer motivado e a medida proposta)\n"
        "6. FECHAMENTO (local, data e assinatura do encarregado)\n"
        "Todo campo sem dado informado recebe a marcação de informação não informada. Ao final, "
        "liste sob o título 'DADOS QUE FALTAM' tudo o que precisa ser completado."
    ),
    "MELHORAR": (
        "TAREFA: reescrever o texto fornecido na redação técnico-policial, PRESERVANDO "
        "integralmente os fatos. É proibido acrescentar, remover ou alterar qualquer circunstância, "
        "data, nome ou conclusão - só a forma muda. Se identificar no texto original alguma "
        "afirmação que antecipe culpa, reescreva-a de modo neutro e avise o encarregado ao final, "
        "sob o título 'AJUSTES DE NEUTRALIDADE'."
    ),
    "FUNDAMENTAR": (
        "TAREFA: apresentar a fundamentação jurídica aplicável ao caso, baseando-se SOMENTE nos "
        "trechos de referência fornecidos abaixo. Cite o artigo e o arquivo de origem. Se os "
        "trechos não cobrirem o caso com segurança, diga isso expressamente - não complete com "
        "conhecimento próprio nem cite artigo que não esteja nos trechos."
    ),
    "PERGUNTAR": (
        "TAREFA: apontar o que ainda falta para fechar o procedimento. Liste (a) as perguntas "
        "objetivas a fazer aos envolvidos ou testemunhas e (b) as diligências que ainda cabem "
        "(documentos a juntar, sistemas a consultar, vistorias). Priorize o que sustenta ou afasta "
        "os indícios de autoria e materialidade. Não invente lacuna que o texto não revele."
    ),
}

MODOS = {
    "RESUMIR": "Síntese objetiva e cronológica da ocorrência",
    "REDIGIR": "Relatório Conclusivo de LI completo, a partir dos dados",
    "MELHORAR": "Aprimora a linguagem preservando os fatos",
    "FUNDAMENTAR": "Fundamentação jurídica com base nas referências",
    "PERGUNTAR": "Perguntas e diligências que ainda faltam",
}


@dataclass
class RespostaRedator:
    texto: str | None = None
    erro: str | None = None
    modo: str | None = None
    fontes: list[str] = field(default_factory=list)


def detectar_modo(texto: str) -> tuple[str | None, str]:
    """Separa o comando do conteúdo: "[MELHORAR] o texto..." -> ("MELHORAR",
    "o texto..."). Sem comando reconhecido, devolve (None, texto original) e o
    chamador trata como consulta normal ao MAPPA."""
    limpo = (texto or "").strip()
    if not limpo.startswith("["):
        return None, limpo
    fim = limpo.find("]")
    if fim < 0:
        return None, limpo
    candidato = limpo[1:fim].strip().upper()
    if candidato not in _INSTRUCOES:
        return None, limpo
    return candidato, limpo[fim + 1:].strip()


def executar(modo: str, conteudo: str, historico: list[dict] | None = None) -> RespostaRedator:
    """Executa um modo de redação. `historico` é a conversa anterior, para o
    encarregado poder dizer "agora melhora esse texto" sem colar tudo de novo."""
    if modo not in _INSTRUCOES:
        return RespostaRedator(erro=f"Modo desconhecido: {modo}.")

    historico = historico or []
    if not conteudo.strip() and not historico:
        return RespostaRedator(
            erro=f"Envie o texto ou os dados junto com o comando. Ex.: [{modo}] seguido do conteúdo.",
            modo=modo,
        )

    partes = [PROMPT_BASE, "", _INSTRUCOES[modo]]
    fontes: list[str] = []

    if modo == "FUNDAMENTAR":
        # Fundamentação não pode sair da memória do modelo - vai buscar no índice.
        consulta = conteudo or " ".join(
            str(m.get("texto") or "") for m in historico if m.get("papel") == "usuario"
        )
        trechos = buscar_trechos(consulta, top_k=8)
        if not trechos:
            return RespostaRedator(
                erro="Não encontrei trechos das referências do MAPPA para fundamentar esse caso. "
                     "Descreva a conduta com outras palavras ou cite o instituto (PCD, SAD, LI, RIP).",
                modo=modo,
            )
        fontes = sorted({t.arquivo for t in trechos})
        partes += [
            "",
            "TRECHOS DE REFERÊNCIA (use somente estes):",
            "\n\n---\n\n".join(f"[{t.arquivo}]\n{t.texto}" for t in trechos),
        ]

    mensagens = [{"role": "system", "content": "\n".join(partes)}]
    for m in historico:
        texto = str(m.get("texto") or "").strip()
        if texto:
            mensagens.append({
                "role": "user" if m.get("papel") == "usuario" else "assistant",
                "content": texto,
            })
    if conteudo.strip():
        mensagens.append({"role": "user", "content": conteudo})

    resposta = chamar_openrouter_detalhado(mensagens, max_tokens=3000, timeout=180)
    if resposta.erro:
        return RespostaRedator(erro=resposta.erro, modo=modo)

    texto = resposta.conteudo
    if resposta.usou_reserva:
        texto += (
            f"\n\n_(Gerado pelo modelo reserva {resposta.modelo_usado}, menor que o principal, "
            "que estava indisponível. Revise com atenção redobrada.)_"
        )
    return RespostaRedator(texto=texto, modo=modo, fontes=fontes)
