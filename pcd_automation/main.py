"""CLI do sistema de automação do PCD (Procedimento Administrativo
Disciplinar Simplificado) da PMMG.

Uso:
    python main.py criar-planilha [caminho.xlsx]
    python main.py instaurar <caminho_planilha.xlsx> [--saida DIR]
    python main.py abrir-vista-inicial <caminho_planilha.xlsx> [--saida DIR]
    python main.py notificar-oitiva <caminho_planilha.xlsx> [--saida DIR]
    python main.py registrar-depoimento <caminho_planilha.xlsx> [--saida DIR]
    python main.py abrir-vista-final <caminho_planilha.xlsx> [--saida DIR]
    python main.py gerar-relatorio <caminho_planilha.xlsx> [--saida DIR]
    python main.py gerar-oficio <caminho_planilha.xlsx> [--saida DIR]
    python main.py gerar-ata-cedmu <caminho_planilha.xlsx> [--saida DIR]
    python main.py verificar-prazos <caminho_planilha.xlsx>
    python main.py novo
    python main.py continuar
    python main.py servidor [--porta 5000]
    python main.py consultar ["pergunta"]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Callable

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from pcd_automation.gerador_portarias import (
    abrir_vista_final,
    abrir_vista_inicial,
    atualizar_status,
    atualizar_status_cedmu,
    atualizar_status_depoimento,
    atualizar_status_oficio,
    atualizar_status_oitiva,
    atualizar_status_relatorio,
    atualizar_status_vista_final,
    atualizar_status_vista_inicial,
    criar_planilha_modelo,
    gerar_cedmu,
    gerar_oficio,
    gerar_relatorio,
    instaurar_processo,
    ler_pendentes_cedmu,
    ler_pendentes_depoimento,
    ler_pendentes_oficio,
    ler_pendentes_oitiva,
    ler_pendentes_relatorio,
    ler_pendentes_vista_final,
    ler_pendentes_vista_inicial,
    ler_processos,
    notificar_oitiva,
    registrar_depoimento,
)
from pcd_automation.gerador_portarias.planilha import LinhaProcesso
from pcd_automation.gerador_portarias.vista_comum import ResultadoVista
from pcd_automation.gestao_prazos import gerar_alertas_processo
from pcd_automation.interativo import wizard
from pcd_automation.rag import consulta as rag_consulta

DIRETORIO_PROCESSOS_PADRAO = Path(__file__).resolve().parent / "processos"


def cmd_criar_planilha(args: argparse.Namespace) -> int:
    caminho = criar_planilha_modelo(args.caminho)
    print(f"Planilha modelo criada em: {caminho}")
    return 0


def cmd_instaurar(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_processos(caminho_planilha, apenas_pendentes=True)
    if not linhas:
        print("Nenhuma linha pendente de instauração encontrada na planilha.")
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Processando REDS={linha.dados.get('reds')!r}...")
        try:
            resultado = instaurar_processo(linha.dados, diretorio_saida)
        except KeyError as exc:
            houve_erro = True
            mensagem = f"Campo obrigatório ausente: {exc}"
            print(f"  ERRO: {mensagem}")
            atualizar_status(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - processo {resultado.processo_id}")
        print(f"  Comunicação Disciplinar gerada em: {resultado.caminho_comunicacao}")
        print(f"  Despacho gerado em: {resultado.caminho_despacho}")
        print(f"  Prazo de conclusão: {resultado.prazo_conclusao}")
        if resultado.alertas:
            print(f"  Alertas: {'; '.join(resultado.alertas)}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem preenchimento manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Processo {resultado.processo_id} gerado em {resultado.diretorio}"
        atualizar_status(caminho_planilha, linha.numero_linha, "INSTAURADO", mensagem)

    return 1 if houve_erro else 0


def _cmd_abrir_vista(
    args: argparse.Namespace,
    *,
    ler_pendentes: Callable[[Path], list[LinhaProcesso]],
    abrir_vista_fn: Callable[[dict, Path], ResultadoVista],
    atualizar_status_fn: Callable[[Path, int, str, str], None],
    status_sucesso: str,
    rotulo: str,
) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_pendentes(caminho_planilha)
    if not linhas:
        print(f"Nenhuma linha instaurada aguardando abertura de {rotulo} encontrada.")
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Abrindo {rotulo} para REDS={linha.dados.get('reds')!r}...")
        resultado = abrir_vista_fn(linha.dados, diretorio_saida)

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status_fn(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - termo gerado em: {resultado.caminho_termo}")
        print(f"  Prazo de defesa: {resultado.prazo_defesa}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem preenchimento manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Termo gerado em {resultado.caminho_termo}"
        atualizar_status_fn(caminho_planilha, linha.numero_linha, status_sucesso, mensagem)

    return 1 if houve_erro else 0


def cmd_abrir_vista_inicial(args: argparse.Namespace) -> int:
    return _cmd_abrir_vista(
        args,
        ler_pendentes=ler_pendentes_vista_inicial,
        abrir_vista_fn=abrir_vista_inicial,
        atualizar_status_fn=atualizar_status_vista_inicial,
        status_sucesso="VISTA_INICIAL_ABERTA",
        rotulo="vista inicial",
    )


def cmd_abrir_vista_final(args: argparse.Namespace) -> int:
    return _cmd_abrir_vista(
        args,
        ler_pendentes=ler_pendentes_vista_final,
        abrir_vista_fn=abrir_vista_final,
        atualizar_status_fn=atualizar_status_vista_final,
        status_sucesso="VISTA_FINAL_ABERTA",
        rotulo="vista final",
    )


def cmd_notificar_oitiva(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_pendentes_oitiva(caminho_planilha)
    if not linhas:
        print("Nenhuma linha instaurada aguardando notificação de oitiva encontrada.")
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Notificando oitiva para REDS={linha.dados.get('reds')!r}...")
        resultado = notificar_oitiva(linha.dados, diretorio_saida)

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status_oitiva(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - notificação da testemunha: {resultado.caminho_notificacao_testemunha}")
        print(f"  OK - notificação do sindicado: {resultado.caminho_notificacao_sindicado}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem preenchimento manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Notificações geradas em {resultado.diretorio}"
        atualizar_status_oitiva(caminho_planilha, linha.numero_linha, "OITIVA_NOTIFICADA", mensagem)

    return 1 if houve_erro else 0


def cmd_registrar_depoimento(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_pendentes_depoimento(caminho_planilha)
    if not linhas:
        print("Nenhuma linha instaurada aguardando registro de depoimento encontrada.")
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Registrando depoimento para REDS={linha.dados.get('reds')!r}...")
        resultado = registrar_depoimento(linha.dados, diretorio_saida)

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status_depoimento(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - termo gerado em: {resultado.caminho_termo}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem preenchimento manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Termo gerado em {resultado.caminho_termo}"
        atualizar_status_depoimento(caminho_planilha, linha.numero_linha, "DEPOIMENTO_REGISTRADO", mensagem)

    return 1 if houve_erro else 0


def cmd_gerar_relatorio(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_pendentes_relatorio(caminho_planilha)
    if not linhas:
        print("Nenhuma linha instaurada aguardando geração de relatório encontrada.")
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Gerando relatório para REDS={linha.dados.get('reds')!r}...")
        resultado = gerar_relatorio(linha.dados, diretorio_saida)

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status_relatorio(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - relatório gerado em: {resultado.caminho_termo}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem redação manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Relatório gerado em {resultado.caminho_termo}"
        atualizar_status_relatorio(caminho_planilha, linha.numero_linha, "RELATORIO_GERADO", mensagem)

    return 1 if houve_erro else 0


def cmd_gerar_oficio(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_pendentes_oficio(caminho_planilha)
    if not linhas:
        print("Nenhuma linha instaurada aguardando geração de ofício de remessa encontrada.")
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Gerando ofício de remessa para REDS={linha.dados.get('reds')!r}...")
        resultado = gerar_oficio(linha.dados, diretorio_saida)

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status_oficio(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - ofício gerado em: {resultado.caminho_termo}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem preenchimento manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Ofício gerado em {resultado.caminho_termo}"
        atualizar_status_oficio(caminho_planilha, linha.numero_linha, "OFICIO_GERADO", mensagem)

    return 1 if houve_erro else 0


def cmd_gerar_cedmu(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    diretorio_saida = Path(args.saida) if args.saida else DIRETORIO_PROCESSOS_PADRAO

    linhas = ler_pendentes_cedmu(caminho_planilha)
    if not linhas:
        print(
            "Nenhuma linha aguardando Ata do CEDMU encontrada (só é gerada quando há RED final "
            "apresentada - art. 523 do MAPPA)."
        )
        return 0

    houve_erro = False
    for linha in linhas:
        print(f"\n[linha {linha.numero_linha}] Gerando Ata de Reunião do CEDMU para REDS={linha.dados.get('reds')!r}...")
        resultado = gerar_cedmu(linha.dados, diretorio_saida)

        if not resultado.ok:
            houve_erro = True
            mensagem = "; ".join(resultado.erros)
            print(f"  ERRO: {mensagem}")
            atualizar_status_cedmu(caminho_planilha, linha.numero_linha, "ERRO", mensagem)
            continue

        print(f"  OK - ata gerada em: {resultado.caminho_termo}")
        if resultado.campos_manuais_pendentes:
            print(
                "  Campos que exigem preenchimento manual no Word antes de assinar: "
                + ", ".join(resultado.campos_manuais_pendentes)
            )

        mensagem = f"Ata do CEDMU gerada em {resultado.caminho_termo}"
        atualizar_status_cedmu(caminho_planilha, linha.numero_linha, "CEDMU_GERADO", mensagem)

    return 1 if houve_erro else 0


def cmd_verificar_prazos(args: argparse.Namespace) -> int:
    caminho_planilha = Path(args.planilha)
    linhas = ler_processos(caminho_planilha, apenas_pendentes=False)

    hoje = date.today()
    algum_alerta = False
    for linha in linhas:
        alertas = gerar_alertas_processo(linha.dados, data_referencia=hoje)
        for alerta in alertas:
            algum_alerta = True
            reds = linha.dados.get("reds")
            print(f"[linha {linha.numero_linha}] REDS={reds} - {alerta['tipo']}: {alerta['mensagem']}")

    if not algum_alerta:
        print("Nenhum atraso ou vencimento próximo encontrado.")
    return 0


def cmd_novo(args: argparse.Namespace) -> int:
    wizard.criar_novo(DIRETORIO_PROCESSOS_PADRAO)
    return 0


def cmd_continuar(args: argparse.Namespace) -> int:
    wizard.continuar(DIRETORIO_PROCESSOS_PADRAO)
    return 0


def cmd_consultar(args: argparse.Namespace) -> int:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    def consultar_e_mostrar(pergunta: str) -> None:
        with console.status("Consultando as referências do MAPPA..."):
            resultado = rag_consulta.responder(pergunta)
        if resultado.resposta:
            console.print(Panel(resultado.resposta, title="Especialista MAPPA", border_style="green"))
        if resultado.erro:
            estilo = "yellow" if resultado.trechos else "red"
            console.print(Panel(resultado.erro, title="Aviso", border_style=estilo))

        if resultado.trechos and not resultado.resposta:
            for trecho in resultado.trechos:
                console.print(Panel(trecho.texto, title=f"[dim]{trecho.arquivo}[/dim]", border_style="blue"))
        elif resultado.trechos:
            fontes = ", ".join(sorted({t.arquivo for t in resultado.trechos}))
            console.print(f"[dim]Fontes consultadas: {fontes}[/dim]")

    if args.pergunta:
        consultar_e_mostrar(args.pergunta)
        return 0

    console.print(Panel(
        "Consulta ao Especialista MAPPA - digite sua dúvida sobre processos administrativos "
        "(prazos, ritos, competência, redação de peças). Deixe em branco para sair.",
        border_style="blue",
    ))
    while True:
        pergunta = console.input("\n[bold]Pergunta:[/bold] ").strip()
        if not pergunta:
            break
        consultar_e_mostrar(pergunta)

    return 0


def cmd_servidor(args: argparse.Namespace) -> int:
    from pcd_automation.webapp.app import criar_app

    app = criar_app(DIRETORIO_PROCESSOS_PADRAO)
    print(f"Assistente de PCD disponível em: http://127.0.0.1:{args.porta}")
    app.run(host="127.0.0.1", port=args.porta, debug=args.debug)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automação de PCD - PMMG")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_criar = subparsers.add_parser("criar-planilha", help="Cria a planilha de controle modelo")
    p_criar.add_argument("caminho", nargs="?", default="planilhas/planilha_modelo.xlsx")
    p_criar.set_defaults(func=cmd_criar_planilha)

    p_instaurar = subparsers.add_parser("instaurar", help="Instaura os PCDs pendentes na planilha")
    p_instaurar.add_argument("planilha")
    p_instaurar.add_argument("--saida", help="Diretório onde salvar os processos (padrão: ./processos)")
    p_instaurar.set_defaults(func=cmd_instaurar)

    p_vista_inicial = subparsers.add_parser(
        "abrir-vista-inicial",
        help="Gera o Termo de Abertura de Vista Inicial (defesa prévia) dos processos já instaurados",
    )
    p_vista_inicial.add_argument("planilha")
    p_vista_inicial.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_vista_inicial.set_defaults(func=cmd_abrir_vista_inicial)

    p_oitiva = subparsers.add_parser(
        "notificar-oitiva",
        help="Gera as notificações de comparecimento da testemunha e de ciência do sindicado para a oitiva",
    )
    p_oitiva.add_argument("planilha")
    p_oitiva.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_oitiva.set_defaults(func=cmd_notificar_oitiva)

    p_depoimento = subparsers.add_parser(
        "registrar-depoimento", help="Gera o Termo de Depoimento da testemunha dos processos já instaurados"
    )
    p_depoimento.add_argument("planilha")
    p_depoimento.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_depoimento.set_defaults(func=cmd_registrar_depoimento)

    p_vista_final = subparsers.add_parser(
        "abrir-vista-final", help="Gera o Termo de Abertura de Vista Final (RED) dos processos já instaurados"
    )
    p_vista_final.add_argument("planilha")
    p_vista_final.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_vista_final.set_defaults(func=cmd_abrir_vista_final)

    p_relatorio = subparsers.add_parser(
        "gerar-relatorio", help="Gera o Relatório do Encarregado dos processos já instaurados"
    )
    p_relatorio.add_argument("planilha")
    p_relatorio.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_relatorio.set_defaults(func=cmd_gerar_relatorio)

    p_oficio = subparsers.add_parser(
        "gerar-oficio", help="Gera o Ofício de Remessa (último documento) dos processos já instaurados"
    )
    p_oficio.add_argument("planilha")
    p_oficio.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_oficio.set_defaults(func=cmd_gerar_oficio)

    p_cedmu = subparsers.add_parser(
        "gerar-ata-cedmu",
        help="Gera a Ata de Reunião do CEDMU para processos com RED final apresentada (art. 523 do MAPPA)",
    )
    p_cedmu.add_argument("planilha")
    p_cedmu.add_argument("--saida", help="Diretório onde os processos foram salvos (padrão: ./processos)")
    p_cedmu.set_defaults(func=cmd_gerar_cedmu)

    p_prazos = subparsers.add_parser("verificar-prazos", help="Lista alertas de prazo de todas as linhas")
    p_prazos.add_argument("planilha")
    p_prazos.set_defaults(func=cmd_verificar_prazos)

    p_novo = subparsers.add_parser(
        "novo", help="Assistente interativo para criar um PCD novo, do zero, respondendo perguntas no terminal"
    )
    p_novo.set_defaults(func=cmd_novo)

    p_continuar = subparsers.add_parser(
        "continuar", help="Assistente interativo para retomar um PCD (rascunho ou processo) de onde parou"
    )
    p_continuar.set_defaults(func=cmd_continuar)

    p_servidor = subparsers.add_parser(
        "servidor", help="Sobe a interface web local (navegador) do assistente de PCD"
    )
    p_servidor.add_argument("--porta", type=int, default=5000)
    p_servidor.add_argument("--debug", action="store_true")
    p_servidor.set_defaults(func=cmd_servidor)

    p_consultar = subparsers.add_parser(
        "consultar", help="Consulta ao Especialista MAPPA (RAG) para dúvidas sobre processos administrativos"
    )
    p_consultar.add_argument("pergunta", nargs="?", help="Pergunta (se omitida, entra em modo interativo)")
    p_consultar.set_defaults(func=cmd_consultar)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
