"""Main CLI application for TCC Questions"""

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
import time
import logging
from typing import Optional

from .experiment_runner import ExperimentRunner
from ..evaluation.contextual_evaluator import ContextualEvaluator
from ..evaluation.models import ResultadoAvaliacao
from ..database import get_db
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

app = typer.Typer(help="CLI para automação de experimentos TCC Questions")
console = Console()


@app.command("run-experiments")
def run_experiments(
    model: str = typer.Option(..., "--model", "-m", help="Nome do modelo LLM a ser testado"),
    config: str = typer.Option(..., "--config", "-c", help="Configuração experimental (no-rag, simple-rag, agentic-rag, etc.)"),
    delay: float = typer.Option(1.0, "--delay", "-d", help="Delay entre chamadas da API (segundos)"),
    questions: Optional[int] = typer.Option(None, "--questions", "-q", help="Número de perguntas a executar (padrão: todas)"),
    start_from: int = typer.Option(1, "--start-from", "-s", help="Pergunta inicial (padrão: 1)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simular execução sem fazer chamadas de API"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Sobrescrever respostas existentes"),
):
    """
    Executa experimentos automatizados com modelos LLM.
    
    Exemplos:
    
        # Executar todas as perguntas com GPT-4 em configuração no-rag
        uv run python -m app.cli.main run-experiments --model "gpt-4" --config "no-rag"
        
        # Executar 10 perguntas com delay de 2 segundos
        uv run python -m app.cli.main run-experiments --model "gpt-3.5-turbo" --config "simple-rag" --questions 10 --delay 2.0
        
        # Simular execução sem fazer chamadas
        uv run python -m app.cli.main run-experiments --model "gpt-4" --config "agentic-rag" --dry-run
    """
    
    console.print(f"[bold blue]🧪 Iniciando experimentos automatizados[/bold blue]")
    console.print(f"[green]Modelo:[/green] {model}")
    console.print(f"[green]Configuração:[/green] {config}")
    console.print(f"[green]Delay:[/green] {delay}s")
    console.print(f"[green]Modo:[/green] {'🔍 Simulação' if dry_run else '🚀 Execução real'}")
    
    runner = ExperimentRunner(
        model_name=model,
        config=config,
        delay=delay,
        dry_run=dry_run,
        overwrite=overwrite
    )
    
    try:
        runner.run(
            max_questions=questions,
            start_from=start_from
        )
        console.print("[bold green]✅ Experimentos concluídos com sucesso![/bold green]")
    except KeyboardInterrupt:
        console.print("[yellow]⚠️ Execução interrompida pelo usuário[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Erro durante execução: {e}[/red]")
        raise typer.Exit(1)


@app.command("list-models")
def list_models():
    """Lista os modelos LLM disponíveis no banco de dados."""
    runner = ExperimentRunner("", "", 0, init_openai=False)  # Dummy values, no OpenAI init
    models = runner.get_available_models()
    
    if not models:
        console.print("[yellow]Nenhum modelo encontrado no banco de dados[/yellow]")
        return
    
    table = Table(title="Modelos LLM Disponíveis")
    table.add_column("ID", style="cyan")
    table.add_column("Nome", style="green")
    table.add_column("Descrição", style="blue")
    
    for model in models:
        description = model.descricao or "N/A"
        table.add_row(str(model.id), model.nome, description)
    
    console.print(table)


@app.command("list-configs")
def list_configs():
    """Lista as configurações experimentais disponíveis."""
    configs = [
        ("no-rag", "Sem uso de RAG (Retrieval-Augmented Generation)"),
        ("simple-rag", "RAG simples com busca básica"),
        ("agentic-rag", "RAG com agentes inteligentes"),
        ("few-shot", "Aprendizado com poucos exemplos"),
        ("chain-of-thought", "Cadeia de pensamento estruturada"),
        ("default", "Configuração padrão do modelo"),
    ]
    
    table = Table(title="Configurações Experimentais")
    table.add_column("Configuração", style="cyan")
    table.add_column("Descrição", style="green")
    
    for config, description in configs:
        table.add_row(config, description)
    
    console.print(table)


@app.command("status")
def show_status(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Filtrar por modelo específico"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Filtrar por configuração específica"),
):
    """Mostra o status atual dos experimentos."""
    runner = ExperimentRunner("", "", 0, init_openai=False)  # Dummy values, no OpenAI init
    status = runner.get_experiment_status(model_filter=model, config_filter=config)
    
    table = Table(title="Status dos Experimentos")
    table.add_column("Modelo", style="cyan")
    table.add_column("Configuração", style="yellow")
    table.add_column("Concluídos", style="green")
    table.add_column("Total", style="blue")
    table.add_column("Progresso", style="magenta")
    
    for item in status:
        progress = f"{item['completed']}/{item['total']} ({item['percentage']:.1f}%)"
        table.add_row(
            item['model'],
            item['config'],
            str(item['completed']),
            str(item['total']),
            progress
        )
    
    console.print(table)


