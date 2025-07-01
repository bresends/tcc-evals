from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Pergunta
from ..schemas import PerguntaCreate

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def listar_perguntas(
    request: Request, 
    db: Session = Depends(get_db),
    norma_tecnica: Optional[str] = None,
    item: Optional[str] = None,
    busca: Optional[str] = None
):
    """Lista todas as perguntas cadastradas com filtros opcionais"""
    
    # Query base
    query = db.query(Pergunta)
    
    # Aplicar filtros
    if norma_tecnica:
        query = query.filter(Pergunta.norma_tecnica == norma_tecnica)
    
    if item:
        query = query.filter(Pergunta.item.ilike(f'%{item}%'))
    
    if busca:
        query = query.filter(
            Pergunta.texto.ilike(f'%{busca}%') | 
            Pergunta.resposta_esperada.ilike(f'%{busca}%')
        )
    
    # Executar query
    perguntas = query.order_by(Pergunta.numero).all()
    
    # Buscar listas para os filtros
    normas_disponiveis = db.query(Pergunta.norma_tecnica).distinct().order_by(Pergunta.norma_tecnica).all()
    normas_disponiveis = [n[0] for n in normas_disponiveis]
    
    itens_disponiveis = db.query(Pergunta.item).distinct().order_by(Pergunta.item).all()
    itens_disponiveis = [i[0] for i in itens_disponiveis]
    
    return templates.TemplateResponse("perguntas/lista.html", {
        "request": request,
        "perguntas": perguntas,
        "normas_disponiveis": normas_disponiveis,
        "itens_disponiveis": itens_disponiveis,
        "filtro_norma": norma_tecnica,
        "filtro_item": item,
        "filtro_busca": busca
    })


@router.get("/nova", response_class=HTMLResponse)
async def nova_pergunta_form(request: Request):
    """Formulário para criar nova pergunta"""
    return templates.TemplateResponse("perguntas/form.html", {
        "request": request,
        "pergunta": None,
        "titulo": "Nova Pergunta"
    })


@router.post("/nova")
async def criar_pergunta(
    numero: int = Form(...),
    texto: str = Form(...),
    resposta_esperada: str = Form(...),
    norma_tecnica: str = Form(...),
    item: str = Form(...),
    db: Session = Depends(get_db)
):
    """Criar nova pergunta"""
    
    # Verificar se número já existe
    if db.query(Pergunta).filter(Pergunta.numero == numero).first():
        raise HTTPException(status_code=400, detail=f"Pergunta número {numero} já existe")
    
    # Criar campo combinado para compatibilidade
    norma_artigo = f"{norma_tecnica} - {item}"
    
    pergunta = Pergunta(
        numero=numero,
        texto=texto,
        resposta_esperada=resposta_esperada,
        norma_tecnica=norma_tecnica,
        item=item,
        norma_artigo=norma_artigo
    )
    
    db.add(pergunta)
    db.commit()
    db.refresh(pergunta)
    
    return RedirectResponse(url="/perguntas", status_code=303)


@router.get("/{pergunta_id}", response_class=HTMLResponse)
async def visualizar_pergunta(pergunta_id: int, request: Request, db: Session = Depends(get_db)):
    """Visualizar pergunta específica"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    return templates.TemplateResponse("perguntas/detalhe.html", {
        "request": request,
        "pergunta": pergunta
    })


@router.get("/{pergunta_id}/editar", response_class=HTMLResponse)
async def editar_pergunta_form(pergunta_id: int, request: Request, db: Session = Depends(get_db)):
    """Formulário para editar pergunta"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    return templates.TemplateResponse("perguntas/form.html", {
        "request": request,
        "pergunta": pergunta,
        "titulo": f"Editar Pergunta #{pergunta.numero}"
    })


@router.post("/{pergunta_id}/editar")
async def atualizar_pergunta(
    pergunta_id: int,
    numero: int = Form(...),
    texto: str = Form(...),
    resposta_esperada: str = Form(...),
    norma_tecnica: str = Form(...),
    item: str = Form(...),
    db: Session = Depends(get_db)
):
    """Atualizar pergunta existente"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    # Verificar se número já existe em outra pergunta
    if pergunta.numero != numero:
        if db.query(Pergunta).filter(Pergunta.numero == numero, Pergunta.id != pergunta_id).first():
            raise HTTPException(status_code=400, detail=f"Pergunta número {numero} já existe")
    
    # Criar campo combinado para compatibilidade
    norma_artigo = f"{norma_tecnica} - {item}"
    
    pergunta.numero = numero
    pergunta.texto = texto
    pergunta.resposta_esperada = resposta_esperada
    pergunta.norma_tecnica = norma_tecnica
    pergunta.item = item
    pergunta.norma_artigo = norma_artigo
    
    db.commit()
    
    return RedirectResponse(url="/perguntas", status_code=303)


@router.post("/{pergunta_id}/deletar")
async def deletar_pergunta(pergunta_id: int, db: Session = Depends(get_db)):
    """Deletar pergunta"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    db.delete(pergunta)
    db.commit()
    
    return RedirectResponse(url="/perguntas", status_code=303)