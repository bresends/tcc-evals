"""Main CLI application for TCC Questions"""

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
from typing import Optional

from .experiment_runner import ExperimentRunner

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


if __name__ == "__main__":
    app()