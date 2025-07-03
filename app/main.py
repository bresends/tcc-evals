from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

from .routers import dashboard, perguntas, experimentos, analises, anotacoes
from .database import engine
from . import models

# Criar tabelas se não existirem
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TCC Questions - Sistema de Catalogação LLM",
    description="Sistema para catalogar e analisar respostas de modelos LLM para normas técnicas do CBMGO",
    version="1.0.0"
)

# Configurar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Incluir routers
app.include_router(dashboard.router, prefix="", tags=["Dashboard"])
app.include_router(perguntas.router, prefix="/perguntas", tags=["Perguntas"])
app.include_router(experimentos.router, prefix="/experimentos", tags=["Experimentos"])
app.include_router(analises.router, prefix="/analises", tags=["Análises"])
app.include_router(anotacoes.router, prefix="/anotacoes", tags=["Anotações"])


@app.get("/")
async def root():
    """Página inicial - redireciona para dashboard"""
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "tcc-questions"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)