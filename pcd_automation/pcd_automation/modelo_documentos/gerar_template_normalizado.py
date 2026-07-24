"""Gera os templates normalizados (com marcadores Jinja2 `{{ campo }}`) a
partir dos modelos originais em branco fornecidos pela unidade.

Os modelos originais usam preenchimento manual ("XX", "FULANO DE TAL",
etc.). O autor do modelo, ao preencher manualmente esses blancos,
frequentemente os deixou em um "run" (bloco de formatação) próprio dentro
do parágrafo - geralmente em negrito, distinto do texto fixo ao redor.
Por isso a normalização troca o texto **apenas dos runs que já eram os
blancos** por marcadores, preservando 100% da formatação original nos
demais runs (ver `normalizador.py`). O merge dos dados é feito depois pelo
`docxtpl` (ver `preenchedor.py`), que respeita essa formatação por run.

Este script roda uma única vez por modelo e produz uma cópia normalizada;
rode de novo apenas se o modelo original correspondente mudar.
"""
from __future__ import annotations

from pathlib import Path

from .normalizador import SubstituicaoParagrafo, gerar_normalizado

RAIZ_MODELOS = Path(__file__).resolve().parents[3] / "Modelo Processo-Procedimento" / "PCD"
DIR_TEMPLATES = Path(__file__).resolve().parent / "templates"


def _paragrafo_uniforme(ancora: str, texto_novo: str) -> SubstituicaoParagrafo:
    """Para parágrafos em que o texto inteiro já está num único run (ou em
    runs com a MESMA formatação), não há nada a preservar seletivamente -
    substituir o parágrafo inteiro é seguro. Isso só funciona de verdade
    quando o parágrafo tem 1 run só; se tiver mais de um, `gerar_normalizado`
    vai lançar erro (nenhum run individual bate com o texto completo do
    parágrafo) - o que sinaliza exatamente quais parágrafos precisam da
    forma explícita `[(texto_do_run, texto_novo_do_run), ...]` abaixo, em
    vez de arriscar perder formatação em silêncio.
    """
    return (ancora, [(ancora, texto_novo)])


def _colapsar(runs_originais: list[str], texto_novo: str) -> list[tuple[str, str]]:
    """Para um SPAN de runs adjacentes que já compartilham a mesma
    formatação (sem negrito seletivo a preservar entre eles), concatena o
    texto novo inteiro no primeiro run do span e esvazia os demais."""
    if not runs_originais:
        return []
    return [(runs_originais[0], texto_novo)] + [(r, "") for r in runs_originais[1:]]


# ============================================================
# Despacho de Instauração
# ============================================================
# Modelo original: a versão sem sufixo é um exemplo já preenchido; "(1)" é
# a versão em branco de verdade. O autor negritou especificamente os
# blancos ("XX", "CIDADE" etc.), deixando rótulos e texto de conexão sem
# negrito - por isso a maioria dos parágrafos abaixo usa a forma explícita
# de runs, não `_paragrafo_uniforme`.
ORIGEM_DESPACHO = RAIZ_MODELOS / "Modelo Despacho de Instauração(1).docx"
DESTINO_DESPACHO = DIR_TEMPLATES / "despacho_instauracao.docx"

SUBSTITUICOES_PARAGRAFO_DESPACHO: list[SubstituicaoParagrafo] = [
    _paragrafo_uniforme(
        "PROCESSO DE COMUNICAÇÃO DISCIPLINAR Nº                       /        .",
        "PROCESSO DE COMUNICAÇÃO DISCIPLINAR Nº {{ numero_processo }}/{{ ano_processo }}.",
    ),
    _paragrafo_uniforme(
        "Ao: Nº XXX.XXX-X, posto/graduação PM FULANO DE TAL, do X BPM",
        "Ao: Nº {{ re_autoridade_processante }}, {{ posto_autoridade_processante }} PM "
        "{{ nome_autoridade_processante }}, do {{ unidade_autoridade_processante }}",
    ),
    (
        "Anexo: Comunicação Disciplinar n.___, contendo ____ fls.  ",
        [
            (
                "Anexo: Comunicação Disciplinar n.___, contendo ____ fls. ",
                "Anexo: Comunicação Disciplinar n.{{ numero_comunicacao_disciplinar }}, "
                "contendo {{ numero_folhas_anexo }} fls.",
            ),
            (" ", ""),
        ],
    ),
    _paragrafo_uniforme(
        "Encaminho-lhe o documento anexo, para que, nos termos do art. 37 do Manual de "
        "Processos e Procedimentos Administrativos (MAPPA), aprovado pela Resolução "
        "Conjunta nº 4.220, de 28jun12, esse encarregado proceda à elaboração do "
        "Processo de Comunicação Disciplinar em face do nº XXX.XXX-X, POSTO/GRADUAÇÃO "
        "PM FULANO DE TAL, pelo cometimento, em tese, da transgressão disciplinar "
        "abaixo descrita:",
        "Encaminho-lhe o documento anexo, para que, nos termos do art. 37 do Manual de "
        "Processos e Procedimentos Administrativos (MAPPA), aprovado pela Resolução "
        "Conjunta nº 4.220, de 28jun12, esse encarregado proceda à elaboração do "
        "Processo de Comunicação Disciplinar em face do nº {{ re_sindicado }}, "
        "{{ posto_graduacao_sindicado_upper }} PM {{ nome_sindicado_upper }}, pelo "
        "cometimento, em tese, da transgressão disciplinar abaixo descrita:",
    ),
    (
        "Síntese do fato: no dia XX do ano de 20XX, na cidade de XXXXXX, por volta das "
        "XX horas, teria o comunicado (descrever sinteticamente o fato ocorrido).",
        [
            ("XX ", "{{ dia_fato }} "),
            ("XX", "{{ ano_fato_sufixo }}"),
            ("XXXXXX", "{{ cidade_fato }}"),
            ("XX", "{{ hora_fato }}"),
            ("(descrever sinteticamente o fato ocorrido)", "{{ resumo_fato }}"),
        ],
    ),
    (
        "Transgressão disciplinar, em tese, cometida: inciso XX, do art. XX do CEDM",
        [(": inciso XX, do art. XX do CEDM", ": {{ tipificacao_cedm }}")],
    ),
    # "Prazo: 15 (quinze) dias corridos..." - texto fixo, confirmado com o
    # usuário, sem marcador nenhum. Nenhuma entrada aqui de propósito.
    (
        "Quartel em CIDADE, XX de XXXXXX de 202X.",
        [
            ("CIDADE", "{{ cidade_sede }}"),
            ("XX", "{{ dia_instauracao }}"),
            ("XXXXXX", "{{ mes_instauracao_extenso }}"),
            # O modelo fixa "202" e só negrita o último dígito do ano - ou
            # seja, o modelo original só suporta datas em 202X (2020-2029).
            # `campos_despacho.py` valida isso e sinaliza [PREENCHER] fora
            # dessa década, em vez de gerar uma data errada em silêncio.
            ("X.", "{{ ano_instauracao_ultimo_digito }}."),
        ],
    ),
    _paragrafo_uniforme(
        "AUTORIDADE MILITAR",
        "{{ posto_autoridade_delegante }} PM {{ nome_autoridade_delegante }} - Autoridade Delegante",
    ),
]

