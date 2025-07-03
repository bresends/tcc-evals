from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, cast, String
from typing import Optional, List
from decimal import Decimal
import math

from ..database import get_db
from ..models import Pergunta, ModeloLLM, Resposta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def listar_experimentos(
    request: Request, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(25, ge=5, le=100, description="Itens por página"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo LLM"),
    configuracao: Optional[str] = Query(None, description="Filtrar por configuração"),
    norma: Optional[str] = Query(None, description="Filtrar por norma técnica"),
    status: Optional[str] = Query(None, description="Filtrar por status (corretas/incorretas)"),
    fonte_citada: Optional[bool] = Query(None, description="Filtrar por fonte citada"),
    somatorio_min: Optional[int] = Query(None, ge=0, description="Somatório mínimo"),
    somatorio_max: Optional[int] = Query(None, ge=0, description="Somatório máximo"),
    busca: Optional[str] = Query(None, description="Busca por texto"),
    order_by: str = Query("pergunta_numero", description="Campo para ordenação"),
    order_dir: str = Query("asc", description="Direção da ordenação (asc/desc)")
):
    """Lista experimentos com paginação e filtros"""
    
    # Query base
    query = db.query(Resposta).join(Pergunta).join(ModeloLLM)
    
    # Aplicar filtros
    if modelo:
        query = query.filter(ModeloLLM.nome == modelo)
    
    if configuracao:
        query = query.filter(Resposta.configuracao == configuracao)
    
    if norma:
        query = query.filter(Pergunta.norma_tecnica == norma)
    
    if status == "corretas":
        query = query.filter(Resposta.resposta_correta == True)
    elif status == "incorretas":
        query = query.filter(Resposta.resposta_correta == False)
    
    if fonte_citada is not None:
        query = query.filter(Resposta.fonte_citada == fonte_citada)
    
    if somatorio_min is not None:
        query = query.filter(Resposta.somatorio >= somatorio_min)
    
    if somatorio_max is not None:
        query = query.filter(Resposta.somatorio <= somatorio_max)
    
    if busca:
        # Buscar em número da pergunta ou texto da pergunta
        search_filter = or_(
            cast(Pergunta.numero, String).contains(busca),
            Pergunta.texto.icontains(busca),
            Pergunta.norma_artigo.icontains(busca)
        )
        query = query.filter(search_filter)
    
    # Aplicar ordenação
    if order_by == "pergunta_numero":
        order_col = Pergunta.numero
    elif order_by == "modelo":
        order_col = ModeloLLM.nome
    elif order_by == "configuracao":
        order_col = Resposta.configuracao
    elif order_by == "tempo_total":
        order_col = Resposta.tempo_total
    elif order_by == "somatorio":
        order_col = Resposta.somatorio
    elif order_by == "created_at":
        order_col = Resposta.created_at
    else:
        order_col = Pergunta.numero
    
    if order_dir == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())
    
    # Adicionar ordenação secundária por número da pergunta para consistência
    if order_by != "pergunta_numero":
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
    
    # Estatísticas dos resultados filtrados
    stats = {
        'total_experimentos': total_count,
        'total_corretas': query.filter(Resposta.resposta_correta == True).count(),
        'total_com_fonte': query.filter(Resposta.fonte_citada == True).count()
    }
    
    # Parâmetros ativos para o template
    filtros_ativos = {
        'modelo': modelo,
        'configuracao': configuracao,
        'norma': norma,
        'status': status,
        'fonte_citada': fonte_citada,
        'somatorio_min': somatorio_min,
        'somatorio_max': somatorio_max,
        'busca': busca
    }
    
    return templates.TemplateResponse("experimentos/lista.html", {
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
        "order_by": order_by,
        "order_dir": order_dir,
        "stats": stats
    })


