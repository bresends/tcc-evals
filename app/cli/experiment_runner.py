"""Experiment runner for automated LLM testing"""

import os
import time
from typing import List, Optional, Dict, Any
from decimal import Decimal
import logging
from datetime import datetime
from dotenv import load_dotenv

from openai import OpenAI

# Load environment variables from .env file
load_dotenv()
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db, engine
from ..models import Pergunta, ModeloLLM, Resposta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('experiment_runs.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
console = Console()


class ExperimentRunner:
    """Main class for running automated experiments with LLM models."""
    
    def __init__(
        self,
        model_name: str,
        config: str,
        delay: float = 1.0,
        dry_run: bool = False,
        overwrite: bool = False,
        init_openai: bool = True
    ):
        self.model_name = model_name
        self.config = config
        self.delay = delay
        self.dry_run = dry_run
        self.overwrite = overwrite
        
        # Initialize OpenAI-compatible client (supports GitHub Models)
        self.client = None
        if not dry_run and init_openai:
            # Check for GitHub Models first, then fallback to OpenAI
            api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("LLM_BASE_URL")
            
            if not api_key:
                raise ValueError("LLM_API_KEY or OPENAI_API_KEY environment variable not set")
            
            # Initialize client with base_url if provided (for GitHub Models)
            if base_url:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self.client = OpenAI(api_key=api_key)
        
        # Database session
        self.db = next(get_db())
        
        # Get model from database (only if model_name is provided)
        self.modelo_obj = None
        if model_name:
            self.modelo_obj = self.db.query(ModeloLLM).filter(
                ModeloLLM.nome == model_name
            ).first()
            
            if not self.modelo_obj:
                raise ValueError(f"Model '{model_name}' not found in database")
    
    def get_available_models(self) -> List[ModeloLLM]:
        """Get all available models from database."""
        return self.db.query(ModeloLLM).order_by(ModeloLLM.nome).all()
    
    def get_experiment_status(
        self, 
        model_filter: Optional[str] = None,
        config_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get status of experiments by model and configuration."""
        
        models = self.db.query(ModeloLLM).order_by(ModeloLLM.nome).all()
        total_questions = self.db.query(Pergunta).count()
        
        configurations = [
            "no-rag", "simple-rag", "agentic-rag", 
            "few-shot", "chain-of-thought"
        ]
        
        status = []
        
        for model in models:
            if model_filter and model.nome != model_filter:
                continue
                
            for config in configurations:
                if config_filter and config != config_filter:
                    continue
                    
                completed = self.db.query(Resposta).filter(
                    Resposta.modelo_id == model.id,
                    Resposta.configuracao == config
                ).count()
                
                percentage = (completed / total_questions * 100) if total_questions > 0 else 0
                
                status.append({
                    'model': model.nome,
                    'config': config,
                    'completed': completed,
                    'total': total_questions,
                    'percentage': percentage
                })
        
        return status
    
    def get_questions_to_process(
        self, 
        max_questions: Optional[int] = None,
        start_from: int = 1
    ) -> List[Pergunta]:
        """Get list of questions to process."""
        
        query = self.db.query(Pergunta).filter(Pergunta.numero >= start_from)
        
        if not self.overwrite and self.modelo_obj:
            # Exclude questions that already have responses for this model/config
            existing_ids = self.db.query(Resposta.pergunta_id).filter(
                Resposta.modelo_id == self.modelo_obj.id,
                Resposta.configuracao == self.config
            ).subquery()
            
            query = query.filter(~Pergunta.id.in_(existing_ids))
        
        query = query.order_by(Pergunta.numero)
        
        if max_questions:
            query = query.limit(max_questions)
        
        return query.all()
    
    def call_openai_api(self, question_text: str) -> Dict[str, Any]:
        """Make API call to OpenAI with proper error handling and timing."""
        
        if self.dry_run:
            # Simulate API call
            time.sleep(0.1)  # Simulate network delay
            
            # Generate more realistic markdown response
            mock_response = f"""# Resposta - {self.config.replace('-', ' ').title()}

## Análise da Norma Técnica

Com base na pergunta apresentada sobre as **normas técnicas do CBMGO**, posso fornecer a seguinte análise:

### Pontos principais:
1. **Requisitos específicos** - conforme estabelecido na regulamentação
2. *Procedimentos obrigatórios* para cumprimento da norma
3. Critérios de `avaliação` e `verificação`

### Configuração utilizada: `{self.config}`
Esta resposta foi gerada utilizando a configuração **{self.config}**, que {self._get_config_description()}.

> **Importante**: Esta é uma resposta simulada gerada pelo sistema de testes do CLI.

### Conformidade:
- [x] Atende aos requisitos mínimos
- [x] Segue as diretrizes estabelecidas
- [ ] Requer verificação adicional

**Modelo**: {self.model_name}  
**Status**: ✅ Simulação concluída

---
*Resposta gerada automaticamente pelo sistema de experimentos TCC Questions*"""
            
            return {
                'response': mock_response,
                'first_response_time': 0.85,
                'total_time': 1.20
            }
        
        # Real API call
        return self._call_real_api(question_text)
    
    def _get_config_description(self):
        """Get description for configuration used in mock responses."""
        descriptions = {
            "no-rag": "utiliza apenas o conhecimento pré-treinado do modelo",
            "simple-rag": "inclui busca básica por informações relevantes",
            "agentic-rag": "emprega agentes inteligentes para análise contextual",
            "few-shot": "aprende através de exemplos fornecidos",
            "chain-of-thought": "estrutura o raciocínio passo a passo"
        }
        return descriptions.get(self.config, "utiliza configuração personalizada")
    
    def _call_real_api(self, question_text: str) -> Dict[str, Any]:
        """Make real API call for non-dry-run mode."""
        start_time = time.time()
        first_response_time = None
        
        try:
            # Prepare messages based on configuration
            messages = self._prepare_messages(question_text)
            
            # Map internal model names to API names based on base_url
            base_url = os.getenv("LLM_BASE_URL", "")
            
            if "deepseek" in base_url:
                # DeepSeek API mapping
                api_model_map = {
                    "deepseek-r1": "deepseek-reasoner",
                    "deepseek-v3": "deepseek-chat",
                    "claude-opus-4": "deepseek-chat",  # Fallback para testes
                    "gemini-2.5-pro": "deepseek-chat",  # Fallback para testes
                    "gemini-2.5-flash": "deepseek-chat",  # Fallback para testes
                    "openai/gpt-4.0": "deepseek-chat",  # Fallback para testes
                    "openai/gpt-4.1": "deepseek-chat",  # Fallback para testes
                    "openai/o3": "deepseek-reasoner",  # Fallback para testes
                }
            elif "github" in base_url:
                # GitHub Models mapping (publisher/model format)
                api_model_map = {
                    "openai/gpt-4.0": "OpenAI/gpt-4o",
                    "openai/gpt-4.1": "OpenAI/gpt-4o",
                    "openai/o3": "OpenAI/o1-preview",
                    "gemini-2.5-pro": "OpenAI/gpt-4o",  # Fallback para testes
                    "gemini-2.5-flash": "OpenAI/gpt-4o-mini",  # Fallback para testes
                }
            else:
                # OpenAI direct mapping
                api_model_map = {
                    "openai/gpt-4.0": "gpt-4o",
                    "openai/gpt-4.1": "gpt-4o",
                    "openai/o3": "o1-preview",
                    "gemini-2.5-pro": "gpt-4o",  # Fallback para testes
                    "gemini-2.5-flash": "gpt-4o-mini",  # Fallback para testes
                }
            
            # Use mapped model name or original if not in map
            api_model_name = api_model_map.get(self.model_name, self.model_name)
            
            response = self.client.chat.completions.create(
                model=api_model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.1,
                stream=False
            )
            
            if first_response_time is None:
                first_response_time = time.time() - start_time
            
            total_time = time.time() - start_time
            
            # Debug logging
            logger.info(f"API Response: {response}")
            
            # Check if response has choices
            if not response.choices or len(response.choices) == 0:
                raise ValueError("API response has no choices")
            
            # Check if message content exists
            message_content = response.choices[0].message.content
            if message_content is None:
                raise ValueError("API response message content is None")
                
            response_text = message_content
            
            return {
                'response': response_text,
                'first_response_time': first_response_time,
                'total_time': total_time
            }
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
    
    def _prepare_messages(self, question_text: str) -> List[Dict[str, str]]:
        """Prepare messages based on configuration."""
        
        system_prompts = {
            "no-rag": "Você é um especialista em normas técnicas do CBMGO. Responda com base apenas no seu conhecimento.",
            "simple-rag": "Você é um especialista em normas técnicas do CBMGO. Use as informações fornecidas para responder com precisão.",
            "agentic-rag": "Você é um agente especializado em normas técnicas do CBMGO. Analise a questão, busque informações relevantes e forneça uma resposta estruturada.",
            "few-shot": "Você é um especialista em normas técnicas do CBMGO. Aqui estão alguns exemplos de como responder perguntas similares:",
            "chain-of-thought": "Você é um especialista em normas técnicas do CBMGO. Pense passo a passo antes de responder."
        }
        
        system_prompt = system_prompts.get(self.config, "Você é um especialista em normas técnicas do CBMGO.")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question_text}
        ]
        
        # Add configuration-specific modifications
        if self.config == "chain-of-thought":
            messages[1]["content"] += "\n\nPense passo a passo antes de responder."
        elif self.config == "few-shot":
            # In a real implementation, you would add examples here
            messages[1]["content"] = f"Com base nos exemplos de normas técnicas, responda: {question_text}"
        
        return messages
    
    def save_response(
        self, 
        pergunta: Pergunta, 
        api_result: Dict[str, Any]
    ) -> Optional[Resposta]:
        """Save experiment response to database."""
        
        if self.dry_run:
            console.print(f"[dim]  💾 [Simulado] Salvaria resposta para pergunta #{pergunta.numero}[/dim]")
            return None
        
        try:
            resposta = Resposta(
                pergunta_id=pergunta.id,
                modelo_id=self.modelo_obj.id,
                configuracao=self.config,
                resposta_dada=api_result['response'],
                tempo_primeira_resposta=Decimal(str(api_result['first_response_time'])),
                tempo_total=Decimal(str(api_result['total_time'])),
                resposta_correta=False,  # To be evaluated manually later
                fonte_citada=False,  # To be evaluated manually later
            )
            
            # Calculate initial score (will be updated manually later)
            resposta.calcular_somatorio()
            
            if self.overwrite:
                # Check if exists and delete
                existing = self.db.query(Resposta).filter(
                    Resposta.pergunta_id == pergunta.id,
                    Resposta.modelo_id == self.modelo_obj.id,
                    Resposta.configuracao == self.config
                ).first()
                
                if existing:
                    self.db.delete(existing)
                    self.db.commit()
            
            self.db.add(resposta)
            self.db.commit()
            self.db.refresh(resposta)
            
            logger.info(f"Saved response for question {pergunta.numero} with model {self.model_name} config {self.config}")
            return resposta
            
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Response already exists for question {pergunta.numero}: {e}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save response: {e}")
            raise
    
    def run(
        self, 
        max_questions: Optional[int] = None,
        start_from: int = 1
    ):
        """Run the experiment for specified questions."""
        
        questions = self.get_questions_to_process(max_questions, start_from)
        
        if not questions:
            console.print("[yellow]📝 Nenhuma pergunta encontrada para processar[/yellow]")
            return
        
        console.print(f"[green]📋 Encontradas {len(questions)} perguntas para processar[/green]")
        
        if not self.dry_run:
            console.print("[yellow]⚠️  ATENÇÃO: Esta execução fará chamadas reais para a API do OpenAI![/yellow]")
            console.print(f"[blue]💰 Custo estimado: Variável conforme modelo {self.model_name}[/blue]")
        
        # Progress tracking
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
                f"🔄 Processando perguntas [{self.config}]",
                total=len(questions)
            )
            
            success_count = 0
            error_count = 0
            
            for i, pergunta in enumerate(questions, 1):
                
                try:
                    progress.update(
                        task, 
                        description=f"🔄 Pergunta #{pergunta.numero} [{self.config}]"
                    )
                    
                    # Make API call
                    api_result = self.call_openai_api(pergunta.texto)
                    
                    # Save response
                    resposta = self.save_response(pergunta, api_result)
                    
                    if resposta or self.dry_run:
                        success_count += 1
                        console.print(
                            f"[green]✅ #{pergunta.numero}[/green] "
                            f"[dim]({api_result['total_time']:.2f}s)[/dim]"
                        )
                    else:
                        console.print(f"[yellow]⚠️ #{pergunta.numero} (já existe)[/yellow]")
                    
                    # Delay between requests
                    if i < len(questions):  # Don't delay after last question
                        time.sleep(self.delay)
                    
                except KeyboardInterrupt:
                    console.print(f"\n[yellow]⚠️ Interrompido pelo usuário na pergunta #{pergunta.numero}[/yellow]")
                    break
                except Exception as e:
                    error_count += 1
                    console.print(f"[red]❌ #{pergunta.numero}: {e}[/red]")
                    logger.error(f"Error processing question {pergunta.numero}: {e}")
                    
                    # Continue with next question after error
                    if i < len(questions):
                        time.sleep(self.delay)
                
                progress.advance(task)
        
        # Summary
        total_processed = success_count + error_count
        console.print("\n" + "="*50)
        console.print(f"[bold]📊 Resumo da Execução[/bold]")
        console.print(f"[green]✅ Sucessos: {success_count}[/green]")
        console.print(f"[red]❌ Erros: {error_count}[/red]")
        console.print(f"[blue]📈 Total processado: {total_processed}/{len(questions)}[/blue]")
        console.print(f"[cyan]⚙️ Configuração: {self.config}[/cyan]")
        console.print(f"[cyan]🤖 Modelo: {self.model_name}[/cyan]")
        
        if not self.dry_run:
            console.print(f"\n[dim]📝 Log detalhado salvo em: experiment_runs.log[/dim]")