from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from ..database import get_db
from ..models import Pergunta, ModeloLLM, Resposta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def listar_experimentos(request: Request, db: Session = Depends(get_db)):
    """Lista todos os experimentos/respostas"""
    respostas = db.query(Resposta).join(Pergunta).join(ModeloLLM).order_by(
        Pergunta.numero, ModeloLLM.nome
    ).all()
    
    return templates.TemplateResponse("experimentos/lista.html", {
        "request": request,
        "respostas": respostas
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
    precisao: Optional[int] = Form(None),
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
        precisao=precisao,
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
    precisao: Optional[int] = Form(None),
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
    resposta.precisao = precisao
    resposta.concisao = concisao
    resposta.fonte_citada = fonte_citada
    resposta.observacoes = observacoes
    
    # Recalcular somatório
    resposta.calcular_somatorio()
    
    db.commit()
    
    return RedirectResponse(url="/experimentos", status_code=303)