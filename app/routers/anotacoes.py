from fastapi import APIRouter, Depends, Request, HTTPException, Query, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional
import math
from datetime import datetime

from ..database import get_db
from ..models import Pergunta, ModeloLLM, Resposta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def listar_anotacoes(
    request: Request, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(10, ge=5, le=50, description="Itens por página"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo LLM"),
    configuracao: Optional[str] = Query(None, description="Filtrar por configuração"),
    norma: Optional[str] = Query(None, description="Filtrar por norma técnica"),
    status: Optional[str] = Query(None, description="Filtrar por status de avaliação"),
    busca: Optional[str] = Query(None, description="Busca por texto"),
):
    """Lista respostas para anotação manual com comparação lado a lado"""
    
    # Query base - mostrar apenas respostas não anotadas manualmente
    query = db.query(Resposta).join(Pergunta).join(ModeloLLM).filter(Resposta.human_annotation.is_(None))
    
    # Aplicar filtros
    if modelo:
        query = query.filter(ModeloLLM.nome == modelo)
    
    if configuracao:
        query = query.filter(Resposta.configuracao == configuracao)
    
    if norma:
        query = query.filter(Pergunta.norma_tecnica == norma)
    
    # Filtros de status não são mais necessários já que só mostramos não anotadas
    # Mas mantemos para compatibilidade se necessário
    if status == "com_resposta":
        query = query.filter(Resposta.resposta_dada.isnot(None))
    elif status == "sem_resposta":
        query = query.filter(Resposta.resposta_dada.is_(None))
    
    if busca:
        # Buscar em número da pergunta ou texto da pergunta
        search_filter = or_(
            Pergunta.numero.like(f"%{busca}%"),
            Pergunta.texto.ilike(f"%{busca}%"),
            Pergunta.norma_artigo.ilike(f"%{busca}%")
        )
        query = query.filter(search_filter)
    
    # Ordenar por número da pergunta
    query = query.order_by(Pergunta.numero.asc())
    
    # Contar total de registros
    total_count = query.count()
    
    # Aplicar paginação
    offset = (page - 1) * per_page
    respostas = query.offset(offset).limit(per_page).all()
    
    # Calcular metadados de paginação
    total_pages = math.ceil(total_count / per_page)
    has_prev = page > 1
    has_next = page < total_pages
    
    # Obter dados para filtros
    modelos_disponiveis = db.query(ModeloLLM.nome).distinct().order_by(ModeloLLM.nome).all()
    modelos_disponiveis = [m[0] for m in modelos_disponiveis]
    
    configuracoes_disponiveis = db.query(Resposta.configuracao).distinct().order_by(Resposta.configuracao).all()
    configuracoes_disponiveis = [c[0] for c in configuracoes_disponiveis]
    
    normas_disponiveis = db.query(Pergunta.norma_tecnica).distinct().order_by(Pergunta.norma_tecnica).all()
    normas_disponiveis = [n[0] for n in normas_disponiveis]
    
    # Estatísticas dos resultados filtrados - todas são pendentes de anotação manual
    stats = {
        'total_respostas': total_count,
        'total_com_resposta': query.filter(Resposta.resposta_dada.isnot(None)).count(),
        'total_sem_resposta': query.filter(Resposta.resposta_dada.is_(None)).count(),
        'total_pendentes': total_count  # Todas são pendentes de anotação manual
    }
    
    # Parâmetros ativos para o template
    filtros_ativos = {
        'modelo': modelo,
        'configuracao': configuracao,
        'norma': norma,
        'status': status,
        'busca': busca
    }
    
    return templates.TemplateResponse("anotacoes/lista.html", {
        "request": request,
        "respostas": respostas,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
            "start_item": offset + 1 if respostas else 0,
            "end_item": min(offset + per_page, total_count)
        },
        "filtros": {
            "modelos_disponiveis": modelos_disponiveis,
            "configuracoes_disponiveis": configuracoes_disponiveis,
            "normas_disponiveis": normas_disponiveis
        },
        "filtros_ativos": filtros_ativos,
        "stats": stats
    })


@router.post("/{resposta_id}/avaliar")
async def avaliar_resposta(
    resposta_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Endpoint AJAX para marcar resposta como certa ou errada"""
    
    resposta = db.query(Resposta).filter(Resposta.id == resposta_id).first()
    if not resposta:
        raise HTTPException(status_code=404, detail="Resposta não encontrada")
    
    correta = payload.get("correta")
    if correta is None:
        raise HTTPException(status_code=400, detail="Campo 'correta' é obrigatório")
    
    # Atualizar campos de anotação manual
    resposta.human_annotation = correta
    resposta.human_annotation_timestamp = datetime.now()
    resposta.resposta_correta = correta  # Manter compatibilidade
    
    # Recalcular somatório se necessário
    resposta.calcular_somatorio()
    
    db.commit()
    
    return JSONResponse({
        "success": True,
        "resposta_id": resposta_id,
        "correta": correta,
        "somatorio": resposta.somatorio,
        "anotado_manualmente": True
    })