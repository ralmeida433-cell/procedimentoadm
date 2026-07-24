"""Assistente interativo (Rich + Questionary) para criar um PCD do zero ou
continuar um já em andamento, etapa por etapa.

Este módulo não reimplementa nenhuma regra de negócio - cada etapa chama a
mesma função de `gerador_portarias` que o modo planilha/CLI usa
(`instaurar_processo`, `abrir_vista_inicial` etc.), então validação de
competência, prazos e geração de documento são idênticas nos dois modos.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pcd_automation.gerador_portarias.planilha import CAMPOS_INFO, converter_valor
from pcd_automation.validador_juridico import validar_processo

from . import estado
from .perguntas import ETAPAS, Etapa, indice_etapa, processo_concluido, proxima_etapa


class OperacaoCancelada(Exception):
    """Levantada quando o usuário aperta Ctrl+C/Esc durante uma pergunta."""


# ---------------------------------------------------------------- perguntas

def _validar_data(texto: str) -> bool | str:
    if not texto.strip():
        return True
    try:
        datetime.strptime(texto.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return "Use o formato dd/mm/aaaa (ex.: 12/07/2026)."


def _perguntar_campo(chave: str, valor_atual=None):
    rotulo, tipo = CAMPOS_INFO.get(chave, (chave, "texto"))

    if tipo == "sim_nao":
        padrao = bool(valor_atual) if isinstance(valor_atual, bool) else False
        resposta = questionary.confirm(rotulo, default=padrao).ask()
        if resposta is None:
            raise OperacaoCancelada
        return resposta

    if tipo == "data":
        padrao = valor_atual.strftime("%d/%m/%Y") if isinstance(valor_atual, date) else (valor_atual or "")
        resposta = questionary.text(f"{rotulo} (dd/mm/aaaa)", default=padrao, validate=_validar_data).ask()
        if resposta is None:
            raise OperacaoCancelada
        return converter_valor("data", resposta) if resposta.strip() else None

    padrao = str(valor_atual) if valor_atual not in (None, "") else ""
    resposta = questionary.text(rotulo, default=padrao).ask()
    if resposta is None:
        raise OperacaoCancelada
    return converter_valor("texto", resposta)


def _perguntar_obrigatorio(chave: str, valor_atual, console: Console):
    while True:
        valor = _perguntar_campo(chave, valor_atual)
        if valor not in (None, ""):
            return valor
        rotulo, _ = CAMPOS_INFO.get(chave, (chave, "texto"))
        console.print(f"[red]Campo obrigatório - não pode ficar em branco: {rotulo}[/red]")


def perguntar_etapa(etapa: Etapa, dados: dict, console: Console) -> dict:
    console.rule(f"[bold cyan]{etapa.titulo}[/bold cyan]")
    for chave in etapa.campos_obrigatorios:
        if dados.get(chave) not in (None, ""):
            continue
        dados[chave] = _perguntar_obrigatorio(chave, dados.get(chave), console)
    if etapa.campos_opcionais:
        console.print("[dim]Campos opcionais abaixo - Enter em branco para pular.[/dim]")
        for chave in etapa.campos_opcionais:
            if dados.get(chave) not in (None, ""):
                continue
            dados[chave] = _perguntar_campo(chave, dados.get(chave))
    return dados


def _revisar_campos(etapa: Etapa, dados: dict, console: Console) -> None:
    todos = etapa.campos_obrigatorios + etapa.campos_opcionais
    escolhas = []
    for chave in todos:
        rotulo, _ = CAMPOS_INFO.get(chave, (chave, "texto"))
        valor = dados.get(chave)
        valor_fmt = valor.strftime("%d/%m/%Y") if isinstance(valor, date) else (valor if valor not in (None, "") else "(vazio)")
        escolhas.append(questionary.Choice(title=f"{rotulo}: {valor_fmt}", value=chave))
    selecionados = questionary.checkbox("Quais campos deseja corrigir? (espaço para marcar, Enter para confirmar)", choices=escolhas).ask()
    if selecionados is None:
        raise OperacaoCancelada
    for chave in selecionados:
        dados[chave] = _perguntar_campo(chave, dados.get(chave))


# ---------------------------------------------------------------- exibição

CAMPOS_REDACAO = {
    "resumo_fato", "analise_fatos_e_provas", "alegacoes_defesa_analise",
    "teor_depoimento", "observacoes_impedimento", "outras_provas",
    "local_fato", "incidentes_processuais",
}


def mostrar_preview(dados: dict, console: Console, titulo: str = "Conferência dos dados") -> None:
    tabela = Table(title=titulo, header_style="bold cyan", show_lines=False)
    tabela.add_column("Campo")
    tabela.add_column("Valor")
    for chave, valor in dados.items():
        if valor in (None, ""):
            continue
        rotulo, tipo = CAMPOS_INFO.get(chave, (chave, "texto"))
        if tipo == "sim_nao":
            valor_fmt = "Sim" if valor else "Não"
        elif isinstance(valor, date):
            valor_fmt = valor.strftime("%d/%m/%Y")
        else:
            valor_fmt = str(valor)
        tabela.add_row(rotulo, valor_fmt)
    console.print(tabela)
    _mostrar_avisos_redacao(dados, console)


def _mostrar_avisos_redacao(dados: dict, console: Console) -> None:
    from pcd_automation.redacao import validar_texto

    linhas: list[str] = []
    for chave in CAMPOS_REDACAO:
        valor = dados.get(chave)
        if isinstance(valor, str) and valor.strip():
            rotulo = CAMPOS_INFO.get(chave, (chave, ""))[0]
            for msg in validar_texto(valor):
                linhas.append(f"[yellow]{rotulo}:[/yellow] {msg}")
    if linhas:
        console.print(Panel(
            "\n".join(linhas),
            title="[bold yellow]Redação oficial - revise antes de assinar[/bold yellow]",
            border_style="yellow",
        ))


def mostrar_resultado(resultado, console: Console) -> None:
    if not resultado.ok:
        console.print(Panel("\n".join(resultado.erros) or "Erro desconhecido.", title="[bold red]Não foi possível gerar[/bold red]", border_style="red"))
        return

    linhas = []
    for campo in (
        "caminho_comunicacao", "caminho_despacho", "caminho_termo",
        "caminho_notificacao_testemunha", "caminho_notificacao_sindicado",
    ):
        valor = getattr(resultado, campo, None)
        if valor:
            linhas.append(f"[green]Gerado:[/green] {valor}")

    prazo = getattr(resultado, "prazo_conclusao", None) or getattr(resultado, "prazo_defesa", None)
    if prazo:
        linhas.append(f"[cyan]Prazo:[/cyan] {prazo}")

    alertas = getattr(resultado, "alertas", None) or []
    for alerta in alertas:
        linhas.append(f"[yellow]Aviso:[/yellow] {alerta}")

    pendentes = getattr(resultado, "campos_manuais_pendentes", None) or []
    if pendentes:
        linhas.append("[yellow]Preencher manualmente no Word antes de assinar:[/yellow] " + ", ".join(pendentes))

    console.print(Panel("\n".join(linhas) or "Concluído.", title="[bold green]OK[/bold green]", border_style="green"))


# ---------------------------------------------------------------- fluxo

def _fluxo_instauracao(dados: dict, diretorio_base: Path, console: Console, chave_rascunho: str):
    etapa = ETAPAS[0]
    try:
        while True:
            dados = perguntar_etapa(etapa, dados, console)
            estado.salvar_rascunho(diretorio_base, chave_rascunho, dados)
            mostrar_preview(dados, console)

            resultado_validacao = validar_processo(dados)
            for alerta in resultado_validacao.alertas:
                console.print(f"[yellow]Aviso:[/yellow] {alerta}")
            if not resultado_validacao.ok:
                console.print(Panel(
                    "\n".join(resultado_validacao.erros),
                    title="[bold red]Corrija antes de instaurar[/bold red]", border_style="red",
                ))
                _revisar_campos(etapa, dados, console)
                continue

            if questionary.confirm("Confirma a instauração com esses dados?", default=True).ask():
                break
            _revisar_campos(etapa, dados, console)
    except OperacaoCancelada:
        estado.salvar_rascunho(diretorio_base, chave_rascunho, dados)
        console.print(f"\n[yellow]Progresso salvo no rascunho '{chave_rascunho}'. Rode 'continuar' para retomar.[/yellow]")
        return None

    resultado = etapa.funcao(dados, diretorio_base)
    mostrar_resultado(resultado, console)
    if not resultado.ok:
        estado.salvar_rascunho(diretorio_base, chave_rascunho, dados)
        console.print(f"[yellow]Rascunho '{chave_rascunho}' mantido - corrija e rode 'continuar'.[/yellow]")
        return None

    estado.remover_rascunho(diretorio_base, chave_rascunho)
    estado.salvar_estado_processo(resultado.diretorio, dados, etapa_concluida_ate=etapa.id)
    return resultado.diretorio, dados


def _continuar_demais_etapas(
    indice_inicial: int, dados: dict, diretorio_base: Path, diretorio_processo: Path, console: Console,
    *, perguntar_antes_da_primeira: bool = True,
) -> None:
    indice = indice_inicial
    etapa_anterior_id = ETAPAS[indice_inicial - 1].id
    primeira = True
    while indice < len(ETAPAS):
        etapa = ETAPAS[indice]
        if etapa is not proxima_etapa(indice - 1, dados):
            # Etapa dispensável para os dados atuais (ex.: CEDMU sem RED apresentada) - pula.
            indice += 1
            continue

        deve_perguntar = (not primeira) or perguntar_antes_da_primeira
        primeira = False
        if deve_perguntar and not questionary.confirm(
            f"Continuar agora para a próxima etapa ({etapa.titulo})?", default=True
        ).ask():
            console.print(f"[cyan]Combinado - rode 'continuar' quando quiser seguir em '{etapa.titulo}'.[/cyan]")
            return

        try:
            while True:
                dados = perguntar_etapa(etapa, dados, console)
                estado.salvar_estado_processo(diretorio_processo, dados, etapa_concluida_ate=etapa_anterior_id)
                mostrar_preview(dados, console)
                if questionary.confirm(f"Confirma gerar os documentos de '{etapa.titulo}'?", default=True).ask():
                    break
                _revisar_campos(etapa, dados, console)
        except OperacaoCancelada:
            estado.salvar_estado_processo(diretorio_processo, dados, etapa_concluida_ate=etapa_anterior_id)
            console.print(f"\n[yellow]Progresso salvo. Rode 'continuar' para retomar em '{etapa.titulo}'.[/yellow]")
            return

        resultado = etapa.funcao(dados, diretorio_base)
        mostrar_resultado(resultado, console)
        if not resultado.ok:
            estado.salvar_estado_processo(diretorio_processo, dados, etapa_concluida_ate=etapa_anterior_id)
            console.print("[red]Corrija os campos indicados e rode 'continuar' de novo.[/red]")
            return
        estado.salvar_estado_processo(diretorio_processo, dados, etapa_concluida_ate=etapa.id)
        etapa_anterior_id = etapa.id
        indice += 1

    console.print(Panel("[bold green]Todas as etapas concluídas para este PCD![/bold green]", border_style="green"))


def criar_novo(diretorio_base: Path) -> None:
    console = Console()
    console.print(Panel(
        "[bold]Novo PCD[/bold]\nResponda os campos abaixo. Ctrl+C a qualquer momento salva o progresso e sai.",
        border_style="green",
    ))

    chave = questionary.text(
        "Identificador para salvar o rascunho (ex.: o REDS, se já tiver) - só serve para retomar depois:"
    ).ask()
    if not chave:
        console.print("[yellow]Cancelado - nada foi salvo.[/yellow]")
        return

    dados = estado.carregar_rascunho(diretorio_base, chave) or {}
    if dados:
        console.print(f"[yellow]Rascunho '{chave}' encontrado - continuando de onde parou.[/yellow]")

    resultado = _fluxo_instauracao(dados, diretorio_base, console, chave)
    if resultado is None:
        return
    diretorio_processo, dados = resultado
    _continuar_demais_etapas(indice_etapa("instauracao") + 1, dados, diretorio_base, diretorio_processo, console)


def continuar(diretorio_base: Path) -> None:
    console = Console()
    rascunhos = estado.listar_rascunhos(diretorio_base)
    processos = estado.listar_processos_em_andamento(diretorio_base)

    if not rascunhos and not processos:
        console.print("[yellow]Nenhum PCD em andamento encontrado (nem rascunho, nem processo instaurado com etapas pendentes).[/yellow]")
        return

    escolhas = [
        questionary.Choice(title=f"[rascunho] {r} - ainda não instaurado", value=("rascunho", r))
        for r in rascunhos
    ]
    for p in processos:
        _, etapa_ate = estado.carregar_estado_processo(p)
        titulo_etapa = next((e.titulo for e in ETAPAS if e.id == etapa_ate), etapa_ate)
        escolhas.append(questionary.Choice(title=f"{p.name} - concluído até: {titulo_etapa}", value=("processo", p)))

    escolha = questionary.select("Qual PCD deseja continuar?", choices=escolhas).ask()
    if escolha is None:
        console.print("[yellow]Cancelado.[/yellow]")
        return
    tipo, alvo = escolha

    if tipo == "rascunho":
        dados = estado.carregar_rascunho(diretorio_base, alvo) or {}
        console.print(Panel(f"Retomando rascunho '{alvo}'", border_style="green"))
        resultado = _fluxo_instauracao(dados, diretorio_base, console, alvo)
        if resultado is None:
            return
        diretorio_processo, dados = resultado
        _continuar_demais_etapas(indice_etapa("instauracao") + 1, dados, diretorio_base, diretorio_processo, console)
        return

    dados, etapa_ate = estado.carregar_estado_processo(alvo)
    indice_atual = indice_etapa(etapa_ate)
    proxima = proxima_etapa(indice_atual, dados)
    if proxima is None:
        console.print("[green]Este PCD já concluiu todas as etapas![/green]")
        return
    console.print(Panel(f"Retomando {alvo.name} na etapa '{proxima.titulo}'", border_style="green"))
    _continuar_demais_etapas(indice_etapa(proxima.id), dados, diretorio_base, alvo, console, perguntar_antes_da_primeira=False)
