"""Índice de busca (BM25) sobre as referências do MAPPA.

Reaproveita, sem duplicar, os mesmos arquivos de `references/` usados pela
skill `especialista-mappa` (`.claude/skills/especialista-mappa/references/`)
- essa pasta é a única fonte de verdade sobre prazos, ritos e artigos.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

TAMANHO_MAXIMO_CHUNK = 1200  # caracteres por trecho, aproximadamente

# Arquivos que tratam especificamente de UM processo - usado para reforçar
# (ou penalizar) a pontuação de busca quando a pergunta cita a sigla do
# processo, já que capítulos de processos diferentes usam vocabulário muito
# parecido ("defesa prévia", "sindicado" etc.) e o BM25 puro, sozinho, tende
# a misturar as siglas.
PROCESSO_POR_ARQUIVO: dict[str, set[str]] = {
    "cap03-dever-comunicar-investigar.md": {"pcd", "pqd", "tdr", "rr"},
    "cap05-rip.md": {"rip"},
    "cap08-sad.md": {"sad"},
    "cap09-sindicancia-viatura.md": {"sad"},
    "cap10-pad.md": {"pad"},
    "cap11-pads.md": {"pads"},
    "cap12-pae.md": {"pae"},
    "cap13-recompensas.md": {"pr"},
}
_SIGLAS_CONHECIDAS = {s for siglas in PROCESSO_POR_ARQUIVO.values() for s in siglas}
_REFORCO_SIGLA = 1.6
_PENALIDADE_SIGLA_DIVERGENTE = 0.5


def _raiz_referencias_padrao() -> Path:
    caminho_env = os.environ.get("MAPPA_REFERENCIAS_DIR")
    if caminho_env:
        return Path(caminho_env)
    raiz_projeto = Path(__file__).resolve().parents[3]
    return raiz_projeto / ".claude" / "skills" / "especialista-mappa" / "references"


@dataclass
class Trecho:
    arquivo: str
    indice: int
    texto: str


def _normalizar(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    return re.findall(r"[a-z0-9]+", texto)


def _dividir_em_paragrafos(texto: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]


def _agrupar_paragrafos(paragrafos: list[str], tamanho_maximo: int) -> list[str]:
    grupos: list[str] = []
    atual: list[str] = []
    tamanho_atual = 0
    for paragrafo in paragrafos:
        if atual and tamanho_atual + len(paragrafo) > tamanho_maximo:
            grupos.append("\n\n".join(atual))
            ultimo = atual[-1]
            atual = [ultimo]
            tamanho_atual = len(ultimo)
        atual.append(paragrafo)
        tamanho_atual += len(paragrafo)
    if atual:
        grupos.append("\n\n".join(atual))
    return grupos


def carregar_trechos(raiz_referencias: Path) -> list[Trecho]:
    """Carrega o conhecimento da skill `especialista-mappa`.

    Indexa TODOS os .md da skill, e não só os de `references/`: o `SKILL.md`
    da raiz traz a metodologia (os 4 modos de atuação, o índice de referências
    e os avisos permanentes), que é justamente a parte procedimental - como
    conduzir, o que auditar, o que nunca fazer. Sem ele, o assistente sabia os
    artigos mas não o método de trabalho da skill.

    A busca é recursiva (`rglob`) para acompanhar a skill se ela ganhar
    subpastas de referência.
    """
    if not raiz_referencias.exists():
        raise FileNotFoundError(
            f"Pasta de referências do MAPPA não encontrada em: {raiz_referencias}. "
            "Defina a variável de ambiente MAPPA_REFERENCIAS_DIR se o caminho padrão não se aplicar."
        )
    raizes = [raiz_referencias]
    # `references/` fica dentro da skill; subindo um nível alcançamos o
    # SKILL.md. Só vale quando o caminho é mesmo o padrão da skill - se o
    # usuário apontou MAPPA_REFERENCIAS_DIR para outro lugar, não saímos de lá.
    if raiz_referencias.name == "references" and (raiz_referencias.parent / "SKILL.md").exists():
        raizes.append(raiz_referencias.parent)

    trechos: list[Trecho] = []
    vistos: set[Path] = set()
    for raiz in raizes:
        for caminho in sorted(raiz.rglob("*.md")):
            if caminho in vistos:
                continue
            vistos.add(caminho)
            texto = caminho.read_text(encoding="utf-8")
            paragrafos = _dividir_em_paragrafos(texto)
            for i, grupo in enumerate(_agrupar_paragrafos(paragrafos, TAMANHO_MAXIMO_CHUNK)):
                trechos.append(Trecho(arquivo=caminho.name, indice=i, texto=grupo))
    return trechos


class IndiceMappa:
    def __init__(self, raiz_referencias: Path | None = None):
        self.raiz_referencias = raiz_referencias or _raiz_referencias_padrao()
        self.trechos = carregar_trechos(self.raiz_referencias)
        self._bm25 = BM25Okapi([_normalizar(t.texto) for t in self.trechos])

    def buscar(self, pergunta: str, top_k: int = 6) -> list[Trecho]:
        termos = _normalizar(pergunta)
        if not termos:
            return []
        pontuacoes = list(self._bm25.get_scores(termos))

        siglas_na_pergunta = set(termos) & _SIGLAS_CONHECIDAS
        if siglas_na_pergunta:
            for i, trecho in enumerate(self.trechos):
                siglas_arquivo = PROCESSO_POR_ARQUIVO.get(trecho.arquivo)
                if siglas_arquivo is None:
                    continue
                if siglas_arquivo & siglas_na_pergunta:
                    pontuacoes[i] *= _REFORCO_SIGLA
                else:
                    pontuacoes[i] *= _PENALIDADE_SIGLA_DIVERGENTE

        indices_ordenados = sorted(range(len(pontuacoes)), key=lambda i: pontuacoes[i], reverse=True)
        return [self.trechos[i] for i in indices_ordenados[:top_k] if pontuacoes[i] > 0]


_indice_global: IndiceMappa | None = None
_assinatura_global: tuple | None = None


def _assinatura_referencias(raiz: Path) -> tuple:
    """Impressão digital do conjunto de arquivos: nome, tamanho e data de
    modificação de cada .md."""
    itens = []
    raizes = [raiz]
    if raiz.name == "references" and (raiz.parent / "SKILL.md").exists():
        raizes.append(raiz.parent)
    vistos: set[Path] = set()
    for r in raizes:
        for caminho in sorted(r.rglob("*.md")):
            if caminho in vistos:
                continue
            vistos.add(caminho)
            try:
                st = caminho.stat()
            except OSError:
                continue
            itens.append((str(caminho), st.st_size, int(st.st_mtime)))
    return tuple(itens)


def obter_indice() -> IndiceMappa:
    """Índice em memória, reconstruído quando os arquivos de referência mudam.

    Sem essa verificação, o índice era montado uma vez por processo e nunca
    mais: acrescentar uma norma à skill não surtia efeito nenhum até alguém
    reiniciar o servidor - e, pior, sem aviso. O assistente continuava
    respondendo "não encontrei nas referências" para algo que já estava lá.

    Comparar tamanho e data de modificação é barato (só um `stat` por arquivo,
    ~34 hoje) e roda antes de cada consulta; a reindexação só acontece quando
    algo realmente mudou.
    """
    global _indice_global, _assinatura_global
    raiz = _raiz_referencias_padrao()
    assinatura = _assinatura_referencias(raiz)
    if _indice_global is None or assinatura != _assinatura_global:
        _indice_global = IndiceMappa(raiz)
        _assinatura_global = assinatura
    return _indice_global
