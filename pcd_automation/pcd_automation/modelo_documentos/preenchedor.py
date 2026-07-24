"""Preenchimento dos templates normalizados via docxtpl.

O merge em si (colocar o dado no lugar do marcador `{{ campo }}`) é
delegado ao docxtpl - ele resolve corretamente o caso em que um marcador
foi dividido em mais de um "run" pelo Word (algo que uma substituição de
texto simples com python-docx não trata de forma confiável) e preserva a
formatação de cada run intocado, o que é exatamente o que
`normalizador.py` precisa para gerar um documento fiel ao modelo.

Usamos `StrictUndefined` do Jinja2 para que um marcador sem valor
correspondente em `dados` estoure erro imediatamente, em vez de virar uma
lacuna vazia e silenciosa no documento final - mesma postura de segurança
do mecanismo anterior.
"""
from __future__ import annotations

from pathlib import Path

from docxtpl import DocxTemplate
from jinja2 import Environment, StrictUndefined

from .cabecalho_layout import padronizar_brasao_esquerda, padronizar_carimbo_direita
from .fonte_miv import aplicar_padrao_miv


def preencher_docx(caminho_template: Path | str, dados: dict, caminho_saida: Path | str) -> None:
    """Preenche `caminho_template` com `dados` e salva em `caminho_saida`.

    Levanta erro (via StrictUndefined) se o template contiver um marcador
    `{{ campo }}` sem chave correspondente em `dados` - isso indica
    dessincronia entre o template normalizado e o módulo `campos_*.py`
    correspondente, e deve ser corrigido no código, não escondido.

    Após o merge, aplica o padrão do MIV (fonte Rawline, margens,
    entrelinhas 1,5 e parágrafo moderno) - a padronização preserva o
    conteúdo, o padrão de negrito e o alinhamento herdados do modelo.

    O carimbo (imagem flutuante do cabeçalho) é padronizado à DIREITA DEPOIS
    de salvar (ver `cabecalho_layout.padronizar_carimbo_direita`): alterações
    em cabeçalho/rodapé feitas no objeto em memória, depois do `render()` do
    docxtpl, não são persistidas por `modelo.save()`. Já o brasão (imagem
    inline no corpo) é padronizado à ESQUERDA em memória, antes de salvar.
    """
    modelo = DocxTemplate(str(caminho_template))
    jinja_env = Environment(undefined=StrictUndefined)
    modelo.render(dados, jinja_env=jinja_env)

    # Usa o atributo `.docx` (documento já renderizado). NÃO usar `get_docx()`
    # aqui: ele chama init_docx(reload=True), que recarrega o template cru e
    # descartaria tanto o merge quanto a formatação aplicada abaixo.
    aplicar_padrao_miv(modelo.docx)
    padronizar_brasao_esquerda(modelo.docx)

    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    modelo.save(str(caminho_saida))

    padronizar_carimbo_direita(caminho_saida)
