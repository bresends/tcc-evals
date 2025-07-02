# TCC Questions CLI - Guia de Uso

Este documento explica como usar a ferramenta CLI para execução automatizada de experimentos com modelos LLM no sistema TCC Questions.

## Índice

- [Visão Geral](#visão-geral)
- [Configuração Inicial](#configuração-inicial)
- [Comandos Disponíveis](#comandos-disponíveis)
- [Configurações Experimentais](#configurações-experimentais)
- [Exemplos Práticos](#exemplos-práticos)
- [Solução de Problemas](#solução-de-problemas)

## Visão Geral

A CLI do TCC Questions permite executar experimentos automatizados com diferentes modelos LLM para avaliar respostas às 92 perguntas sobre normas técnicas do CBMGO. O sistema suporta múltiplas configurações experimentais e integração com APIs de LLM.

### Funcionalidades Principais

- ✅ Execução automatizada de experimentos
- ✅ Suporte a múltiplos modelos LLM
- ✅ Diferentes configurações experimentais (no-rag, simple-rag, etc.)
- ✅ Integração com GitHub Models e OpenAI
- ✅ Sistema de logging detalhado
- ✅ Modo dry-run para testes
- ✅ Controle de rate limiting
- ✅ Relatórios de progresso em tempo real

## Configuração Inicial

### 1. Variáveis de Ambiente

Configure as variáveis no arquivo `.env`:

```bash
# Para GitHub Models
LLM_API_KEY=ghp_your_github_token_here
LLM_BASE_URL=https://models.github.ai/inference

# Para OpenAI (alternativo)
OPENAI_API_KEY=sk-your_openai_key_here

# Database (já configurado)
DATABASE_URL=postgresql://...
```

### 2. Dependências

Certifique-se de que todas as dependências estão instaladas:

```bash
uv sync
```

### 3. Verificação da Configuração

Teste se a configuração está correta:

```bash
uv run python -m app.cli.main list-models
```

## Comandos Disponíveis

### `list-models`
Lista todos os modelos LLM disponíveis no sistema.

```bash
uv run python -m app.cli.main list-models
```

**Exemplo de saída:**
```
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID ┃ Nome                     ┃ Descrição                                    ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1  │ gemini-2.5-pro           │ Google Gemini 2.5 Pro - Modelo avançado     │
│ 2  │ gemini-2.5-flash         │ Google Gemini 2.5 Flash - Versão otimizada  │
│ 3  │ openai/gpt-4.0           │ OpenAI GPT-4.0 - Modelo de linguagem        │
└────┴──────────────────────────┴──────────────────────────────────────────────┘
```

### `status`
Exibe o status dos experimentos por modelo e configuração.

```bash
# Status geral
uv run python -m app.cli.main status

# Status filtrado por modelo
uv run python -m app.cli.main status --model "openai/gpt-4.0"

# Status filtrado por configuração
uv run python -m app.cli.main status --config "no-rag"
```

**Exemplo de saída:**
```
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┓
┃ Modelo         ┃ Configuração ┃ Concluídos ┃ Total ┃ Progresso   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━┩
│ openai/gpt-4.0 │ no-rag       │ 8          │ 92    │ 8/92 (8.7%) │
│ openai/gpt-4.0 │ simple-rag   │ 0          │ 92    │ 0/92 (0.0%) │
└────────────────┴──────────────┴────────────┴───────┴─────────────┘
```

### `run-experiments`
Executa experimentos automatizados com modelos LLM.

```bash
uv run python -m app.cli.main run-experiments --model "MODELO" --config "CONFIGURAÇÃO" [OPÇÕES]
```

**Parâmetros obrigatórios:**
- `--model, -m`: Nome do modelo LLM
- `--config, -c`: Configuração experimental

**Parâmetros opcionais:**
- `--questions, -q`: Número de perguntas a executar (padrão: todas)
- `--start-from, -s`: Pergunta inicial (padrão: 1)
- `--delay, -d`: Delay entre chamadas da API em segundos (padrão: 1.0)
- `--dry-run`: Simular execução sem fazer chamadas de API
- `--overwrite`: Sobrescrever respostas existentes

## Configurações Experimentais

O sistema suporta 5 configurações experimentais diferentes:

### 1. `no-rag`
- **Descrição**: Utiliza apenas o conhecimento pré-treinado do modelo
- **Prompt**: "Você é um especialista em normas técnicas do CBMGO. Responda com base apenas no seu conhecimento."
- **Uso**: Linha de base para comparação

### 2. `simple-rag`
- **Descrição**: Inclui busca básica por informações relevantes
- **Prompt**: "Você é um especialista em normas técnicas do CBMGO. Use as informações fornecidas para responder com precisão."
- **Uso**: RAG básico com recuperação de documentos

### 3. `agentic-rag`
- **Descrição**: Emprega agentes inteligentes para análise contextual
- **Prompt**: "Você é um agente especializado em normas técnicas do CBMGO. Analise a questão, busque informações relevantes e forneça uma resposta estruturada."
- **Uso**: RAG avançado com raciocínio multi-etapas

### 4. `few-shot`
- **Descrição**: Aprende através de exemplos fornecidos
- **Prompt**: "Você é um especialista em normas técnicas do CBMGO. Aqui estão alguns exemplos de como responder perguntas similares:"
- **Uso**: Aprendizado por exemplos

### 5. `chain-of-thought`
- **Descrição**: Estrutura o raciocínio passo a passo
- **Prompt**: "Você é um especialista em normas técnicas do CBMGO. Pense passo a passo antes de responder."
- **Uso**: Raciocínio explícito e estruturado

## Exemplos Práticos

### Exemplo 1: Simulação Básica
Teste o sistema sem gastar tokens da API:

```bash
uv run python -m app.cli.main run-experiments \
  --model "openai/gpt-4.0" \
  --config "no-rag" \
  --questions 5 \
  --dry-run
```

### Exemplo 2: Experimento Real com 10 Perguntas
Execute um experimento real com delay de 2 segundos:

```bash
uv run python -m app.cli.main run-experiments \
  --model "openai/gpt-4.0" \
  --config "no-rag" \
  --questions 10 \
  --delay 2.0
```

### Exemplo 3: Continuar de onde Parou
Continue um experimento a partir da pergunta 21:

```bash
uv run python -m app.cli.main run-experiments \
  --model "gemini-2.5-pro" \
  --config "simple-rag" \
  --start-from 21 \
  --delay 1.5
```

### Exemplo 4: Sobrescrever Respostas Existentes
Reexecute experimentos sobrescrevendo dados existentes:

```bash
uv run python -m app.cli.main run-experiments \
  --model "openai/gpt-4.0" \
  --config "no-rag" \
  --questions 5 \
  --overwrite
```

### Exemplo 5: Experimento Completo
Execute todas as 92 perguntas para um modelo:

```bash
uv run python -m app.cli.main run-experiments \
  --model "openai/gpt-4.0" \
  --config "chain-of-thought" \
  --delay 1.0
```

## Mapeamento de Modelos

O sistema mapeia automaticamente os nomes dos modelos internos para os nomes da API:

| Modelo Interno | API GitHub Models | API OpenAI |
|----------------|-------------------|------------|
| `openai/gpt-4.0` | `OpenAI/gpt-4o` | `gpt-4o` |
| `openai/gpt-4.1` | `OpenAI/gpt-4o` | `gpt-4o` |
| `openai/o3` | `OpenAI/o1-preview` | `o1-preview` |
| `gemini-2.5-pro` | `OpenAI/gpt-4o` | `gpt-4o` |
| `gemini-2.5-flash` | `OpenAI/gpt-4o-mini` | `gpt-4o-mini` |

## Monitoramento e Logs

### Progress Tracking
O sistema exibe progresso em tempo real:

```
🔄 Processando perguntas [no-rag] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 80% 0:02:15
✅ #1 (11.17s)
✅ #2 (19.75s)
✅ #3 (15.32s)
```

### Logs Detalhados
Os logs são salvos automaticamente em `experiment_runs.log`:

```bash
tail -f experiment_runs.log
```

### Resumo Final
Ao final da execução, é exibido um resumo:

```
==================================================
📊 Resumo da Execução
✅ Sucessos: 8
❌ Erros: 0
📈 Total processado: 8/10
⚙️ Configuração: no-rag
🤖 Modelo: openai/gpt-4.0
```

## Solução de Problemas

### Erro: Model not found
**Problema**: `Model not found; expected format: {publisher}/{model_name}`

**Solução**: Verifique se o modelo está corretamente cadastrado no banco de dados:
```bash
uv run python -m app.cli.main list-models
```

### Erro: API Key not set
**Problema**: `LLM_API_KEY or OPENAI_API_KEY environment variable not set`

**Solução**: Configure as variáveis de ambiente no arquivo `.env`:
```bash
echo "LLM_API_KEY=seu_token_aqui" >> .env
```

### Erro: Rate Limiting
**Problema**: Muitas chamadas para a API muito rapidamente

**Solução**: Aumente o delay entre chamadas:
```bash
--delay 3.0
```

### Erro: Timeout
**Problema**: Comando interrompido por timeout

**Solução**: Execute em lotes menores:
```bash
--questions 20
```

### Respostas Duplicadas
**Problema**: Experimento já executado anteriormente

**Solução**: Use `--overwrite` para sobrescrever ou verifique o status:
```bash
uv run python -m app.cli.main status --model "modelo" --config "config"
```

## Workflows Recomendados

### Para Pesquisa Acadêmica

1. **Teste inicial**: Execute dry-run para validar configuração
2. **Piloto**: Execute 10 perguntas para cada configuração
3. **Validação**: Analise os resultados no dashboard web
4. **Execução completa**: Execute todas as 92 perguntas
5. **Análise**: Use ferramentas de análise estatística

### Para Desenvolvimento

1. **Debug**: Use dry-run para testar alterações
2. **Validação**: Execute subset pequeno com dados reais
3. **Benchmark**: Compare diferentes configurações
4. **Otimização**: Ajuste prompts e parâmetros

## Considerações de Custos

- **GitHub Models**: Gratuito com limitações de rate
- **OpenAI**: Custos por token (GPT-4o: ~$0.005/1K tokens)
- **Estimativa**: 92 perguntas ≈ 5-10 USD por modelo/configuração

Use `--dry-run` extensivamente para evitar custos desnecessários durante desenvolvimento.

## Próximos Passos

Após executar os experimentos:

1. Acesse o dashboard web em `http://localhost:8000/dashboard`
2. Visualize a matriz de experimentos em `/experimentos/matriz`
3. Analise resultados individuais
4. Execute análises estatísticas
5. Exporte dados para ferramentas externas

---

**Desenvolvido para o projeto TCC Questions - Sistema de Avaliação de LLMs em Normas Técnicas do CBMGO**