SUBSTITUICOES_TABELA_DESPACHO = [
    (2, 1, "XXX REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "XXX BATALHÃO DE POLÍCIA MILITAR", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]


# ============================================================
# Os demais 8 documentos ainda usam a forma "parágrafo uniforme" (herdada
# da versão anterior do normalizador, sem preservação de negrito seletivo
# dentro do parágrafo) - ver task de acompanhamento para migrá-los ao
# mesmo padrão do Despacho acima, run a run.
# ============================================================

# --- Termo de Abertura de Vista Final (RED) ---
ORIGEM_VISTA_FINAL = RAIZ_MODELOS / "15 Modelo Termo de Abertura de Vista Final.docx"
DESTINO_VISTA_FINAL = DIR_TEMPLATES / "termo_abertura_vista_final.docx"

SUBSTITUICOES_PARAGRAFO_VISTA_FINAL: list[SubstituicaoParagrafo] = [
    (
        "Anexo(s): Cópia dos autos da portaria nº XXX.XXX/202X – XXXBPM PCD ",
        [
            (
                ": Cópia dos autos da portaria nº XXX.XXX/202",
                ": Cópia dos autos da portaria nº {{ numero_processo }}/{{ ano_processo }} – "
                "{{ numero_batalhao_pm }}º BPM",
            ),
            ("X", ""),
            (" – ", ""),
            ("XXX", ""),
            ("BP", ""),
            ("M", ""),
        ],
    ),
    (
        "Aos XX dias do mês de XX do ano de 2022, nesta cidade de  XXXXXXX, Estado de "
        "Minas Gerais, no Quartel do Xº BPM, onde eu, Fulano de Tal, posto/graduação PM, "
        "encarregado do processo, encontrava-me, compareceu o nº XXX.XXX-X, "
        "posto/graduação PM Fulano de Tal, lotado no BPTRAN, ao qual foi feita a "
        "abertura de vista da comunicação disciplinar anexa, contendo XX fls., "
        "numeradas de XX a XX, nos termos do inciso LV, do art. 5º, da Constituição "
        "Federal, e em observância ao art. 37 do MAPPA, que asseguram o amplo direito "
        "de defesa e do exercício do contraditório, e, considerando que o militar "
        "supracitado cometeu em tese, atos que configuram transgressão disciplinar, "
        "especificada no inciso XXX do art. XX do Código de Ética e Disciplina dos "
        "Militares, conforme síntese abaixo:",
        [
            ("XX", "{{ dia_citacao }}"),
            ("dias do mês de ", "dias do mês de "),
            ("XX", "{{ mes_citacao_extenso }}"),
            (
                " do ano de 2022, nesta cidade de ",
                " do ano de {{ ano_citacao }}, nesta cidade de ",
            ),
            (" XXXXXXX", "{{ cidade_sede }}"),
            (", Estado de Minas Gerais, no Quartel do", ", Estado de Minas Gerais, no Quartel do"),
            ("Xº ", "{{ numero_batalhao_pm }}º "),
            (", onde eu, ", ", onde eu, "),
            ("Fulano de Tal", "{{ nome_autoridade_processante }}"),
            (", ", ", "),
            ("posto/graduação", "{{ posto_autoridade_processante }}"),
            (" nº ", " nº "),
            ("XXX.XXX-X", "{{ re_sindicado }}"),
            (", ", ", "),
            ("posto/graduação", "{{ posto_graduacao_sindicado }}"),
            ("Fulano de Tal", "{{ nome_sindicado }}"),
            (", lotado no ", ", lotado no "),
            ("BPTRAN", "{{ unidade_sindicado }}"),
            ("XX", "{{ numero_folhas_anexo }}"),
            ("XX", "{{ numero_folha_inicial }}"),
            ("XX", "{{ numero_folha_final }}"),
            ("XXX", "{{ numero_inciso_cedm }}"),
            ("XX", "{{ numero_artigo_cedm }}"),
        ],
    ),
    (
        "“No dia X, do ano de XXXX, na cidade de XXXXXXXXX, por volta das XX:XX horas, "
        "o comunicado (motivar adequadamente a conduta praticada).” Posto isto, "
        "encontra-se esse comunicado incurso, em tese, no inciso XXX do art. XX do CEDM.",
        [
            ("No dia ", "No dia "),
            ("X", "{{ dia_fato }}"),
            (", do ano de ", ", do ano de "),
            ("XXXX", "{{ ano_fato }}"),
            (", na cidade de ", ", na cidade de "),
            ("XXXXXXXXX", "{{ cidade_fato }}"),
            (" XX:XX ", " {{ hora_fato }} "),
            (
                "horas, o comunicado (motivar adequadamente a conduta praticada).",
                "horas, o comunicado {{ resumo_fato }}.",
            ),
            (" XXX", " {{ numero_inciso_cedm }}"),
            ("XX", "{{ numero_artigo_cedm }}"),
        ],
    ),
    (
        "Quartel em Belo Horizonte, XX de XXXXX de 2022.",
        _colapsar(
            ["Quartel em Belo Horizonte, ", "XX ", "de XXXXX de 2022."],
            "Quartel em {{ cidade_sede }}, {{ data_citacao_extenso }}.",
        ),
    ),
]

SUBSTITUICOES_TABELA_VISTA_FINAL = [
    (2, 1, "XXXX REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "XXX BATALHÃO DE POLÍCIA MILITAR", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]

# --- Termo de Abertura de Vista Inicial (defesa prévia) ---
# Os dois arquivos originais desse modelo não são utilizáveis como fonte
# (ver histórico) - este template é derivado do normalizado do Vista
# Final, trocando só o título.
DESTINO_VISTA_INICIAL = DIR_TEMPLATES / "termo_abertura_vista_inicial.docx"

SUBSTITUICOES_PARAGRAFO_VISTA_INICIAL: list[SubstituicaoParagrafo] = [
    (
        "APRESENTAÇÃO DAS RAZÕES ESCRITAS DE DEFESA FINAL (RED)",
        _colapsar(
            ["APRESENTAÇÃO DAS ", "RAZÕES ESCRITAS ", "DE DEFESA", " FINAL (RED)"],
            "APRESENTAÇÃO DAS ALEGAÇÕES DE DEFESA",
        ),
    ),
]


# --- Comunicação Disciplinar ---
# "(1)" é a versão em branco (com placeholders "XXX.XXX-X"/"FULANO"); inclui
# bloco de testemunha, ao contrário da versão base.
ORIGEM_COMUNICACAO = RAIZ_MODELOS / "Modelo Comunicação Disciplinar(1).docx"
DESTINO_COMUNICACAO = DIR_TEMPLATES / "comunicacao_disciplinar.docx"

SUBSTITUICOES_PARAGRAFO_COMUNICACAO: list[SubstituicaoParagrafo] = [
    (
        "COMUNICAÇÃO DISCIPLINAR Nº 03/2026                    ",
        [("COMUNICAÇÃO DISCIPLINAR Nº 03/2026", "COMUNICAÇÃO DISCIPLINAR Nº {{ numero_comunicacao_disciplinar }}")],
    ),
    (
        "Ao Sr. Ten Cel PM Comandante do 33° BPM",
        [("Ten Cel PM Comandante do 33° BPM", "Ten Cel PM Comandante do {{ numero_batalhao_pm }}° BPM")],
    ),
    (
        "Anexos: Escala de Serviço, contendo 1 fls.",
        [
            (
                "Escala de Serviço, contendo 1 fls.",
                "Escala de Serviço, contendo {{ numero_folhas_escala_servico }} fls.",
            )
        ],
    ),
    _paragrafo_uniforme(
        "UNIDADE: 33º BPM \tNÚMERO: \t999.999-9\tP/G: CB PM",
        "UNIDADE: {{ unidade_sindicado }} \tNÚMERO: \t{{ re_sindicado }}\tP/G: {{ posto_graduacao_sindicado }}",
    ),
    _paragrafo_uniforme("NOME: JOSÉ CURIOSO", "NOME: {{ nome_sindicado_upper }}"),
    _paragrafo_uniforme("DIA: 28/07/2025\tHORA: 12H03MIN", "DIA: {{ data_fato_barra }}\tHORA: {{ hora_fato }}"),
    _paragrafo_uniforme("LOCAL: Sede do 34º BPM ", "LOCAL: {{ local_fato }}"),
    (
        "SÍNTESE: Comunico a V. Sa. que o militar supracitado, estando de serviço na SOU "
        "do 34º BPM, foi avistado por este comunicante sozinho dentro da sala do Núcleo "
        "de Justiça e Disciplina desta unidade, sentado em frente a um dos computadores, "
        "e que ao me aproximar, verifiquei que ele pesquisava na aba do SICOR os dados "
        "do 1º SGT Roberto Carlos, militar lotado na 21ª Cia do 34º BPM.",
        [
            (
                " Comunico a V. Sa. que o militar supracitado, estando de serviço na SOU do 34º "
                "BPM, foi avistado por este comunicante sozinho dentro da sala do Núcleo de "
                "Justiça e Disciplina desta unidade, sentado em frente a um dos computadores, e "
                "que ao me aproximar, verifiquei que ele pesquisava na aba do SICOR os dados do "
                "1º SGT Roberto Carlos, militar lotado na 21ª Cia do 34º BPM.",
                " Comunico a V. Sa. que o militar supracitado, {{ resumo_fato }}.",
            )
        ],
    ),
    _paragrafo_uniforme(
        "UNIDADE:\t34ºBPM\tNÚMERO: \t222.222-2\tP/G: SD PM",
        "UNIDADE:\t{{ unidade_testemunha }}\tNÚMERO: \t{{ re_testemunha }}\tP/G: {{ posto_testemunha }}",
    ),
    _paragrafo_uniforme("NOME: DAVI SANTOS", "NOME: {{ nome_testemunha_upper }}"),
    (
        "BENS/DOCUMENTOS RELACIONADOS: ",
        [("BENS/DOCUMENTOS RELACIONADOS: ", "BENS/DOCUMENTOS RELACIONADOS: {{ bens_documentos_relacionados }}")],
    ),
    _paragrafo_uniforme(
        "UNIDADE:\t34º\tNÚMERO: \t333.333~3\tP/G: 1º TEN PM",
        "UNIDADE:\t{{ unidade_comunicante }}\tNÚMERO: \t{{ re_comunicante }}\tP/G: {{ posto_comunicante }}",
    ),
    _paragrafo_uniforme("NOME: JONAS RODRIGUES", "NOME: {{ nome_comunicante_upper }}"),
    (
        "Quartel em Belo Horizonte, 01/08/2025.",
        _colapsar(
            ["Quartel em Belo Horizonte, ", "01/08/2025", "."],
            "Quartel em {{ cidade_sede }}, {{ data_comunicacao_barra }}.",
        ),
    ),
    _paragrafo_uniforme("JONAS RODRIGUES, 1º TEN PM", "{{ nome_comunicante_upper }}, {{ posto_comunicante }} PM"),
]

SUBSTITUICOES_TABELA_COMUNICACAO = [
    (2, 1, "PRIMEIRA REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "TRIGÉSIMO QUARTO BATALHÃO DE POLÍCIA MILITAR", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]


# --- Notificação de Comparecimento de Testemunha (convoca a testemunha) ---
ORIGEM_NOTIFICACAO_TESTEMUNHA = (
    RAIZ_MODELOS / "Modelo Notificação de Comparecimento Testemunha de ACUSAÇÃO-DEFESA(1).docx"
)
DESTINO_NOTIFICACAO_TESTEMUNHA = DIR_TEMPLATES / "notificacao_testemunha.docx"

SUBSTITUICOES_PARAGRAFO_NOTIFICACAO_TESTEMUNHA: list[SubstituicaoParagrafo] = [
    _paragrafo_uniforme(
        "Belo Horizonte, 11 de julho de 2025.",
        "{{ cidade_sede }}, {{ data_notificacao_testemunha_extenso }}.",
    ),
    (
        "Conforme delegação do Sr. Ten-Cel PM Jhon Logan Cmt do 36° BPM para investigar "
        "eventual cometimento de transgressão disciplinar praticada por policial militar "
        "desta unidade, solicito o comparecimento do policial militar Nº 048.345-6 , CB PM "
        "CHUCK NORRIS, lotado no 36° BPM no dia 15/07/2026, às 13:00 horas a sede do 36° "
        "BPM, situado a Rua Sao Paulo, Celvia, em Vespasiano, para ser ouvido na condição "
        "de testemunha.",
        [
            (
                "Ten-Cel PM Jhon Logan Cmt do 36° BPM",
                "{{ posto_autoridade_delegante }} PM {{ nome_autoridade_delegante }} "
                "Cmt do {{ numero_batalhao_pm }}° BPM",
            ),
            (
                "Nº 048.345-6 , CB PM CHUCK NORRIS",
                "Nº {{ re_testemunha }} , {{ posto_testemunha }} PM {{ nome_testemunha_upper }}",
            ),
            (
                ", lotado no 36° BPM no dia 15/07/2026, às 13:00 horas a sede do 36° "
                "BPM, situado a Rua Sao Paulo, Celvia, em Vespasiano, para ser ouvido na condição "
                "de testemunha.",
                ", lotado no {{ unidade_testemunha }} no dia {{ data_oitiva_barra }}, às "
                "{{ hora_oitiva }} horas a sede do {{ numero_batalhao_pm }}° BPM, situado a "
                "{{ endereco_sede }}, para ser ouvido na condição de testemunha.",
            ),
        ],
    ),
    _paragrafo_uniforme(
        "VICTOR STONE, SGT PM", "{{ nome_autoridade_processante_upper }}, {{ posto_autoridade_processante }} PM"
    ),
    _paragrafo_uniforme("CHUCK NORRIS CB PM", "{{ nome_testemunha_upper }} {{ posto_testemunha }} PM"),
    (
        "RECEBI uma via desta notificação, em 11/07/2026.",
        [
            (
                "uma via desta notificação, em 11/07/2026.",
                "uma via desta notificação, em {{ data_notificacao_testemunha_barra }}.",
            )
        ],
    ),
]

SUBSTITUICOES_TABELA_NOTIFICACAO_TESTEMUNHA = [
    (2, 1, "PRIMEIRA REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "36º BATALHÃO DE POLÍCIA MILITAR", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]

# --- Notificação do Sindicado/Defensor para conhecimento da audição de testemunhas ---
# "(1)" é a versão em branco de verdade (placeholders "XXX.XXX-X").
ORIGEM_NOTIFICACAO_SINDICADO = RAIZ_MODELOS / "Modelo Termo de Notificação testemunha de ACUSAÇÃO-DEFESA(1).docx"
DESTINO_NOTIFICACAO_SINDICADO = DIR_TEMPLATES / "notificacao_sindicado_audicao.docx"

SUBSTITUICOES_PARAGRAFO_NOTIFICACAO_SINDICADO: list[SubstituicaoParagrafo] = [
    _paragrafo_uniforme(
        "Ao: XXX.XXX-X, Posto/graduação PM Fulano de Tal ou Defensor",
        "Ao: {{ re_sindicado }}, {{ posto_graduacao_sindicado }} PM {{ nome_sindicado }} ou Defensor",
    ),
    _paragrafo_uniforme(
        "Ref.: despacho nº XXX.XXX/2022 – x BPM PCD:",
        "Ref.: despacho nº {{ numero_processo }}/{{ ano_processo }} – {{ numero_batalhao_pm }} BPM PCD:",
    ),
    (
        "Notifico-lhe a comparecer, facultativamente, no dia XX de XXXXXXX de XXXX, as XX:XX "
        "horas, na sede do X BPM, a fim de assistir a audição da testemunha Posto/graduação PM "
        "FULANO DE TAL (OU OUTRA PESSOA – ESPECIFICAR) sobre os fatos constantes no PCD de "
        "portaria n° XXX.XXX/2022, na qual esse militar encontra-se na condição de TESTEMUNHA, "
        "ocasião em que poderá assistir ao referido depoimento, diretamente ou através de "
        "defensor constituído, fazer perguntas ou questionamentos pertinentes.",
        [
            (
                "Notifico-lhe a comparecer, facultativamente, no dia XX de XXXXXXX de XXXX, as XX:XX "
                "horas, na sede do X BPM, a fim de assistir a audição da testemunha ",
                "Notifico-lhe a comparecer, facultativamente, no dia {{ dia_oitiva }} de "
                "{{ mes_oitiva_extenso }} de {{ ano_oitiva }}, as {{ hora_oitiva }} horas, na sede do "
                "{{ numero_batalhao_pm }} BPM, a fim de assistir a audição da testemunha ",
            ),
            ("Posto/graduação PM FULANO DE TAL", "{{ posto_testemunha }} PM {{ nome_testemunha_upper }}"),
            ("(OU OUTRA PESSOA – ESPECIFICAR)", ""),
            (
                " sobre os fatos constantes no PCD de portaria n° XXX.XXX/2022, na qual esse militar "
                "encontra-se na condição de TESTEMUNHA, ocasião em que poderá assistir ao referido "
                "depoimento, diretamente ou através de defensor constituído, fazer perguntas ou "
                "questionamentos pertinentes.",
                " sobre os fatos constantes no PCD de portaria n° {{ numero_processo }}/{{ ano_processo }}, "
                "na qual esse militar encontra-se na condição de TESTEMUNHA, ocasião em que poderá "
                "assistir ao referido depoimento, diretamente ou através de defensor constituído, "
                "fazer perguntas ou questionamentos pertinentes.",
            ),
        ],
    ),
    _paragrafo_uniforme(
        "Quartel em Belo Horizonte, 02 de outubro de 2025.",
        "Quartel em {{ cidade_sede }}, {{ data_notificacao_sindicado_extenso }}.",
    ),
    (
        "RECEBI a uma via desta notificação, em XX/XX/2022, e demais documentos juntados, e "
        "estou ciente de seu conteúdo.",
        [
            (
                "a uma via desta notificação, em XX/XX/2022, e demais documentos juntados, e "
                "estou ciente de seu conteúdo",
                "a uma via desta notificação, em {{ data_notificacao_sindicado_barra }}, e demais "
                "documentos juntados, e estou ciente de seu conteúdo",
            ),
        ],
    ),
    _paragrafo_uniforme(
        "FULANO DE TAL, POSTO/GRADUAÇÃO PM", "{{ nome_autoridade_processante }}, {{ posto_autoridade_processante }} PM"
    ),
    _paragrafo_uniforme("FULANO DE TAL", "{{ nome_sindicado }}"),
]

SUBSTITUICOES_TABELA_NOTIFICACAO_SINDICADO = [
    (2, 1, "PRIMEIRA REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "BATALHÃO DE POLÍCIA DE TRÂNSITO", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]


# --- Termo de Depoimento de Testemunha ---
# "Termo de depoimento Testemunha.docx" (sem sufixo "de ACUSAÇÃO-DEFESA") é
# o modelo em branco de verdade (com placeholders "XX"); ainda existe.
ORIGEM_DEPOIMENTO = RAIZ_MODELOS / "Termo de depoimento Testemunha.docx"
DESTINO_DEPOIMENTO = DIR_TEMPLATES / "termo_depoimento_testemunha.docx"

SUBSTITUICOES_PARAGRAFO_DEPOIMENTO: list[SubstituicaoParagrafo] = [
    (
        "TERMO DE DEPOIMENTO DA Xº TESTEMUNHA",
        _colapsar(
            ["TERMO DE DE", "POIMENTO", " DA", " ", "X", "º", " TESTEMUNHA"],
            "TERMO DE DEPOIMENTO DA {{ numero_ordem_testemunha }}º TESTEMUNHA",
        ),
    ),
    (
        "Local: Quartel do BPTran em Belo Horizonte/MG.",
        _colapsar(
            ["Local: Quartel do ", "BPTran", " em Belo Horizonte/MG."],
            "Local: Quartel do {{ numero_batalhao_pm }}º BPM em {{ cidade_sede }}/MG.",
        ),
    ),
    _paragrafo_uniforme(
        "Data da oitiva: XX/XX/202X – XXXXXX-feira.",
        "Data da oitiva: {{ data_oitiva_barra }} – {{ dia_semana_oitiva }}.",
    ),
    _paragrafo_uniforme(
        "Nome do sindicante: Fulano de Tal, Posto/Graduação PM",
        "Nome do sindicante: {{ nome_autoridade_processante }}, {{ posto_autoridade_processante }} PM",
    ),
    ("Nome: FULANO DE TAL", [("FULANO DE TAL", "{{ nome_testemunha_upper }}")]),
    _paragrafo_uniforme(
        "Profissão: Policial Militar Posto/graduação: XXX PM nº: XXX.XXX-X",
        "Profissão: Policial Militar Posto/graduação: {{ posto_testemunha }} PM nº: {{ re_testemunha }}",
    ),
    _paragrafo_uniforme("Pai: Fulano de Tal", "Pai: {{ nome_pai_testemunha }}"),
    _paragrafo_uniforme("Mãe: Fulana de Tal", "Mãe: {{ nome_mae_testemunha }}"),
    (
        "Idade: XX \t\t\tData de nascimento: XX/XX/XXXX Sexo: XXXXX",
        _colapsar(
            ["Idade: XX ", "\t", "\t", "\tData de nascimento: XX/XX/XXXX Sexo: XXXXX"],
            "Idade: {{ idade_testemunha }} \t\t\tData de nascimento: {{ data_nascimento_testemunha_barra }} "
            "Sexo: {{ sexo_testemunha }}",
        ),
    ),
    (
        "Nacionalidade: Brasileira \tNaturalidade: XXXXXXX",
        _colapsar(
            ["Nacionalidade: Brasileira ", "\tNaturalidade: XXXXXXX"],
            "Nacionalidade: {{ nacionalidade_testemunha }} \tNaturalidade: {{ naturalidade_testemunha }}",
        ),
    ),
    _paragrafo_uniforme("Estado civil: XXXXXXXXXX", "Estado civil: {{ estado_civil_testemunha }}"),
    _paragrafo_uniforme(
        "CPF: XXX.XXX.XXX-XX Identidade: XXXXXXX",
        "CPF: {{ cpf_testemunha }} Identidade: {{ identidade_testemunha }}",
    ),
    _paragrafo_uniforme(
        "Local de trabalho: Avenida Amazonas, 6227, Bairro Gameleira, Belo Horizonte/MG",
        "Local de trabalho: {{ local_trabalho_testemunha }}",
    ),
    _paragrafo_uniforme(
        "Tel. celular: (0XX) XXXXX-XXXX Tel. Residencial: (0XX) XXXXX-XXXX Tel. comercial: (0XX) XXXXX-XXXX",
        "Tel. celular: {{ telefone_celular_testemunha }} Tel. Residencial: {{ telefone_residencial_testemunha }} "
        "Tel. comercial: {{ telefone_comercial_testemunha }}",
    ),
    _paragrafo_uniforme("Escolaridade: XXXXXXXXX", "Escolaridade: {{ escolaridade_testemunha }}"),
    (
        "INQUIRIDO acerca dos fatos constantes da portaria nº XXX.XXX que lhe foi lida, respondeu: "
        "QUE transcrever as respostas da maneira mais clara possível e da maneira mais idêntica "
        "possível à fala do interrogado. Dada a palavra à defesa, pelo defensor foi perguntado "
        "(...). Nada mais disse nem lhe foi perguntado e para constar, lavrei este termo que, "
        "iniciado as XX:XX horas foi encerrado às XX:XX horas do mesmo dia, o qual depois de lido "
        "e achado conforme, vai assinado. O sindicado (e seu defensor, caso tenha sido "
        "constituído) fica(m), ainda, desde já, NOTIFICADO(S) a acompanhar(em), facultativamente, "
        "a audição das testemunhas (ou outras",
        [
            ("º XXX.XXX", "º {{ numero_processo }}/{{ ano_processo }}"),
            (
                "transcrever as respostas da maneira mais clara possível e da maneira mais idêntica "
                "possível à fala do interrogado",
                "{{ teor_depoimento }}",
            ),
            (
                "pelo defensor foi perguntado (...). Nada mais disse nem lhe foi perguntado e para "
                "constar, lavrei este termo que, iniciado as XX:XX horas foi encerrado às XX:XX "
                "horas do mesmo dia, o qual depois de lido e achado conforme, vai assinado. O "
                "sindicado (e seu defensor, caso tenha sido constituído) fica(m), ainda, desde já, "
                "NOTIFICADO(S) a acompanhar(em), facultativamente, a audição das testemunhas (ou outras",
                "pelo defensor foi perguntado (...). Nada mais disse nem lhe foi perguntado e para "
                "constar, lavrei este termo que, iniciado as {{ hora_inicio_depoimento }} horas foi "
                "encerrado às {{ hora_fim_depoimento }} horas do mesmo dia, o qual depois de lido e "
                "achado conforme, vai assinado. O sindicado (e seu defensor, caso tenha sido "
                "constituído) fica(m), ainda, desde já, NOTIFICADO(S) a acompanhar(em), "
                "facultativamente, a audição das testemunhas (ou outras",
            ),
        ],
    ),
    (
        "pessoas, especificar), que ocorrerá no próximo dia ___/ ____/ _______, às _____ horas, "
        "no (especificar o local).",
        [
            (
                ", especificar), que ocorrerá no próximo dia ___/ ____/ _______, às _____ horas, "
                "no (especificar o local).",
                ", especificar), que ocorrerá no próximo dia {{ data_proxima_oitiva }}, às "
                "{{ hora_proxima_oitiva }} horas, no {{ local_proxima_oitiva }}.",
            ),
        ],
    ),
]
# "FULANO DE TAL, POSTO/GRADUAÇÃO PM" se repete 3x (testemunha, sindicado,
# sindicante/encarregado) - a fila em `_substituir_runs` consome cada
# ocorrência na ordem em que aparece no documento.
SUBSTITUICOES_PARAGRAFO_DEPOIMENTO += [
    _paragrafo_uniforme("FULANO DE TAL, POSTO/GRADUAÇÃO PM", "{{ nome_testemunha_upper }}, {{ posto_testemunha }} PM"),
    _paragrafo_uniforme(
        "FULANO DE TAL, POSTO/GRADUAÇÃO PM", "{{ nome_sindicado }}, {{ posto_graduacao_sindicado }} PM"
    ),
    _paragrafo_uniforme("FULANO DE TAL", "{{ nome_defensor_sindicado }}"),
    _paragrafo_uniforme(
        "FULANO DE TAL, POSTO/GRADUAÇÃO PM", "{{ nome_autoridade_processante }}, {{ posto_autoridade_processante }} PM"
    ),
]

SUBSTITUICOES_TABELA_DEPOIMENTO = [
    (2, 1, "PRIMEIRA REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "BATALHÃO DE POLÍCIA DE TRÂNSITO", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]


# --- Relatório do Encarregado ---
# Único arquivo existente para este modelo (exemplo já preenchido, caso
# "JASON TODDY"). As seções 2 (fatos/provas), 3 (alegações de defesa) e o
# parecer (seção 6) são análise e julgamento jurídico do encarregado - não
# são adivinhadas pelo sistema, apenas marcadas [PREENCHER] quando ausentes.
ORIGEM_RELATORIO = RAIZ_MODELOS / "Modelo Relatório do encarregado.docx"
DESTINO_RELATORIO = DIR_TEMPLATES / "relatorio_encarregado.docx"

SUBSTITUICOES_PARAGRAFO_RELATORIO: list[SubstituicaoParagrafo] = [
    (
        "a. Processo de Comunicação Disciplinar n° 07081982, de 10/07/2026. ",
        _colapsar(
            ["a. Processo de Comunicação Disciplinar n° ", "07081982", ", de ", "10", "/", "07", "/", "2026", ". "],
            "a. Processo de Comunicação Disciplinar n° {{ numero_comunicacao_disciplinar }}, "
            "de {{ data_comunicacao_barra }}.",
        ),
    ),
    (
        "N° 123456-7, CBPM JASON TODDY, Art. 15 Inciso V do CEDM;  ",
        _colapsar(
            ["N° ", "123456-7", ",", " CB", "PM ", "JASON TODDY", ", Art. ", "15", " Inciso ", "V", " do CEDM;  "],
            "N° {{ re_sindicado }}, {{ posto_graduacao_sindicado }} PM {{ nome_sindicado_upper }}, "
            "{{ tipificacao_cedm }};",
        ),
    ),
    (
        "c. Fato: Este Processo de Comunicação Disciplinar teve por finalidade apurar "
        "transgressão disciplinar em tese cometida no dia 09 de julho do ano de 2025, na "
        "cidade de Vespasiano Horizonte, por volta das 15h00min, onde teria o comunicado:  "
        "utilizando uma camisa de cor branca com inscrições referentes ao Curso Tático "
        "Móvel, sem qualquer tipo de identificação do nome funcional . ",
        [
            ("09 ", "{{ dia_fato }} "),
            ("julho", "{{ mes_fato_extenso }}"),
            ("5", "{{ ano_fato_ultimo_digito }}"),
            ("Vespasiano", "{{ cidade_fato }}"),
            # "Horizonte" aqui é resíduo do exemplo original (a cidade foi
            # trocada para "Vespasiano" sem remover a palavra seguinte) -
            # removido por ser um resíduo, não um marcador de branco.
            (" Horizonte, por volta das ", ", por volta das "),
            ("15", "{{ hora_fato }}"),
            (
                " utilizando uma camisa de cor branca com inscrições referentes ao Curso Tático "
                "Móvel, sem qualquer tipo de identificação do nome funcional ",
                "{{ resumo_fato }}",
            ),
        ],
    ),
    (
        ". Local: Vespasiano, Data/hora: 101500JUL25 Em serviço? SIM",
        _colapsar(
            [". Local: ", "Vespasiano, ", "Data/hora: 1", "0150", "0", "JUL", "25 Em serviço? ", "SIM"],
            ". Local: {{ cidade_fato }}, Data/hora: {{ data_hora_militar_fato }} Em serviço? {{ em_servico_sindicado }}",
        ),
    ),
    (
        "Nº XXX.XXX-X, Posto/Graduação PM Fulano de Tal (fls.___)",
        _colapsar(
            ["Nº XXX.XXX-X", ", Posto/Graduação ", "PM Fulano de Tal (fls.___)"],
            "Nº {{ re_testemunha }}, {{ posto_testemunha }} PM {{ nome_testemunha_upper }} "
            "(fls.{{ numero_folha_depoimento_testemunha }})",
        ),
    ),
    (
        "g. Objetos apreendidos/arrecadados: (listar) ",
        _colapsar(
            ["g. Objetos apreendidos/arrecadados: (", "listar", ") "],
            "g. Objetos apreendidos/arrecadados: {{ objetos_apreendidos }}",
        ),
    ),
    _paragrafo_uniforme("h. Outras provas: (descrever e indicar fls.).  ", "h. Outras provas: {{ outras_provas }}"),
    _paragrafo_uniforme(
        "No dia / / , às _ horas, o PM/BM ... Relatar o que efetivamente ficou apurado, "
        "fazendo citações de declarações, provas, eliminando as contradições e agrupando as "
        "comprovações existentes, relatando a tese da defesa e suas considerações, "
        "argumentando todos os tópicos apresentados. Não fazer cópias integrais de "
        "depoimentos e declarações (“control C + control V”). O ideal é que, neste item, o "
        "encarregado, de maneira bem objetiva e motivada nas provas dos autos, descreva a "
        "síntese da acusação e do que foi apurado. Em regra não deve exceder a 20 (vinte) "
        "linhas cada”. ",
        "{{ analise_fatos_e_provas }}",
    ),
    _paragrafo_uniforme(
        "Descrever as teses de defesa e contra argumentá-las ou acatá-las, motivadamente. ",
        "{{ alegacoes_defesa_analise }}",
    ),
    _paragrafo_uniforme(
        "Descrever os prazos (prorrogações, sobrestamentos, renovações e outros incidentes).",
        "{{ incidentes_processuais }}",
    ),
    (
        "Nº XXX.XXX-X, Posto/Graduação PM Fulano de Tal, Art. XX, inciso XX do CEDM. ",
        _colapsar(
            ["Nº XXX.XXX-X", ", Posto/Graduação ", "PM Fulano de Tal", ", Art. XX, inciso XX do CEDM. "],
            "Nº {{ re_sindicado }}, {{ posto_graduacao_sindicado }} PM {{ nome_sindicado_upper }}, "
            "{{ tipificacao_cedm }}.",
        ),
    ),
    _paragrafo_uniforme(
        "Quartel em Belo Horizonte 18 de outubro de 2022. ", "Quartel em {{ cidade_sede }} {{ data_relatorio_extenso }}."
    ),
    _paragrafo_uniforme(
        "FULANO DE TAL, POSTO/GRADUAÇÃO PM", "{{ nome_autoridade_processante }}, {{ posto_autoridade_processante }} PM"
    ),
]

SUBSTITUICOES_TABELA_RELATORIO = [
    (2, 1, "3° REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "36°BATALHÃO DE POLÍCIA MILITAR", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]


# --- Ofício de Remessa ---
# "(1)" é a versão em branco (placeholders "(posto e nome)"/"XX").
ORIGEM_OFICIO = RAIZ_MODELOS / "Modelo Ofício de Remessa(1).docx"
DESTINO_OFICIO = DIR_TEMPLATES / "oficio_remessa.docx"

SUBSTITUICOES_PARAGRAFO_OFICIO: list[SubstituicaoParagrafo] = [
    (
        "Ofício n° 15/PCD 126515-2026",
        [("15/PCD 126515-2026", "{{ numero_oficio_remessa }}/PCD {{ numero_processo }}/{{ ano_processo }}")],
    ),
    _paragrafo_uniforme("Belo Horizonte, 21 de agosto de 2022.", "{{ cidade_sede }}, {{ data_oficio_remessa_extenso }}."),
    (
        "Ao: Sr. (posto e nome) - Autoridade Militar Delegante",
        [
            (
                "Sr. (posto e nome) - Autoridade Militar Delegante",
                "Sr. {{ posto_autoridade_delegante }} {{ nome_autoridade_delegante }} - Autoridade Militar Delegante",
            )
        ],
    ),
    (
        "Assunto: remessa de autos do PCD 101.101/2026.",
        [("remessa de autos do PCD 101.101/2026.", "remessa de autos do PCD {{ numero_processo }}/{{ ano_processo }}.")],
    ),
    (
        "Anexo: autos contendo um total de XX fls.",
        [
            (
                "autos contendo um total de XX fls.",
                "autos contendo um total de {{ numero_folhas_autos_final }} fls.",
            )
        ],
    ),
    _paragrafo_uniforme(
        "Ref.: Despacho 101.101-2026-PCD – Xº BPM",
        "Ref.: Despacho {{ numero_processo }}-{{ ano_processo }}-PCD – {{ numero_batalhao_pm }}º BPM",
    ),
    _paragrafo_uniforme(
        "NOME, POSTO/GRADUAÇÃO PM", "{{ nome_autoridade_processante }}, {{ posto_autoridade_processante }} PM"
    ),
]

SUBSTITUICOES_TABELA_OFICIO = [
    (2, 1, "PRIMEIRA REGIÃO DE POLÍCIA MILITAR", "{{ numero_regiao_pm }}ª REGIÃO DE POLÍCIA MILITAR"),
    (2, 2, "TRIGÉSIMO QUARTO BATALHÃO DE POLÍCIA MILITAR", "{{ numero_batalhao_pm }}º BATALHÃO DE POLÍCIA MILITAR"),
]


def gerar_todos() -> list[Path]:
    gerados = [
        gerar_normalizado(
            ORIGEM_DESPACHO, DESTINO_DESPACHO,
            SUBSTITUICOES_PARAGRAFO_DESPACHO, SUBSTITUICOES_TABELA_DESPACHO,
        ),
        gerar_normalizado(
            ORIGEM_VISTA_FINAL, DESTINO_VISTA_FINAL,
            SUBSTITUICOES_PARAGRAFO_VISTA_FINAL, SUBSTITUICOES_TABELA_VISTA_FINAL,
        ),
    ]
    gerados.append(
        gerar_normalizado(DESTINO_VISTA_FINAL, DESTINO_VISTA_INICIAL, SUBSTITUICOES_PARAGRAFO_VISTA_INICIAL)
    )
    gerados.append(
        gerar_normalizado(
            ORIGEM_COMUNICACAO, DESTINO_COMUNICACAO,
            SUBSTITUICOES_PARAGRAFO_COMUNICACAO, SUBSTITUICOES_TABELA_COMUNICACAO,
        )
    )
    gerados.append(
        gerar_normalizado(
            ORIGEM_NOTIFICACAO_TESTEMUNHA, DESTINO_NOTIFICACAO_TESTEMUNHA,
            SUBSTITUICOES_PARAGRAFO_NOTIFICACAO_TESTEMUNHA, SUBSTITUICOES_TABELA_NOTIFICACAO_TESTEMUNHA,
        )
    )
    gerados.append(
        gerar_normalizado(
            ORIGEM_NOTIFICACAO_SINDICADO, DESTINO_NOTIFICACAO_SINDICADO,
            SUBSTITUICOES_PARAGRAFO_NOTIFICACAO_SINDICADO, SUBSTITUICOES_TABELA_NOTIFICACAO_SINDICADO,
        )
    )
    gerados.append(
        gerar_normalizado(
            ORIGEM_DEPOIMENTO, DESTINO_DEPOIMENTO,
            SUBSTITUICOES_PARAGRAFO_DEPOIMENTO, SUBSTITUICOES_TABELA_DEPOIMENTO,
        )
    )
    gerados.append(
        gerar_normalizado(
            ORIGEM_RELATORIO, DESTINO_RELATORIO,
            SUBSTITUICOES_PARAGRAFO_RELATORIO, SUBSTITUICOES_TABELA_RELATORIO,
        )
    )
    gerados.append(
        gerar_normalizado(
            ORIGEM_OFICIO, DESTINO_OFICIO,
            SUBSTITUICOES_PARAGRAFO_OFICIO, SUBSTITUICOES_TABELA_OFICIO,
        )
    )
    return gerados


if __name__ == "__main__":
    for caminho in gerar_todos():
        print(f"Template normalizado gerado em: {caminho}")
