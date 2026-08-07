"""Extração da base única da ocorrência a partir de um documento.

Recebe o texto de um REDS (ou de outro documento: boletim, termo, certidão) já
extraído por `extracao.extrair_texto` - com OCR quando o PDF é digitalizado - e
devolve o JSON no formato de `ocorrencia.py`.

Diferença para `extracao.classificar_e_extrair`: aquele módulo lê um PROCESSO
já redigido (PCD, SAD, RIP...) para pré-preencher um rascunho; este lê a
OCORRÊNCIA de origem e monta a base de dados que alimenta todos os módulos,
com a qualificação civil completa (CPF, RG, filiação, endereço, escolaridade)
que os termos de depoimento exigem.
"""
from __future__ import annotations

import json
import re

from .ia_cliente import RespostaIA, chamar_openrouter_detalhado
from .ocorrencia import normalizar

PROMPT_SISTEMA = """Você é um extrator especializado em Boletins de Ocorrência da PMMG (REDS) e demais \
documentos policiais. Analise o texto fornecido e extraia as entidades no formato JSON abaixo.

REGRAS DE EXTRAÇÃO (obrigatórias):
1. Responda EXCLUSIVAMENTE com o JSON, sem markdown e sem texto explicativo.
2. NUNCA invente dados. Campo que não estiver no texto deve vir como null. Não deduza CPF, RG, \
filiação, endereço ou data de nascimento a partir de outros dados.
3. Separe as pessoas por "tipo_envolvimento", usando exatamente um destes valores: "Autor", \
"Conduzido", "Vítima", "Testemunha", "Condutor", "Militar", "Outro".
4. Policiais militares que atuaram na ocorrência vão em "equipe_policial", NÃO em "pessoas".
5. Datas no formato "aaaa-mm-dd". Horas no formato "HH:MM".
6. "historico_sucinto": resuma o histórico da ocorrência de forma objetiva e impessoal, sem juízo \
de valor. Não copie o texto inteiro; sintetize o que aconteceu.
7. Em "bens_envolvidos", cada item é uma string descritiva (ex.: "01 (uma) motocicleta Honda CG 160, \
placa ABC-1D23"). Liste apenas o que o texto menciona.
8. Liste em "ambiguidades" qualquer trecho ilegível, dado conflitante ou dúvida sobre a qual pessoa \
pertence determinado dado.

FORMATO DE SAÍDA:
{"ocorrencia": {"reds_numero": null, "natureza": null, "data_fato": null, "hora_fato": null, \
"local": null, "municipio": null, "uf": null, "unidade": null, "fracao": null, \
"historico_sucinto": null},
 "pessoas": [{"tipo_envolvimento": "...", "nome_completo": null, "cpf": null, "rg": null, \
"data_nascimento": null, "nacionalidade": null, "naturalidade": null, "estado_civil": null, \
"profissao": null, "escolaridade": null, "mae": null, "pai": null, "telefone": null, "email": null, \
"endereco": {"logradouro": null, "numero": null, "bairro": null, "cidade": null, "uf": null, \
"cep": null}}],
 "bens_envolvidos": {"objetos": [], "veiculos": [], "drogas": [], "armas": [], "valores": []},
 "equipe_policial": [{"cargo_graduacao": null, "nome_militar": null, "num_policial": null, \
"funcao": null, "unidade": null}],
 "viaturas": [],
 "ambiguidades": []}
"""


def _extrair_json(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip(), flags=re.IGNORECASE)
    return json.loads(texto)


# Documentos e contatos têm formato rígido, então dá para conferir por regex o
# que a IA devolveu. Em teste, um CPF que estava claramente no REDS
# ("CPF: 012.345.678-90") não veio no JSON - num sistema cujo propósito é não
# redigitar, perder documento silenciosamente é falha grave. Esta camada só
# PREENCHE lacuna: nunca sobrescreve valor que a IA já trouxe.
_PADROES_CAMPO = {
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "rg": re.compile(r"\bMG[\s.-]?\d{2}\.?\d{3}\.?\d{3}\b", re.IGNORECASE),
    "telefone": re.compile(r"\(\d{2}\)\s?\d{4,5}-?\d{4}"),
}
_PADRAO_CEP = re.compile(r"\b\d{5}-?\d{3}\b")


