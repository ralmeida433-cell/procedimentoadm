"""Relatório Conclusivo do Levantamento Inicial (LI).

Base normativa (MAPPA, Capítulo IV - arts. 100 a 103):

- art. 100, I: o LI cabe quando os indícios de autoria e/ou materialidade,
  ALÉM DE INSUFICIENTES, demonstrem necessidade de obter elementos que
  justifiquem a instauração de RIP ou de processo/procedimento regular. É a
  medida mais leve da escala - abaixo do RIP (inciso II), que por sua vez está
  abaixo da SAD/IPM;
- art. 100, §1º: não procedendo os fatos, arquiva-se (arts. 6º e 7º), ou a
  autoridade acompanha o caso, ou adota outras medidas administrativas;
- art. 100, §2º: o LI é realizado pela Seção de Inteligência OU por militar
  possuidor de precedência hierárquica em relação ao investigado - requisito
  de competência conferido em `alertas_conformidade`;
- art. 100, §3º: "para confecção do Levantamento Inicial, não há maiores
  formalidades", e o resultado pode ser apresentado por relatório ou qualquer
  outro documento que registre o fato averiguado. Por isso este módulo gera UMA
  peça (o relatório conclusivo), e não um rito com várias peças;
- art. 101: cuidado para não ensejar exposição pública do militar investigado;
- art. 103: confirmada preliminarmente a veracidade, a portaria do processo
  seguinte cita como origem o LI - não a denúncia anônima.

Sem prazo fixo: o MAPPA não estabelece prazo de conclusão para o LI (ao
contrário do RIP, 15 dias, e da SAD, 30). Coerente com o art. 100, §3º. O
módulo não inventa um.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .gerador_acidente_viatura import (
    CAMINHO_BASE, _abrir_base, _assinatura, _data, _data_barra, _fecho_local_data,
    _p, _qualificar, _para_assinatura, _salvar, _sim, _texto,
)
from .schema import precedencia_posto

NOME_ARQUIVO = "relatorio_conclusivo_li.docx"

# Medidas que o encarregado pode propor, na escala do art. 100.
MEDIDAS = [
    "Arquivamento (fatos não procedem ou inexistência de indícios)",
    "Instauração de RIP (indícios mais consistentes, porém ainda insuficientes)",
    "Instauração de PCD",
    "Instauração de SAD",
    "Instauração de PADS",
    "Instauração de PAD",
    "Remessa para IPM (indício de crime militar)",
    "Adoção de medidas administrativas/operacionais",
]

# Medidas que só se sustentam se o encarregado tiver apontado indícios.
_MEDIDAS_QUE_EXIGEM_INDICIOS = {m for m in MEDIDAS if m.startswith(("Instauração", "Remessa"))}


@dataclass
class ResultadoLI:
    ok: bool = True
    documentos: list[str] = field(default_factory=list)
    pendentes: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)


def alertas_conformidade(dados: dict) -> list[str]:
    """Confere o que o MAPPA exige do LI. Não impede a geração - aponta."""
    avisos: list[str] = []

    # art. 100, §2º - competência do encarregado.
    if not _sim(dados.get("encarregado_inteligencia")):
        posto_enc = precedencia_posto(str(dados.get("posto_encarregado") or ""))
        posto_inv = precedencia_posto(str(dados.get("posto_envolvido") or ""))
        if posto_enc is not None and posto_inv is not None and posto_enc <= posto_inv:
            avisos.append(
                "Competência (art. 100, §2º, do MAPPA): o LI deve ser realizado pela Seção de "
                "Inteligência ou por militar com precedência hierárquica sobre o investigado. O "
                f"encarregado ({dados.get('posto_encarregado')}) não tem precedência sobre o "
                f"investigado ({dados.get('posto_envolvido')}). Designe outro encarregado ou "
                "registre que o levantamento coube à Seção de Inteligência."
            )

    # Coerência entre o que foi apurado e a medida proposta.
    medida = str(dados.get("medida_proposta") or "")
    houve_indicios = _sim(dados.get("houve_indicios"))
    if medida in _MEDIDAS_QUE_EXIGEM_INDICIOS and not houve_indicios:
        avisos.append(
            f"Coerência da conclusão: foi proposta a medida \"{medida}\", mas o relatório não "
            "registra a existência de indícios de autoria/materialidade. Instaurar procedimento "
            "sem indício apontado no próprio relatório fragiliza o ato - reveja a análise ou a "
            "medida proposta."
        )
    if medida.startswith("Arquivamento") and houve_indicios:
        avisos.append(
            "Coerência da conclusão: o relatório aponta indícios, mas propõe o arquivamento. Se os "
            "indícios existem, o art. 100 do MAPPA aponta para RIP ou processo regular; se não "
            "procedem, ajuste a análise. O arquivamento segue os arts. 6º e 7º do MAPPA."
        )

    # art. 103 - origem citada na portaria seguinte.
    if _sim(dados.get("origem_denuncia_anonima")) and medida in _MEDIDAS_QUE_EXIGEM_INDICIOS:
        avisos.append(
            "Origem (art. 103 do MAPPA): confirmada preliminarmente a veracidade, a portaria do "
            "processo a ser instaurado deve indicar como origem ESTE Levantamento Inicial, e não a "
            "denúncia anônima."
        )

    # art. 101 - sigilo.
    avisos.append(
        "Sigilo (art. 101 do MAPPA): durante e após o levantamento, evite qualquer medida que "
        "enseje exposição pública do militar investigado."
    )
    return avisos


def _montar(doc, dados: dict, pendentes: list[str]) -> None:
    cidade = _texto(dados, "cidade_sede", "cidade do quartel", pendentes)
    unidade = _texto(dados, "unidade", "unidade/órgão", pendentes)
    registro = _texto(dados, "registro_li", "registro do LI", pendentes)
    encarregado = _qualificar(dados, "encarregado", "dados do encarregado do LI", pendentes)
    mandante = _texto(dados, "autoridade_mandante", "autoridade mandante", pendentes)

    _p(doc, "RELATÓRIO CONCLUSIVO DE LEVANTAMENTO INICIAL", centro=True, negrito=True, recuo=False)
    _p(doc, registro, centro=True, negrito=True, recuo=False)
    _p(doc, "")

    _p(doc, "1. IDENTIFICAÇÃO", negrito=True, recuo=False)
    _p(doc, f"a. Unidade/Órgão: {unidade}.")
    _p(doc, f"b. Registro: {registro}.")
    _p(doc, f"c. Autoridade mandante: {mandante}.")
    _p(doc, f"d. Encarregado do Levantamento Inicial: {encarregado}"
            f"{' (Seção de Inteligência)' if _sim(dados.get('encarregado_inteligencia')) else ''}.")
    envolvido = str(dados.get("nome_envolvido") or "").strip()
    if envolvido:
        _p(doc, f"e. Envolvido/investigado: {_qualificar(dados, 'envolvido', 'dados do envolvido', pendentes)}.")
    else:
        _p(doc, "e. Envolvido/investigado: não identificado até o presente levantamento.")
    _p(doc, "")

    _p(doc, "2. INTRODUÇÃO E ORIGEM", negrito=True, recuo=False)
    origem = ("denúncia anônima" if _sim(dados.get("origem_denuncia_anonima"))
              else _texto(dados, "origem_fato", "origem do fato", pendentes))
    _p(doc, f"Por determinação do {mandante}, coube a este encarregado proceder ao Levantamento "
            f"Inicial de que trata o art. 100, inciso I, do MAPPA, destinado a obter elementos que "
            f"permitam à autoridade competente avaliar a necessidade de instauração de "
            f"procedimento regular, tendo por origem {origem}.")
    _p(doc, f"Objeto da apuração: {_texto(dados, 'objeto_apuracao', 'objeto da apuração', pendentes)}")
    data_fato = _data(dados, "data_fato")
    if data_fato:
        _p(doc, f"Os fatos noticiados teriam ocorrido em {_data_barra(data_fato, 'data do fato', pendentes)}"
                f"{', em ' + str(dados.get('local_fato')) if dados.get('local_fato') else ''}.")
    _p(doc, "")

    _p(doc, "3. DILIGÊNCIAS REALIZADAS", negrito=True, recuo=False)
    _p(doc, _texto(dados, "diligencias", "diligências realizadas (seção 3 do relatório)", pendentes))
    _p(doc, "")

    _p(doc, "4. ESCLARECIMENTOS DO(S) ENVOLVIDO(S)", negrito=True, recuo=False)
    esclarecimentos = str(dados.get("esclarecimentos") or "").strip()
    _p(doc, esclarecimentos or "Não foram colhidos esclarecimentos do(s) envolvido(s) nesta fase, "
                               "dada a natureza sumária do levantamento.")
    _p(doc, "")

    _p(doc, "5. ANÁLISE DOS FATOS E DAS PROVAS", negrito=True, recuo=False)
    _p(doc, _texto(dados, "analise_fatos", "análise dos fatos e das provas (seção 5 do relatório)", pendentes))
    _p(doc, f"Quanto aos indícios de autoria e materialidade: "
            f"{'foram identificados elementos indiciários, adiante especificados' if _sim(dados.get('houve_indicios')) else 'não foram identificados, até o presente levantamento, indícios suficientes de autoria e/ou materialidade'}.")
    enquadramento = str(dados.get("enquadramento_tese") or "").strip()
    if enquadramento:
        _p(doc, f"Quanto ao enquadramento, em tese: {enquadramento}")
    _p(doc, "")

    _p(doc, "6. CONCLUSÃO E PARECER", negrito=True, recuo=False)
    _p(doc, _texto(dados, "conclusao", "conclusão do encarregado (seção 6 do relatório)", pendentes))
    medida = str(dados.get("medida_proposta") or "").strip()
    if medida:
        _p(doc, f"Diante do exposto, este encarregado propõe, salvo melhor juízo de Vossa Senhoria, "
                f"a seguinte medida: {medida}.")
    else:
        pendentes.append("medida proposta ao final do relatório")
        _p(doc, "Diante do exposto, este encarregado propõe, salvo melhor juízo de Vossa Senhoria, a "
                "seguinte medida: [PREENCHER: medida proposta ao final do relatório].")
    _p(doc, "É o relatório, que submeto à superior apreciação.")

    _fecho_local_data(doc, cidade, _data(dados, "data_relatorio"))
    _assinatura(doc, _para_assinatura(dados, "encarregado"), "Encarregado do Levantamento Inicial")


def gerar_documentos(dados: dict, diretorio_saida: Path) -> ResultadoLI:
    resultado = ResultadoLI()
    pendentes: list[str] = []
    try:
        doc = _abrir_base()
        _montar(doc, dados, pendentes)
        _salvar(doc, Path(diretorio_saida) / NOME_ARQUIVO)
        resultado.documentos.append(NOME_ARQUIVO)
    except Exception as exc:  # noqa: BLE001 - erro vira mensagem para o usuário
        resultado.ok = False
        resultado.erros.append(f"{NOME_ARQUIVO}: {exc}")

    resultado.pendentes = pendentes
    resultado.alertas = alertas_conformidade(dados)
    return resultado
