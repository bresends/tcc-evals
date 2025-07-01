# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web application for cataloging and analyzing Large Language Model (LLM) responses applied to technical fire safety standards from CBMGO (Corpo de Bombeiros Militar de Goiás). The system supports academic research by systematically comparing 10 different LLM models across 92 standardized questions.

## Architecture

**Multi-layered FastAPI application with PostgreSQL backend:**
- **Data Layer**: SQLAlchemy models (`Pergunta`, `ModeloLLM`, `Resposta`) with calculated metrics
- **API Layer**: FastAPI routers organized by domain (dashboard, perguntas, experimentos, analises)  
- **Presentation Layer**: Jinja2 templates with Tailwind CSS v4 and Plotly visualizations
- **Database**: PostgreSQL (Supabase) with Alembic migrations

**Key Design Patterns:**
- Router-based API organization with domain separation
- Automatic metric calculation via model methods (`calcular_somatorio()`)
- Template inheritance with consistent navigation and styling
- Statistical analysis integration via Pandas/NumPy in analysis routes

## Essential Commands

### Development Setup
```bash
# Install Python dependencies
uv sync

# Install CSS dependencies  
bun install

# Run database migrations
uv run alembic upgrade head

# Initialize with pre-configured LLM models
uv run python -m app.init_data

# Compile Tailwind CSS
bunx tailwindcss -i static/css/input.css -o static/css/output.css
```

### Running the Application
```bash
# Development with auto-reload
uv run python run.py

# Alternative with uvicorn directly
uv run uvicorn app.main:app --reload

# Development with CSS watching (2 terminals)
bun run dev  # Terminal 1: CSS watch
uv run python run.py  # Terminal 2: API server
```

### Database Operations
```bash
# Create new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Reset data (re-run initialization)
uv run python -m app.init_data
```

### Code Quality
```bash
# Format code
uv run black app/

# Sort imports
uv run isort app/

# Lint code
uv run flake8 app/
```

## Data Model Architecture

**Core Entities:**
- `Pergunta`: Research questions (1-92) with expected answers and norm references
- `ModeloLLM`: LLM models (pre-configured with 10 research models)
- `Resposta`: Experiment results linking questions to models with metrics

**Metric System:**
- Quantitative: Response time, correctness (boolean), quality scales (1-5)
- Automatic: Calculated `somatorio` field via `calcular_somatorio()` method
- Qualitative: Free-text observations field

**Database Considerations:**
- PostgreSQL with Decimal precision for timing metrics
- Unique constraints on question numbers and model names
- Foreign key relationships with cascading for data integrity

## Router Organization

**Domain-Driven Structure:**
- `dashboard.py`: Aggregate statistics and overview metrics
- `perguntas.py`: CRUD operations for research questions
- `experimentos.py`: Experiment data entry and matrix visualization
- `analises.py`: Statistical analysis with Plotly chart generation

**Template Routing:**
- All routes return HTML via Jinja2 templates
- Form submissions use FastAPI Form dependencies
- Statistical visualizations embedded as HTML via Plotly

## Styling and Frontend

**Tailwind CSS v4 Implementation:**
- Uses `@import "tailwindcss"` in input.css
- Compiled via Bun's tailwindcss CLI
- No configuration file needed (v4 zero-config approach)
- Base template provides consistent navigation and responsive layout

**Chart Integration:**
- Plotly.js v2.35.2 loaded via CDN in base template
- Charts generated server-side and embedded as HTML divs using `plotly.offline.plot()`
- Responsive design with mobile-first approach
- Use `include_plotlyjs=False` to avoid conflicts with CDN version

## Configuration Notes

**Environment Setup:**
- Database URL configured via `.env` file (Supabase PostgreSQL)
- No additional environment variables required
- Static file serving configured for `/static` route

**Package Management:**
- Python: UV with pyproject.toml configuration
- CSS/JS: Bun for Tailwind compilation only
- No Node.js runtime dependencies in production

## Research Context

This system specifically supports academic research comparing LLM performance on technical fire safety standards. The 10 pre-configured models represent current state-of-the-art LLMs including GPT-4 variants, Gemini, Claude, and others. The 92-question dataset is designed for statistical analysis (ANOVA) comparing model performance across multiple dimensions.

## Common Issues and Solutions

**Template Errors:**
- If templates show "undefined" variables, ensure routes pass complete context dictionaries
- Main `/` route redirects to `/dashboard` to avoid template variable issues
- All dashboard data must be fetched from database before template rendering

**Database Connection:**
- Uses PostgreSQL via Supabase with connection string in `.env`
- Alembic handles migrations - always run `alembic upgrade head` after model changes
- Initial data populated via `app.init_data` module

**CSS Compilation:**
- Tailwind CSS must be compiled before use: `bunx tailwindcss -i static/css/input.css -o static/css/output.css`
- Use `bun run dev` for development watching
- Tailwind v4 uses `@import "tailwindcss"` syntax in input.css

**Plotly Visualizations:**
- Use `include_plotlyjs=False` in `plot()` calls to avoid CDN conflicts
- Charts are embedded as HTML divs in templates
- Plotly v2.35.2 loaded via CDN for consistency