def _blocos_por_pessoa(texto: str, pessoas: list[dict]) -> dict[str, str]:
    """Recorta o trecho do documento que descreve cada pessoa: do seu nome até
    o nome da pessoa seguinte. Sem esse recorte, um CPF de outra pessoa poderia
    ser colado no registro errado - erro pior do que a lacuna."""
    posicoes: list[tuple[int, str]] = []
    for pessoa in pessoas:
        nome = (pessoa.get("nome_completo") or "").strip()
        if not nome:
            continue
        pos = texto.upper().find(nome.upper())
        if pos >= 0:
            posicoes.append((pos, pessoa["id"]))
    posicoes.sort()
    blocos: dict[str, str] = {}
    for i, (inicio, pessoa_id) in enumerate(posicoes):
        fim = posicoes[i + 1][0] if i + 1 < len(posicoes) else len(texto)
        blocos[pessoa_id] = texto[inicio:fim]
    return blocos


def completar_por_regex(dados: dict, texto: str) -> list[str]:
    """Preenche CPF, RG, telefone e CEP que a IA deixou vazios mas que estão no
    bloco daquela pessoa. Devolve a lista do que foi recuperado, para a tela
    poder mostrar ao usuário o que veio por esta via."""
    recuperados: list[str] = []
    pessoas = dados.get("pessoas") or []
    blocos = _blocos_por_pessoa(texto, pessoas)
    for pessoa in pessoas:
        bloco = blocos.get(pessoa.get("id") or "")
        if not bloco:
            continue
        nome = pessoa.get("nome_completo") or "(sem nome)"
        for campo, padrao in _PADROES_CAMPO.items():
            if pessoa.get(campo):
                continue
            achado = padrao.search(bloco)
            if achado:
                pessoa[campo] = achado.group(0)
                recuperados.append(f"{campo.upper()} de {nome}")
        endereco = pessoa.get("endereco") or {}
        if not endereco.get("cep"):
            achado = _PADRAO_CEP.search(bloco)
            if achado:
                endereco["cep"] = achado.group(0)
                pessoa["endereco"] = endereco
                recuperados.append(f"CEP de {nome}")
    return recuperados


def extrair_ocorrencia(texto: str) -> tuple[dict | None, str | None, RespostaIA | None]:
    """Devolve (dados_normalizados, erro, resposta_ia)."""
    if not (texto or "").strip():
        return None, (
            "Não foi possível extrair nenhum texto do arquivo (pode estar em branco, corrompido ou "
            "o OCR não reconheceu nada)."
        ), None

    resposta = chamar_openrouter_detalhado(
        [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": f"Documento a analisar:\n\n{texto[:150000]}"},
        ],
        max_tokens=12000,
        timeout=240,
        json_obrigatorio=True,
    )
    if resposta.erro:
        return None, resposta.erro, resposta
    try:
        bruto = _extrair_json(resposta.conteudo)
    except json.JSONDecodeError:
        return None, f"A IA não retornou um JSON válido. Resposta bruta: {resposta.conteudo[:400]}", resposta

    dados = normalizar(bruto)
    dados["ambiguidades"] = [str(a) for a in (bruto.get("ambiguidades") or [])]

    recuperados = completar_por_regex(dados, texto)
    if recuperados:
        dados["ambiguidades"].append(
            "Dados que a IA não trouxe e foram recuperados do texto por conferência automática "
            "(confira se estão na pessoa certa): " + "; ".join(recuperados) + "."
        )

    if resposta.usou_reserva:
        dados["ambiguidades"].append(
            f"O modelo principal estava indisponível; a extração foi feita pelo modelo reserva "
            f"{resposta.modelo_usado}, que é menor. Confira os dados com atenção redobrada."
        )
    return dados, None, resposta
