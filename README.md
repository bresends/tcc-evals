# TCC Questions - Sistema de Catalogação LLM

Sistema web para catalogar e analisar respostas de modelos de linguagem grandes (LLMs) aplicados às normas técnicas do CBMGO.

## 🎯 Funcionalidades

- **Dashboard**: Visão geral dos experimentos e estatísticas
- **Gerenciamento de Perguntas**: CRUD para as 92 perguntas do dataset
- **Experimentos**: Catalogar respostas dos 10 modelos LLM
- **Matriz de Experimentos**: Visualização perguntas vs modelos
- **Análises Estatísticas**: Comparações e métricas de desempenho
- **Visualizações**: Gráficos interativos com Plotly
- **Exportação**: Download dos dados em CSV

## 🏗️ Arquitetura

### Stack Tecnológica
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: Jinja2 Templates + Tailwind CSS v4
- **Banco de Dados**: PostgreSQL (Supabase)
- **Visualização**: Plotly.js
- **Análise**: Pandas + NumPy + SciPy
- **Gerenciadores**: UV (Python) + Bun (CSS/JS)

### Estrutura do Projeto
```
tcc-questions/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação principal FastAPI
│   ├── database.py          # Configuração do banco
│   ├── models.py            # Modelos SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic
│   ├── init_data.py         # Script de dados iniciais
│   └── routers/
│       ├── dashboard.py     # Dashboard principal
│       ├── perguntas.py     # Gerenciamento de perguntas
│       ├── experimentos.py  # Catalogação de experimentos
│       └── analises.py      # Análises estatísticas
├── templates/               # Templates Jinja2
├── static/
│   ├── css/                # CSS compilado do Tailwind
│   └── js/                 # JavaScript
├── alembic/                # Migrações do banco
├── .env                    # Configurações de ambiente
├── pyproject.toml          # Dependências Python (UV)
├── package.json            # Dependências CSS/JS (Bun)
└── run.py                  # Script de execução
```

## 🚀 Instalação e Configuração

### Pré-requisitos
- Python 3.11+
- UV (gerenciador de pacotes Python)
- Bun (para Tailwind CSS)
- PostgreSQL (ou acesso ao Supabase)

### 1. Instalar dependências Python
```bash
uv sync
```

### 2. Instalar dependências CSS/JS
```bash
bun install
```

### 3. Executar migrações
```bash
uv run alembic upgrade head
```

### 4. Inicializar dados
```bash
uv run python -m app.init_data
```

### 5. Compilar CSS
```bash
bunx tailwindcss -i static/css/input.css -o static/css/output.css
```

## ▶️ Execução

### Método 1: Script direto
```bash
uv run python run.py
```

### Método 2: Uvicorn
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Método 3: Durante desenvolvimento (com CSS watch)
Terminal 1:
```bash
bun run dev  # Watch do Tailwind CSS
```

Terminal 2:
```bash
uv run python run.py  # Servidor FastAPI
```

## 🌐 Acesso

- **Aplicação**: http://localhost:8000
- **Dashboard**: http://localhost:8000/dashboard
- **Perguntas**: http://localhost:8000/perguntas
- **Experimentos**: http://localhost:8000/experimentos
- **Matriz**: http://localhost:8000/experimentos/matriz
- **Análises**: http://localhost:8000/analises
- **API Docs**: http://localhost:8000/docs

## 📊 Uso do Sistema

### 1. Gerenciar Perguntas
- Acesse `/perguntas` para visualizar as 92 perguntas do dataset
- Use "Nova Pergunta" para adicionar perguntas ao experimento
- Edite/delete perguntas conforme necessário

### 2. Catalogar Experimentos
- Acesse `/experimentos/novo` para inserir resultados
- Selecione a pergunta e modelo LLM
- Preencha as métricas:
  - Tempo de primeira resposta (segundos)
  - Tempo total (segundos)
  - Resposta correta (sim/não)
  - Clareza, Precisão, Concisão (1-5)
  - Fonte citada (sim/não)
  - Observações qualitativas

### 3. Visualizar Matriz
- Acesse `/experimentos/matriz` para ver visão geral
- Visualização tipo grid: perguntas vs modelos
- Status visual dos experimentos realizados

### 4. Analisar Resultados
- Acesse `/analises` para estatísticas comparativas
- Gráficos de taxa de acerto por modelo
- Análise de tempo médio de resposta
- Matriz de correlação entre métricas
- Gráfico radar de qualidade

### 5. Exportar Dados
- Use o botão "Exportar CSV" na navegação
- Download de todos os dados para análise externa
- Formato compatível com Excel/R/Python

## 🎯 Modelos LLM Suportados

O sistema vem pré-configurado com os 10 modelos mencionados no TCC:

1. **Google Gemini 2.5 Pro** (`gemini-2.5-pro`)
2. **Google Gemini 2.5 Flash** (`gemini-2.5-flash`)
3. **OpenAI GPT-4.0** (`gpt-4.0`)
4. **OpenAI GPT-4.1** (`gpt-4.1`)
5. **OpenAI O3** (`o3`)
6. **Anthropic Claude Opus 4** (`claude-opus-4`)
7. **DeepSeek R1** (`deepseek-r1`)
8. **DeepSeek V3** (`deepseek-v3`)
9. **xAI Grok 3** (`grok-3`)
10. **Alibaba Qwen 3 235B** (`qwen-3-235B`)

## 📈 Métricas Coletadas

### Métricas Quantitativas
- **Tempo de primeira resposta**: Tempo até a primeira resposta (segundos)
- **Tempo total**: Tempo total de processamento (segundos)
- **Resposta correta**: Avaliação binária da correção
- **Clareza**: Escala 1-5 para clareza da resposta
- **Precisão**: Escala 1-5 para precisão técnica
- **Concisão**: Escala 1-5 para concisão
- **Fonte citada**: Se o modelo citou a norma correta

### Métricas Derivadas
- **Somatório**: Soma automática das métricas de qualidade
- **Taxa de acerto**: Percentual de respostas corretas por modelo
- **Tempo médio**: Média de tempo de resposta
- **Qualidade média**: Média das métricas de qualidade

## 🎓 Aplicação no TCC

Este sistema suporta diretamente a pesquisa do TCC ao:

1. **Catalogar sistematicamente** todas as 92 perguntas × 10 modelos = 920 experimentos
2. **Medir objetivamente** tempo, acurácia e qualidade das respostas
3. **Comparar estatisticamente** o desempenho entre modelos
4. **Gerar visualizações** para inclusão na dissertação
5. **Exportar dados** para análises estatísticas avançadas (ANOVA, etc.)
6. **Documentar observações** qualitativas para discussão

## 📄 Licença

MIT License - Projeto acadêmico para TCC