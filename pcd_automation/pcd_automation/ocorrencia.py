"""Base única da ocorrência - o "preenchimento único" do sistema.

Uma ocorrência é extraída uma vez (do REDS ou de outro documento) e passa a
alimentar TODOS os módulos: PCD, Recompensa, RIP, SAD, APF e Sindicância de
Acidente com Viatura. Nenhum módulo volta a pedir um dado que já está aqui.

Estrutura (JSON, persistida em `processos/_ocorrencias/<id>.json`):

    {
      "ocorrencia": {reds_numero, natureza, data_fato, hora_fato, local,
                     municipio, uf, unidade, fracao, historico_sucinto},
      "pessoas": [{id, tipo_envolvimento, nome_completo, cpf, rg,
                   data_nascimento, nacionalidade, naturalidade, estado_civil,
                   profissao, escolaridade, mae, pai, telefone, email,
                   endereco: {logradouro, numero, bairro, cidade, uf, cep}}],
      "bens_envolvidos": {objetos, veiculos, drogas, armas, valores},
      "equipe_policial": [{cargo_graduacao, nome_militar, num_policial, funcao,
                           unidade}],
      "viaturas": [...]
    }

Dois princípios que valem para o sistema inteiro:

1. campo ausente no documento é `null`, nunca inventado. Quem consome decide o
   que fazer com a ausência (em geral, marcar [PREENCHER]);
2. nada é gravado sem o usuário conferir. A extração é sugestão; a tela de
   revisão é que transforma em base da ocorrência.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

DIR_OCORRENCIAS = "_ocorrencias"

CAMPOS_PESSOA = [
    "nome_completo", "cpf", "rg", "data_nascimento", "nacionalidade",
    "naturalidade", "estado_civil", "profissao", "escolaridade", "mae", "pai",
    "telefone", "email",
]
CAMPOS_ENDERECO = ["logradouro", "numero", "bairro", "cidade", "uf", "cep"]

TIPOS_ENVOLVIMENTO = [
    "Autor", "Conduzido", "Vítima", "Testemunha", "Condutor", "Militar", "Outro",
]


# ---------------------------------------------------------------- persistência

def _pasta(diretorio_base: Path) -> Path:
    return Path(diretorio_base) / DIR_OCORRENCIAS


def salvar_ocorrencia(diretorio_base: Path, dados: dict, ocorrencia_id: str | None = None) -> str:
    ocorrencia_id = ocorrencia_id or uuid4().hex[:8]
    caminho = _pasta(diretorio_base) / f"{ocorrencia_id}.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    agora = datetime.now().isoformat(timespec="seconds")
    anterior = carregar_ocorrencia(diretorio_base, ocorrencia_id)
    payload = {
        "criado_em": (anterior or {}).get("criado_em") or agora,
        "atualizado_em": agora,
        "dados": normalizar(dados),
    }
    caminho.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ocorrencia_id


def carregar_ocorrencia(diretorio_base: Path, ocorrencia_id: str) -> dict | None:
    caminho = _pasta(diretorio_base) / f"{ocorrencia_id}.json"
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def listar_ocorrencias(diretorio_base: Path) -> list[dict]:
    pasta = _pasta(diretorio_base)
    if not pasta.exists():
        return []
    itens = []
    for caminho in pasta.glob("*.json"):
        try:
            payload = json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        payload["id"] = caminho.stem
        payload["resumo"] = resumo(payload.get("dados") or {})
        itens.append(payload)
    itens.sort(key=lambda i: i.get("criado_em") or "", reverse=True)
    return itens


def remover_ocorrencia(diretorio_base: Path, ocorrencia_id: str) -> None:
    (_pasta(diretorio_base) / f"{ocorrencia_id}.json").unlink(missing_ok=True)


# ---------------------------------------------------------------- normalização

def normalizar(dados: dict) -> dict:
    """Garante a forma do esquema, sem inventar conteúdo: chaves que faltam
    viram vazias, e cada pessoa recebe um id estável para os módulos poderem
    referenciá-la."""
    dados = dict(dados or {})
    dados.setdefault("ocorrencia", {})
    dados["pessoas"] = [_normalizar_pessoa(p, i) for i, p in enumerate(dados.get("pessoas") or [], 1)]
    bens = dados.get("bens_envolvidos") or {}
    dados["bens_envolvidos"] = {
        chave: list(bens.get(chave) or [])
        for chave in ("objetos", "veiculos", "drogas", "armas", "valores")
    }
    # O posto vem em texto livre ("3º SGT PM", "Sd") tanto do REDS quanto da
    # digitação manual. Normalizar aqui - e não só na extração - garante que
    # qualquer caminho de entrada produza o valor canônico que os <select> dos
    # formulários reconhecem; caso contrário o campo chega marcado como "fora
    # da lista".
    from pcd_automation.webapp.campos_ui import normalizar_posto

    equipe = []
    for militar in dados.get("equipe_policial") or []:
        militar = dict(militar or {})
        if militar.get("cargo_graduacao"):
            militar["cargo_graduacao"] = normalizar_posto(str(militar["cargo_graduacao"]))
        equipe.append(militar)
    dados["equipe_policial"] = equipe
    dados["viaturas"] = list(dados.get("viaturas") or [])
    return dados


def _normalizar_pessoa(pessoa: dict, indice: int) -> dict:
    pessoa = dict(pessoa or {})
    pessoa.setdefault("id", f"p_{indice:02d}")
    for campo in CAMPOS_PESSOA:
        pessoa.setdefault(campo, None)
    endereco = dict(pessoa.get("endereco") or {})
    for campo in CAMPOS_ENDERECO:
        endereco.setdefault(campo, None)
    pessoa["endereco"] = endereco
    pessoa["tipo_envolvimento"] = pessoa.get("tipo_envolvimento") or "Outro"
    return pessoa


def resumo(dados: dict) -> str:
    oc = dados.get("ocorrencia") or {}
    partes = [oc.get("reds_numero"), oc.get("natureza"), oc.get("municipio")]
    texto = " — ".join(str(p) for p in partes if p)
    return texto or "(ocorrência sem identificação)"


# ---------------------------------------------------------------- qualificação

def _data_br(valor) -> str | None:
    if not valor:
        return None
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    try:
        return date.fromisoformat(str(valor).strip()).strftime("%d/%m/%Y")
    except ValueError:
        return str(valor)


def formatar_qualificacao(pessoa: dict) -> str:
    """Monta a qualificação em texto corrido, como exigem os termos de
    depoimento e as portarias.

    Só entra no texto o que existe: um dado ausente é OMITIDO em vez de virar
    "None" ou um espaço em branco no meio da frase - num termo assinado, "filho
    de None e None" seria pior do que a informação simplesmente não constar.
    """
    if not pessoa:
        return ""
    nome = (pessoa.get("nome_completo") or "").strip()
    if not nome:
        return ""

    partes: list[str] = [nome]
    for chave in ("nacionalidade", "estado_civil", "profissao"):
        valor = (pessoa.get(chave) or "").strip() if pessoa.get(chave) else ""
        if valor:
            partes.append(valor)

    nascimento = _data_br(pessoa.get("data_nascimento"))
    if nascimento:
        partes.append(f"nascido(a) em {nascimento}")
    if pessoa.get("naturalidade"):
        partes.append(f"natural de {pessoa['naturalidade']}")

    mae, pai = (pessoa.get("mae") or "").strip(), (pessoa.get("pai") or "").strip()
    if mae and pai:
        partes.append(f"filho(a) de {pai} e {mae}")
    elif mae:
        partes.append(f"filho(a) de {mae}")
    elif pai:
        partes.append(f"filho(a) de {pai}")

    documentos = []
    if pessoa.get("rg"):
        documentos.append(f"RG nº {pessoa['rg']}")
    if pessoa.get("cpf"):
        documentos.append(f"CPF nº {pessoa['cpf']}")
    if documentos:
        partes.append("portador(a) do " + " e ".join(documentos))

    endereco = _formatar_endereco(pessoa.get("endereco") or {})
    if endereco:
        partes.append(f"residente em {endereco}")
    if pessoa.get("telefone"):
        partes.append(f"telefone {pessoa['telefone']}")

    return ", ".join(partes) + "."


def _formatar_endereco(endereco: dict) -> str:
    logradouro = (endereco.get("logradouro") or "").strip()
    if not logradouro:
        return ""
    texto = logradouro
    if endereco.get("numero"):
        texto += f", nº {endereco['numero']}"
    if endereco.get("bairro"):
        texto += f", bairro {endereco['bairro']}"
    cidade, uf = endereco.get("cidade"), endereco.get("uf")
    if cidade and uf:
        texto += f", {cidade}/{uf}"
    elif cidade:
        texto += f", {cidade}"
    if endereco.get("cep"):
        texto += f", CEP {endereco['cep']}"
    return texto


def pessoa_por_tipo(dados: dict, *tipos: str) -> dict | None:
    """Primeira pessoa cujo tipo de envolvimento casa com algum dos informados
    (comparação sem acento e sem caixa)."""
    alvos = {_sem_acento(t) for t in tipos}
    for pessoa in dados.get("pessoas") or []:
        if _sem_acento(pessoa.get("tipo_envolvimento") or "") in alvos:
            return pessoa
    return None


def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto.strip().lower()


# ------------------------------------------------- mapeamento para os módulos
#
# Cada entrada liga um campo do formulário de um módulo a um dado da
# ocorrência. É esta tabela - e só ela - que precisa crescer quando um módulo
# novo entrar no sistema: nenhum formulário precisa ser reescrito.
#
# O valor pode ser:
#   ("oc", "campo")                 -> bloco "ocorrencia"
#   ("pessoa", (tipos...), "campo") -> primeira pessoa do(s) tipo(s) indicado(s)
#   ("qualificacao", (tipos...))    -> qualificação em texto corrido
#   ("militar", indice, "campo")    -> equipe policial

MAPEAMENTO_MODULOS: dict[str, dict[str, tuple]] = {
    "recompensa": {
        "reds_recompensa": ("oc", "reds_numero"),
        "unidade_proponente": ("oc", "unidade"),
        "posto_proposto": ("militar", 0, "cargo_graduacao"),
        "nome_proposto": ("militar", 0, "nome_militar"),
        "numero_proposto": ("militar", 0, "num_policial"),
        "unidade_proposto": ("militar", 0, "unidade"),
    },
    "rip": {
        "resumo_fato_rip": ("oc", "historico_sucinto"),
        "unidade_investigador": ("oc", "unidade"),
    },
    "sad": {
        "descricao_transgressao_sad": ("oc", "historico_sucinto"),
        "unidade_encarregado_sad": ("oc", "unidade"),
        "nome_sindicado_sad": ("militar", 0, "nome_militar"),
        "posto_sindicado_sad": ("militar", 0, "cargo_graduacao"),
        "numero_sindicado_sad": ("militar", 0, "num_policial"),
        "unidade_sindicado_sad": ("militar", 0, "unidade"),
    },
    "apf": {
        "data_fato_apf": ("oc", "data_fato"),
        "hora_fato_apf": ("oc", "hora_fato"),
        "local_fato_apf": ("oc", "local"),
        "dinamica_fato_apf": ("oc", "historico_sucinto"),
        "nome_condutor_apf": ("militar", 0, "nome_militar"),
        "posto_condutor_apf": ("militar", 0, "cargo_graduacao"),
        "numero_condutor_apf": ("militar", 0, "num_policial"),
        "nome_conduzido_apf": ("pessoa", ("conduzido", "autor"), "nome_completo"),
        "qualificacao_conduzido_apf": ("qualificacao", ("conduzido", "autor")),
    },
    "acidente_viatura": {
        "unidade": ("oc", "unidade"),
        "cidade_sede": ("oc", "municipio"),
        "data_fato": ("oc", "data_fato"),
        "hora_fato": ("oc", "hora_fato"),
        "local_fato": ("oc", "local"),
        "historico_fato": ("oc", "historico_sucinto"),
        "nome_envolvido": ("militar", 0, "nome_militar"),
        "posto_envolvido": ("militar", 0, "cargo_graduacao"),
        "numero_envolvido": ("militar", 0, "num_policial"),
    },
}

# PCD usa o schema canônico (pcd_automation.schema), com nomes próprios.
MAPEAMENTO_PCD: dict[str, tuple] = {
    "reds": ("oc", "reds_numero"),
    "data_fato": ("oc", "data_fato"),
    "hora_fato": ("oc", "hora_fato"),
    "cidade_fato": ("oc", "municipio"),
    "local_fato": ("oc", "local"),
    "resumo_fato": ("oc", "historico_sucinto"),
    "nome_sindicado": ("militar", 0, "nome_militar"),
    "posto_graduacao_sindicado": ("militar", 0, "cargo_graduacao"),
    "re_sindicado": ("militar", 0, "num_policial"),
    "unidade_sindicado": ("militar", 0, "unidade"),
    "nome_testemunha": ("militar", 1, "nome_militar"),
    "posto_testemunha": ("militar", 1, "cargo_graduacao"),
    "re_testemunha": ("militar", 1, "num_policial"),
    "unidade_testemunha": ("militar", 1, "unidade"),
}


def _resolver(dados: dict, regra: tuple):
    origem = regra[0]
    if origem == "oc":
        return (dados.get("ocorrencia") or {}).get(regra[1])
    if origem == "militar":
        equipe = dados.get("equipe_policial") or []
        indice = regra[1]
        return equipe[indice].get(regra[2]) if len(equipe) > indice else None
    if origem == "pessoa":
        pessoa = pessoa_por_tipo(dados, *regra[1])
        return pessoa.get(regra[2]) if pessoa else None
    if origem == "qualificacao":
        pessoa = pessoa_por_tipo(dados, *regra[1])
        return formatar_qualificacao(pessoa) if pessoa else None
    return None


def valores_para(dados: dict, mapeamento: dict[str, tuple]) -> dict:
    """Traduz a ocorrência para os campos de um formulário. Só devolve o que
    tem valor - campo sem dado não entra, para não sobrescrever com vazio o que
    o usuário já digitou."""
    valores = {}
    for campo, regra in mapeamento.items():
        valor = _resolver(dados, regra)
        if valor not in (None, "", [], {}):
            valores[campo] = valor
    return valores


def valores_para_modulo(dados: dict, modulo_id: str) -> dict:
    return valores_para(dados, MAPEAMENTO_MODULOS.get(modulo_id) or {})


def valores_para_pcd(dados: dict) -> dict:
    return valores_para(dados, MAPEAMENTO_PCD)