@app.command("evaluate-contextual")
def evaluate_contextual(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Filtrar por modelo específico"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Filtrar por configuração específica"),
    norma: Optional[str] = typer.Option(None, "--norma", "-n", help="Filtrar por norma técnica (ex: NT-09)"),
    apenas_interessantes: bool = typer.Option(False, "--apenas-interessantes", help="Avaliar apenas perguntas interessantes"),
    apenas_duvidosas: bool = typer.Option(False, "--apenas-duvidosas", help="Avaliar apenas perguntas com respostas duvidosas"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limitar número de avaliações"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simular avaliação sem fazer chamadas de API"),
    force_reevaluate: bool = typer.Option(False, "--force", help="Reavaliar mesmo respostas já avaliadas"),
):
    """
    Avalia respostas automaticamente usando contexto completo (norma, item, resposta esperada).
    
    Exemplos:
    
    # Avaliar respostas de um modelo específico
    uv run python -m app.cli.main evaluate-contextual --model "deepseek-v3" --config "no-rag"
    
    # Avaliar apenas perguntas interessantes
    uv run python -m app.cli.main evaluate-contextual --apenas-interessantes
    
    # Avaliar respostas de uma norma específica
    uv run python -m app.cli.main evaluate-contextual --norma "NT-09"
    
    # Simular avaliação
    uv run python -m app.cli.main evaluate-contextual --dry-run --limit 5
    """
    
    console.print("🧠 Iniciando avaliação contextual de respostas")
    
    # Mostrar configuração
    console.print(f"[green]Modelo:[/green] {model if model else 'Todos'}")
    console.print(f"[green]Configuração:[/green] {config if config else 'Todas'}")
    console.print(f"[green]Norma:[/green] {norma if norma else 'Todas'}")
    console.print(f"[green]Modo:[/green] {'🔍 Simulação' if dry_run else '🚀 Avaliação real'}")
    
    if apenas_interessantes:
        console.print("[yellow]📌 Filtrando apenas perguntas interessantes[/yellow]")
    
    if apenas_duvidosas:
        console.print("[yellow]⚠️ Filtrando apenas perguntas com respostas duvidosas[/yellow]")
    
    try:
        # Inicializar avaliador
        evaluator = ContextualEvaluator(dry_run=dry_run, overwrite=force_reevaluate)
        
        # Obter sessão do banco
        db = next(get_db())
        
        # Executar avaliação com filtros
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=False
        ) as progress:
            
            task = progress.add_task("🔄 Avaliando respostas...", total=None)
            
            resultados = evaluator.avaliar_por_filtros(
                db=db,
                modelo_nome=model,
                configuracao=config,
                norma_tecnica=norma,
                apenas_interessantes=apenas_interessantes,
                apenas_duvidosas=apenas_duvidosas,
                limit=limit
            )
        
        # Mostrar resultados
        if resultados:
            console.print(f"\n[green]✅ {len(resultados)} respostas avaliadas com sucesso![/green]")
            
            # Tabela com resumo dos resultados
            table = Table(title="Resumo das Avaliações")
            table.add_column("Pergunta", style="cyan")
            table.add_column("Modelo", style="blue")
            table.add_column("Config", style="green")
            table.add_column("Norma", style="yellow")
            table.add_column("Score", style="red")
            table.add_column("Correta", style="green")
            table.add_column("Fonte Citada", style="purple")
            
            # Mostrar primeiros 10 resultados
            for resultado in resultados[:10]:
                avaliacao = resultado.avaliacao
                score_str = f"{resultado.score_final:.1f}/10"
                correto_str = "✅" if avaliacao.resposta_correta else "❌"
                fonte_str = "📚" if avaliacao.fonte_citada else "❌"
                
                table.add_row(
                    f"#{resultado.pergunta_numero}",
                    resultado.modelo_nome,
                    resultado.configuracao,
                    resultado.norma_tecnica,
                    score_str,
                    correto_str,
                    fonte_str
                )
            
            console.print(table)
            
            if len(resultados) > 10:
                console.print(f"[dim]... e mais {len(resultados) - 10} resultados[/dim]")
            
            # Estatísticas gerais
            scores = [r.score_final for r in resultados]
            corretas = sum(1 for r in resultados if r.avaliacao.resposta_correta)
            com_fonte = sum(1 for r in resultados if r.avaliacao.fonte_citada)
            
            console.print(f"\n[bold]📊 Estatísticas Gerais:[/bold]")
            console.print(f"[green]Score médio:[/green] {sum(scores)/len(scores):.2f}/10")
            console.print(f"[green]Respostas corretas:[/green] {corretas}/{len(resultados)} ({corretas/len(resultados)*100:.1f}%)")
            console.print(f"[green]Com fonte citada:[/green] {com_fonte}/{len(resultados)} ({com_fonte/len(resultados)*100:.1f}%)")
            
        else:
            console.print("[yellow]⚠️ Nenhuma resposta encontrada para avaliar com os filtros especificados[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Erro durante avaliação: {e}[/red]")
        raise typer.Exit(1)
    
    finally:
        if 'db' in locals():
            db.close()


