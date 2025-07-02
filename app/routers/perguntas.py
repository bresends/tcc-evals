from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
    busca: Optional[str] = None,
    flag_resposta_duvidosa: Optional[bool] = None,
    flag_questionario_teste: Optional[bool] = None,
    flag_interessante: Optional[bool] = None
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
    
    # Filtros de flags
    if flag_resposta_duvidosa is not None:
        query = query.filter(Pergunta.flag_resposta_duvidosa == flag_resposta_duvidosa)
    
    if flag_questionario_teste is not None:
        query = query.filter(Pergunta.flag_questionario_teste == flag_questionario_teste)
    
    if flag_interessante is not None:
        query = query.filter(Pergunta.flag_interessante == flag_interessante)
    
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
        "filtro_busca": busca,
        "filtro_flag_resposta_duvidosa": flag_resposta_duvidosa,
        "filtro_flag_questionario_teste": flag_questionario_teste,
        "filtro_flag_interessante": flag_interessante
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


@router.post("/{pergunta_id}/toggle-flag-duvidosa")
async def toggle_flag_resposta_duvidosa(pergunta_id: int, request: Request, db: Session = Depends(get_db)):
    """Alternar flag de resposta duvidosa"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    pergunta.flag_resposta_duvidosa = not pergunta.flag_resposta_duvidosa
    db.commit()
    
    # Se for requisição AJAX, retornar JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "flag_resposta_duvidosa": pergunta.flag_resposta_duvidosa,
            "message": "Duvidosa" if pergunta.flag_resposta_duvidosa else "Confirmada"
        })
    
    return RedirectResponse(url="/perguntas", status_code=303)


@router.post("/{pergunta_id}/toggle-flag-teste")
async def toggle_flag_questionario_teste(pergunta_id: int, request: Request, db: Session = Depends(get_db)):
    """Alternar flag de questionário de teste"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    pergunta.flag_questionario_teste = not pergunta.flag_questionario_teste
    db.commit()
    
    # Se for requisição AJAX, retornar JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "flag_questionario_teste": pergunta.flag_questionario_teste,
            "message": "Teste" if pergunta.flag_questionario_teste else "Comum"
        })
    
    return RedirectResponse(url="/perguntas", status_code=303)


@router.post("/{pergunta_id}/toggle-flag-interessante")
async def toggle_flag_interessante(pergunta_id: int, request: Request, db: Session = Depends(get_db)):
    """Alternar flag de pergunta interessante"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    pergunta.flag_interessante = not pergunta.flag_interessante
    db.commit()
    
    # Se for requisição AJAX, retornar JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "flag_interessante": pergunta.flag_interessante,
            "message": "Interessante" if pergunta.flag_interessante else "Comum"
        })
    
    return RedirectResponse(url="/perguntas", status_code=303)


# Rotas HTMX para toggle de flags
@router.post("/{pergunta_id}/htmx-toggle-flag-duvidosa")
async def htmx_toggle_flag_resposta_duvidosa(pergunta_id: int, db: Session = Depends(get_db)):
    """Toggle flag duvidosa via HTMX - retorna fragmento HTML"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    pergunta.flag_resposta_duvidosa = not pergunta.flag_resposta_duvidosa
    db.commit()
    
    # Retornar fragmento HTML do botão atualizado
    button_class = "text-orange-600 bg-orange-50" if pergunta.flag_resposta_duvidosa else "text-gray-600 hover:text-orange-600 hover:bg-orange-50"
    title_text = "Marcar como OK" if pergunta.flag_resposta_duvidosa else "Marcar como duvidosa"
    
    return HTMLResponse(f'''
        <button type="submit" 
               class="inline-flex items-center justify-center w-8 h-8 {button_class} rounded-lg transition-all duration-200 hover:shadow-sm"
               title="{title_text}"
               hx-post="/perguntas/{pergunta_id}/htmx-toggle-flag-duvidosa"
               hx-swap="outerHTML"
               hx-trigger="click"
               hx-target="closest button">
            <span class="text-sm">🚨</span>
        </button>
    ''')


@router.post("/{pergunta_id}/htmx-toggle-flag-teste")
async def htmx_toggle_flag_questionario_teste(pergunta_id: int, db: Session = Depends(get_db)):
    """Toggle flag teste via HTMX - retorna fragmento HTML"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    pergunta.flag_questionario_teste = not pergunta.flag_questionario_teste
    db.commit()
    
    # Retornar fragmento HTML do botão atualizado
    button_class = "text-blue-600 bg-blue-50" if pergunta.flag_questionario_teste else "text-gray-600 hover:text-blue-600 hover:bg-blue-50"
    title_text = "Remover do teste" if pergunta.flag_questionario_teste else "Adicionar ao teste"
    
    return HTMLResponse(f'''
        <button type="submit" 
               class="inline-flex items-center justify-center w-8 h-8 {button_class} rounded-lg transition-all duration-200 hover:shadow-sm"
               title="{title_text}"
               hx-post="/perguntas/{pergunta_id}/htmx-toggle-flag-teste"
               hx-swap="outerHTML"
               hx-trigger="click"
               hx-target="closest button">
            <span class="text-sm">🧪</span>
        </button>
    ''')


@router.post("/{pergunta_id}/htmx-toggle-flag-interessante")
async def htmx_toggle_flag_interessante(pergunta_id: int, db: Session = Depends(get_db)):
    """Toggle flag interessante via HTMX - retorna fragmento HTML"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    pergunta.flag_interessante = not pergunta.flag_interessante
    db.commit()
    
    # Retornar fragmento HTML do botão atualizado
    button_class = "text-yellow-600 bg-yellow-50" if pergunta.flag_interessante else "text-gray-600 hover:text-yellow-600 hover:bg-yellow-50"
    title_text = "Desmarcar como interessante" if pergunta.flag_interessante else "Marcar como interessante"
    
    return HTMLResponse(f'''
        <button type="submit" 
               class="inline-flex items-center justify-center w-8 h-8 {button_class} rounded-lg transition-all duration-200 hover:shadow-sm"
               title="{title_text}"
               hx-post="/perguntas/{pergunta_id}/htmx-toggle-flag-interessante"
               hx-swap="outerHTML"
               hx-trigger="click"
               hx-target="closest button">
            <span class="text-sm">⭐</span>
        </button>
    ''')


@router.get("/{pergunta_id}/htmx-badges")
async def htmx_get_badges(pergunta_id: int, db: Session = Depends(get_db)):
    """Retorna fragmento HTML com badges atualizados"""
    pergunta = db.query(Pergunta).filter(Pergunta.id == pergunta_id).first()
    if not pergunta:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    badges_html = f'''
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
            {pergunta.norma_tecnica}
        </span>
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
            {pergunta.item}
        </span>
    '''
    
    if pergunta.flag_resposta_duvidosa:
        badges_html += '''
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200 flag-duvidosa">
            🚨 Duvidosa
        </span>
        '''
    
    if pergunta.flag_questionario_teste:
        badges_html += '''
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200 flag-teste">
            🧪 Teste
        </span>
        '''
    
    if pergunta.flag_interessante:
        badges_html += '''
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 border border-yellow-200 flag-interessante">
            ⭐ Interessante
        </span>
        '''
    
    return HTMLResponse(badges_html)