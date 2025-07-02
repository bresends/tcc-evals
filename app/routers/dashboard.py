from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from ..database import get_db
from ..models import Pergunta, ModeloLLM, Resposta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal com estatísticas gerais"""
    
    # Contar totais
    total_perguntas = db.query(Pergunta).count()
    total_modelos = db.query(ModeloLLM).count()
    total_respostas = db.query(Resposta).count()
    
    # Calcular progresso
    total_experimentos_possivel = total_perguntas * total_modelos
    progresso_percentual = (total_respostas / total_experimentos_possivel * 100) if total_experimentos_possivel > 0 else 0
    
    # Estatísticas de qualidade
    respostas_corretas = db.query(Resposta).filter(Resposta.resposta_correta == True).count()
    taxa_acerto = (respostas_corretas / total_respostas * 100) if total_respostas > 0 else 0
    
    # Tempo médio
    tempo_medio = db.query(func.avg(Resposta.tempo_total)).scalar() or 0
    
    # Estatísticas das flags
    perguntas_duvidosas = db.query(Pergunta).filter(Pergunta.flag_resposta_duvidosa == True).count()
    perguntas_teste = db.query(Pergunta).filter(Pergunta.flag_questionario_teste == True).count()
    perguntas_interessantes = db.query(Pergunta).filter(Pergunta.flag_interessante == True).count()
    
    # Estatísticas por modelo (top 5)
    stats_modelos = db.query(
        ModeloLLM.nome,
        func.count(Resposta.id).label('total_respostas'),
        func.sum(func.cast(Resposta.resposta_correta, Integer)).label('corretas'),
        func.avg(Resposta.tempo_total).label('tempo_medio'),
        func.avg(Resposta.somatorio).label('somatorio_medio')
    ).join(Resposta).group_by(ModeloLLM.id, ModeloLLM.nome).limit(5).all()
    
    context = {
        "request": request,
        "total_perguntas": total_perguntas,
        "total_modelos": total_modelos,
        "total_respostas": total_respostas,
        "progresso_percentual": round(progresso_percentual, 1),
        "taxa_acerto": round(taxa_acerto, 1),
        "perguntas_duvidosas": perguntas_duvidosas,
        "perguntas_teste": perguntas_teste,
        "perguntas_interessantes": perguntas_interessantes,
        "tempo_medio": round(float(tempo_medio), 2) if tempo_medio else 0,
        "stats_modelos": stats_modelos
    }
    
    return templates.TemplateResponse("dashboard.html", context)