@app.command("evaluate-batch")
def evaluate_batch(
    model: str = typer.Option(..., "--model", "-m", help="Nome do modelo LLM a ser avaliado"),
    config: str = typer.Option(..., "--config", "-c", help="Configuração experimental (no-rag, simple-rag, agentic-rag, etc.)"),
    norma: Optional[str] = typer.Option(None, "--norma", "-n", help="Filtrar por norma técnica específica (ex: NT-09)"),
    apenas_interessantes: bool = typer.Option(False, "--apenas-interessantes", help="Avaliar apenas perguntas interessantes"),
    apenas_duvidosas: bool = typer.Option(False, "--apenas-duvidosas", help="Avaliar apenas perguntas com respostas duvidosas"),
    max_responses: Optional[int] = typer.Option(None, "--max", help="Número máximo de respostas a avaliar"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simular avaliação sem fazer chamadas de API"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Reavaliar respostas já avaliadas"),
):
    """
    Avalia respostas em lote para um modelo e configuração específicos.
    
    Segue o mesmo padrão do run-experiments: evita duplicatas e processa
    todas as respostas não avaliadas para a combinação modelo/config especificada.
    
    Exemplos:
    
        # Avaliar todas as respostas não avaliadas do deepseek-v3 no-rag
        uv run python -m app.cli.main evaluate-batch --model "deepseek-v3" --config "no-rag"
        
        # Avaliar apenas respostas da NT-09 que ainda não foram avaliadas
        uv run python -m app.cli.main evaluate-batch --model "deepseek-v3" --config "no-rag" --norma "NT-09"
        
        # Reavaliar todas as respostas, mesmo as já avaliadas
        uv run python -m app.cli.main evaluate-batch --model "deepseek-v3" --config "no-rag" --overwrite
        
        # Simular avaliação sem custos de API
        uv run python -m app.cli.main evaluate-batch --model "deepseek-v3" --config "no-rag" --dry-run
    """
    
    console.print(f"[bold blue]🧠 Iniciando avaliação em lote[/bold blue]")
    console.print(f"[green]Modelo:[/green] {model}")
    console.print(f"[green]Configuração:[/green] {config}")
    console.print(f"[green]Norma:[/green] {norma if norma else 'Todas'}")
    console.print(f"[green]Modo:[/green] {'🔍 Simulação' if dry_run else '🚀 Avaliação real'}")
    
    if apenas_interessantes:
        console.print("[yellow]📌 Filtrando apenas perguntas interessantes[/yellow]")
    
    if apenas_duvidosas:
        console.print("[yellow]⚠️ Filtrando apenas perguntas com respostas duvidosas[/yellow]")
    
    if overwrite:
        console.print("[yellow]🔄 Modo overwrite: reavaliando respostas já avaliadas[/yellow]")
    
    try:
        # Inicializar avaliador
        evaluator = ContextualEvaluator(dry_run=dry_run, overwrite=overwrite)
        
        # Obter sessão do banco
        db = next(get_db())
        
        # Obter respostas para avaliar (seguindo padrão do ExperimentRunner)
        respostas = evaluator.get_responses_to_evaluate(
            db=db,
            modelo_nome=model,
            configuracao=config,
            max_responses=max_responses,
            norma_tecnica=norma,
            apenas_interessantes=apenas_interessantes,
            apenas_duvidosas=apenas_duvidosas
        )
        
        if not respostas:
            console.print("[yellow]📝 Nenhuma resposta encontrada para avaliar com os filtros especificados[/yellow]")
            return
        
        console.print(f"[green]📋 Encontradas {len(respostas)} respostas para avaliar[/green]")
        
        if not dry_run:
            console.print("[yellow]⚠️  ATENÇÃO: Esta execução fará chamadas reais para a API do DeepSeek![/yellow]")
            console.print(f"[blue]💰 Custo estimado: Variável conforme número de respostas ({len(respostas)})[/blue]")
        
        # Progress tracking (seguindo padrão do ExperimentRunner)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            
            task = progress.add_task(
                f"🔄 Avaliando respostas [{config}]",
                total=len(respostas)
            )
            
            success_count = 0
            error_count = 0
            resultados = []
            
            for i, resposta in enumerate(respostas, 1):
                
                try:
                    progress.update(
                        task, 
                        description=f"🔄 Resposta #{resposta.pergunta.numero} [{config}]"
                    )
                    
                    # Fazer avaliação
                    avaliacao = evaluator.avaliar_resposta(resposta.pergunta, resposta)
                    
                    if avaliacao:
                        # Criar resultado
                        resultado = ResultadoAvaliacao(
                            avaliacao=avaliacao,
                            score_final=avaliacao.calcular_score_total(),
                            pergunta_numero=resposta.pergunta.numero,
                            modelo_nome=resposta.modelo.nome,
                            configuracao=resposta.configuracao,
                            timestamp=datetime.now().isoformat(),
                            norma_tecnica=resposta.pergunta.norma_tecnica,
                            item_norma=resposta.pergunta.item,
                            flag_resposta_duvidosa=resposta.pergunta.flag_resposta_duvidosa
                        )
                        
                        resultados.append(resultado)
                        
                        # Atualizar banco (se não for dry_run)
                        if not dry_run:
                            evaluator._atualizar_resposta_banco(resposta, avaliacao, db)
                        
                        success_count += 1
                        score_str = f"{resultado.score_final:.1f}/10"
                        correto_str = "✅" if avaliacao.resposta_correta else "❌"
                        fonte_str = "📚" if avaliacao.fonte_citada else "❌"
                        
                        console.print(
                            f"[green]✅ #{resposta.pergunta.numero}[/green] "
                            f"[blue]{score_str}[/blue] "
                            f"{correto_str} {fonte_str}"
                        )
                    else:
                        error_count += 1
                        console.print(f"[red]❌ #{resposta.pergunta.numero}: Falha na avaliação[/red]")
                    
                    # Delay já aplicado no ContextualEvaluator antes da chamada API
                    # if i < len(respostas):
                    #     time.sleep(2.0)  # Removido: delay movido para ContextualEvaluator
                    
                except KeyboardInterrupt:
                    console.print(f"\n[yellow]⚠️ Interrompido pelo usuário na resposta #{resposta.pergunta.numero}[/yellow]")
                    break
                except Exception as e:
                    error_count += 1
                    console.print(f"[red]❌ #{resposta.pergunta.numero}: {e}[/red]")
                    logger.error(f"Erro ao avaliar resposta {resposta.id}: {e}")
                    
                    # Delay já aplicado no ContextualEvaluator antes da chamada API
                    # if i < len(respostas):
                    #     time.sleep(2.0)  # Removido: delay movido para ContextualEvaluator
                
                progress.advance(task)
        
        # Resumo final (seguindo padrão do ExperimentRunner)
        total_processed = success_count + error_count
        console.print("\n" + "="*60)
        console.print(f"[bold]📊 Resumo da Avaliação em Lote[/bold]")
        console.print(f"[green]✅ Sucessos: {success_count}[/green]")
        console.print(f"[red]❌ Erros: {error_count}[/red]")
        console.print(f"[blue]📈 Total processado: {total_processed}/{len(respostas)}[/blue]")
        console.print(f"[cyan]⚙️ Configuração: {config}[/cyan]")
        console.print(f"[cyan]🤖 Modelo: {model}[/cyan]")
        
        # Estatísticas das avaliações
        if resultados:
            scores = [r.score_final for r in resultados]
            corretas = sum(1 for r in resultados if r.avaliacao.resposta_correta)
            com_fonte = sum(1 for r in resultados if r.avaliacao.fonte_citada)
            
            console.print(f"\n[bold]📊 Estatísticas das Avaliações:[/bold]")
            console.print(f"[green]Score médio:[/green] {sum(scores)/len(scores):.2f}/10")
            console.print(f"[green]Respostas corretas:[/green] {corretas}/{len(resultados)} ({corretas/len(resultados)*100:.1f}%)")
            console.print(f"[green]Com fonte citada:[/green] {com_fonte}/{len(resultados)} ({com_fonte/len(resultados)*100:.1f}%)")
        
        if not dry_run:
            console.print(f"\n[dim]📝 Log detalhado salvo em: experiment_runs.log[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Erro durante avaliação: {e}[/red]")
        raise typer.Exit(1)
    
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    app()