@router.get("/novo", response_class=HTMLResponse)
async def novo_experimento_form(
    request: Request, 
    db: Session = Depends(get_db),
    pergunta_id: Optional[int] = None,
    modelo_id: Optional[int] = None,
    configuracao: Optional[str] = None
):
    """Formulário para novo experimento"""
    perguntas = db.query(Pergunta).order_by(Pergunta.numero).all()
    modelos = db.query(ModeloLLM).order_by(ModeloLLM.nome).all()
    
    return templates.TemplateResponse("experimentos/form.html", {
        "request": request,
        "perguntas": perguntas,
        "modelos": modelos,
        "resposta": None,
        "titulo": "Novo Experimento",
        "pergunta_id_preselected": pergunta_id,
        "modelo_id_preselected": modelo_id,
        "configuracao_preselected": configuracao
    })


@router.post("/novo")
async def criar_experimento(
    pergunta_id: int = Form(...),
    modelo_id: int = Form(...),
    configuracao: str = Form(...),
    resposta_dada: Optional[str] = Form(None),
    tempo_primeira_resposta: Optional[float] = Form(None),
    tempo_total: Optional[float] = Form(None),
    resposta_correta: bool = Form(False),
    clareza: Optional[int] = Form(None),
    fundamentacao_tecnica: Optional[int] = Form(None),
    concisao: Optional[int] = Form(None),
    fonte_citada: bool = Form(False),
    observacoes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Criar novo experimento/resposta"""
    
    # Verificar se já existe resposta para esta combinação pergunta/modelo/configuracao
    existente = db.query(Resposta).filter(
        Resposta.pergunta_id == pergunta_id,
        Resposta.modelo_id == modelo_id,
        Resposta.configuracao == configuracao
    ).first()
    
    if existente:
        raise HTTPException(
            status_code=400, 
            detail="Já existe uma resposta para esta combinação pergunta/modelo/configuração"
        )
    
    resposta = Resposta(
        pergunta_id=pergunta_id,
        modelo_id=modelo_id,
        configuracao=configuracao,
        resposta_dada=resposta_dada,
        tempo_primeira_resposta=Decimal(str(tempo_primeira_resposta)) if tempo_primeira_resposta else None,
        tempo_total=Decimal(str(tempo_total)) if tempo_total else None,
        resposta_correta=resposta_correta,
        clareza=clareza,
        fundamentacao_tecnica=fundamentacao_tecnica,
        concisao=concisao,
        fonte_citada=fonte_citada,
        observacoes=observacoes
    )
    
    # Calcular somatório automaticamente
    resposta.calcular_somatorio()
    
    db.add(resposta)
    db.commit()
    db.refresh(resposta)
    
    return RedirectResponse(url="/experimentos", status_code=303)


@router.get("/matriz", response_class=HTMLResponse)
async def matriz_experimentos(
    request: Request, 
    db: Session = Depends(get_db),
    configuracao: str = "no-rag"
):
    """Visualização em matriz: perguntas vs modelos para uma configuração específica"""
    perguntas = db.query(Pergunta).order_by(Pergunta.numero).all()
    modelos = db.query(ModeloLLM).order_by(ModeloLLM.nome).all()
    
    # Obter configurações disponíveis
    configuracoes_disponiveis = db.query(Resposta.configuracao).distinct().all()
    configuracoes = [config[0] for config in configuracoes_disponiveis]
    
    # Garantir que as configurações básicas estejam disponíveis
    configuracoes_basicas = ["no-rag", "simple-rag", "agentic-rag", "few-shot", "chain-of-thought"]
    for config_basica in configuracoes_basicas:
        if config_basica not in configuracoes:
            configuracoes.append(config_basica)
    
    # Se a configuração selecionada não existir, usar no-rag como padrão
    if configuracao not in configuracoes:
        configuracao = "no-rag"
    
    # Criar matriz de respostas para a configuração selecionada
    matriz = {}
    respostas = db.query(Resposta).filter(Resposta.configuracao == configuracao).all()
    
    for resposta in respostas:
        chave = f"{resposta.pergunta_id}_{resposta.modelo_id}_{resposta.configuracao}"
        matriz[chave] = resposta
    
    return templates.TemplateResponse("experimentos/matriz.html", {
        "request": request,
        "perguntas": perguntas,
        "modelos": modelos,
        "matriz": matriz,
        "configuracoes": sorted(configuracoes),
        "configuracao_selecionada": configuracao
    })


@router.get("/{resposta_id}", response_class=HTMLResponse)
async def visualizar_experimento(resposta_id: int, request: Request, db: Session = Depends(get_db)):
    """Visualizar experimento específico"""
    resposta = db.query(Resposta).filter(Resposta.id == resposta_id).first()
    if not resposta:
        raise HTTPException(status_code=404, detail="Experimento não encontrado")
    
    return templates.TemplateResponse("experimentos/detalhe.html", {
        "request": request,
        "resposta": resposta
    })


@router.get("/{resposta_id}/editar", response_class=HTMLResponse)
async def editar_experimento_form(resposta_id: int, request: Request, db: Session = Depends(get_db)):
    """Formulário para editar experimento"""
    resposta = db.query(Resposta).filter(Resposta.id == resposta_id).first()
    if not resposta:
        raise HTTPException(status_code=404, detail="Experimento não encontrado")
    
    perguntas = db.query(Pergunta).order_by(Pergunta.numero).all()
    modelos = db.query(ModeloLLM).order_by(ModeloLLM.nome).all()
    
    return templates.TemplateResponse("experimentos/form.html", {
        "request": request,
        "perguntas": perguntas,
        "modelos": modelos,
        "resposta": resposta,
        "titulo": f"Editar Experimento #{resposta.id}"
    })


@router.post("/{resposta_id}/editar")
async def atualizar_experimento(
    resposta_id: int,
    pergunta_id: int = Form(...),
    modelo_id: int = Form(...),
    configuracao: str = Form(...),
    resposta_dada: Optional[str] = Form(None),
    tempo_primeira_resposta: Optional[float] = Form(None),
    tempo_total: Optional[float] = Form(None),
    resposta_correta: bool = Form(False),
    clareza: Optional[int] = Form(None),
    fundamentacao_tecnica: Optional[int] = Form(None),
    concisao: Optional[int] = Form(None),
    fonte_citada: bool = Form(False),
    observacoes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Atualizar experimento existente"""
    resposta = db.query(Resposta).filter(Resposta.id == resposta_id).first()
    if not resposta:
        raise HTTPException(status_code=404, detail="Experimento não encontrado")
    
    # Verificar se mudou a combinação pergunta/modelo/configuracao e se já existe
    if (resposta.pergunta_id != pergunta_id or 
        resposta.modelo_id != modelo_id or 
        resposta.configuracao != configuracao):
        existente = db.query(Resposta).filter(
            Resposta.pergunta_id == pergunta_id,
            Resposta.modelo_id == modelo_id,
            Resposta.configuracao == configuracao,
            Resposta.id != resposta_id
        ).first()
        
        if existente:
            raise HTTPException(
                status_code=400,
                detail="Já existe uma resposta para esta combinação pergunta/modelo/configuração"
            )
    
    resposta.pergunta_id = pergunta_id
    resposta.modelo_id = modelo_id
    resposta.configuracao = configuracao
    resposta.resposta_dada = resposta_dada
    resposta.tempo_primeira_resposta = Decimal(str(tempo_primeira_resposta)) if tempo_primeira_resposta else None
    resposta.tempo_total = Decimal(str(tempo_total)) if tempo_total else None
    resposta.resposta_correta = resposta_correta
    resposta.clareza = clareza
    resposta.fundamentacao_tecnica = fundamentacao_tecnica
    resposta.concisao = concisao
    resposta.fonte_citada = fonte_citada
    resposta.observacoes = observacoes
    
    # Recalcular somatório
    resposta.calcular_somatorio()
    
    db.commit()
    
    return RedirectResponse(url="/experimentos", status_code=303)