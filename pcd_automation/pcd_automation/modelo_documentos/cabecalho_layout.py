"""Padronização da posição dos dois elementos gráficos do cabeçalho.

Padrão exigido (igual em TODOS os documentos):
  - **Brasão da PMMG** (escudo colorido, que acompanha o timbre "POLÍCIA
    MILITAR DE MINAS GERAIS...") → extremidade ESQUERDA.
  - **Carimbo de "nº de folha / assinatura"** (o selo circular "FL.__/Ass.__")
    → extremidade DIREITA.

Estrutura real dos modelos (verificada abrindo cada `.docx`):
  - O brasão é uma imagem INLINE, dentro da primeira tabela do CORPO do
    documento. Nessa tabela de 3 colunas (imagem | espaçador | timbre), o
    brasão já vem na PRIMEIRA célula (esquerda) e o timbre na última
    (direita). Ou seja: no arquivo-fonte o brasão já está correto (à
    esquerda).
  - O carimbo é uma imagem FLUTUANTE (âncora) no CABEÇALHO da página. A
    posição horizontal dele variava entre os modelos (alguns à esquerda,
    outros à direita).

Histórico (importante p/ não repetir o erro): uma versão anterior deste
módulo tinha os dois elementos TROCADOS - achava que a imagem da tabela era
o carimbo e a imagem flutuante era o brasão. Resultado: empurrava o brasão
para a direita e o carimbo para a esquerda (exatamente o contrário do
esperado). As funções abaixo refletem a estrutura real.

IMPORTANTE sobre o ajuste do carimbo: ele NÃO pode ser feito no objeto
`python-docx` em memória. O `docxtpl`, durante o `render()`, substitui as
partes de cabeçalho/rodapé por objetos novos
(`DocxTemplate.map_headers_footers_xml`), então uma mutação feita via
`secao.header` depois do `render()` não é o que `modelo.save()` grava - o
salvamento usa a referência de parte que o docxtpl trocou internamente. Por
isso esse ajuste opera nos BYTES do `.docx` já salvo (reabre o zip, corrige
o XML dos cabeçalhos/rodapés, regrava o zip). Já o ajuste do brasão mexe no
CORPO do documento (document.xml), que não sofre essa troca - então pode ser
feito em memória, antes de salvar.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from docx.oxml.ns import qn


def _tem_desenho(celula_xml) -> bool:
    return celula_xml.find(".//" + qn("w:drawing")) is not None


def _trocar_conteudo(celula_a, celula_b) -> None:
    filhos_a = list(celula_a)
    filhos_b = list(celula_b)
    for filho in filhos_a:
        celula_a.remove(filho)
    for filho in filhos_b:
        celula_b.remove(filho)
    for filho in filhos_b:
        celula_a.append(filho)
    for filho in filhos_a:
        celula_b.append(filho)


def _trocar_largura_colunas(tabela_xml, indice_a: int, indice_b: int) -> None:
    grid = tabela_xml.find(qn("w:tblGrid"))
    if grid is None:
        return
    colunas = grid.findall(qn("w:gridCol"))
    if len(colunas) <= max(indice_a, indice_b):
        return
    atributo_largura = qn("w:w")
    largura_a = colunas[indice_a].get(atributo_largura)
    largura_b = colunas[indice_b].get(atributo_largura)
    if largura_a is None or largura_b is None:
        return
    colunas[indice_a].set(atributo_largura, largura_b)
    colunas[indice_b].set(atributo_largura, largura_a)


def padronizar_brasao_esquerda(doc) -> None:
    """Garante que o brasão (imagem inline na 1ª tabela do corpo) fique na
    célula da ESQUERDA.

    Nos modelos-fonte o brasão já vem na primeira célula, então normalmente
    esta função é um no-op. Ela é DEFENSIVA/idempotente: se encontrar o
    brasão na ÚLTIMA célula (e não na primeira), devolve o conteúdo e a
    largura da coluna para a primeira, mantendo o timbre à direita.
    """
    if not doc.tables:
        return
    tabela = doc.tables[0]
    if not tabela.rows:
        return
    celulas_xml = tabela.rows[0]._tr.findall(qn("w:tc"))
    if len(celulas_xml) < 2:
        return

    primeira, ultima = celulas_xml[0], celulas_xml[-1]
    # Se o brasão já está na primeira célula, nada a fazer (caso normal).
    if _tem_desenho(primeira):
        return
    # Se está só na última, traz de volta para a primeira.
    if _tem_desenho(ultima):
        _trocar_conteudo(primeira, ultima)
        _trocar_largura_colunas(tabela._tbl, 0, len(celulas_xml) - 1)


# Casa o bloco <wp:positionH ...>...</wp:positionH> inteiro (tanto a variante
# com <wp:posOffset> quanto a com <wp:align>) para substituí-lo por
# alinhamento à direita relativo à margem.
_PADRAO_POSITION_H = re.compile(r"<wp:positionH\b.*?</wp:positionH>", re.DOTALL)
_POSITION_H_DIREITA = '<wp:positionH relativeFrom="margin"><wp:align>right</wp:align></wp:positionH>'
_PADRAO_NOME_PARTE_CABECALHO = re.compile(r"word/(header|footer)\d*\.xml$")


def padronizar_carimbo_direita(caminho_docx: Path | str) -> None:
    """Força a imagem flutuante do cabeçalho/rodapé (o carimbo de folha/
    assinatura) para a extremidade DIREITA da página (alinhada à margem
    direita).

    Opera nos bytes do `.docx` já salvo (ver nota no topo do módulo sobre
    por que não dá para fazer isso via `python-docx` em memória quando o
    documento passou pelo `docxtpl`). Só ajusta a posição HORIZONTAL - a
    vertical de cada modelo não é alterada. Arquivos sem imagem flutuante no
    cabeçalho (ex.: Comunicação Disciplinar) não são afetados.
    """
    caminho_docx = Path(caminho_docx)
    with zipfile.ZipFile(caminho_docx, "r") as entrada:
        nomes = entrada.namelist()
        conteudos = {nome: entrada.read(nome) for nome in nomes}

    mudou = False
    for nome in nomes:
        if not _PADRAO_NOME_PARTE_CABECALHO.search(nome):
            continue
        xml = conteudos[nome].decode("utf-8")
        novo_xml, quantidade = _PADRAO_POSITION_H.subn(_POSITION_H_DIREITA, xml)
        if quantidade:
            conteudos[nome] = novo_xml.encode("utf-8")
            mudou = True

    if not mudou:
        return

    with zipfile.ZipFile(caminho_docx, "w", zipfile.ZIP_DEFLATED) as saida:
        for nome in nomes:
            saida.writestr(nome, conteudos[nome])
