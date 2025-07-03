from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
import json
from io import StringIO

from ..database import get_db
from ..models import Pergunta, ModeloLLM, Resposta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def analises_gerais(request: Request, db: Session = Depends(get_db)):
    """Página principal de análises estatísticas"""
    
    # Estatísticas por modelo
    stats_query = db.query(
        ModeloLLM.nome,
        func.count(Resposta.id).label('total_respostas'),
        func.sum(func.cast(Resposta.resposta_correta, Integer)).label('corretas'),
        func.avg(Resposta.tempo_total).label('tempo_medio'),
        func.avg(Resposta.clareza).label('clareza_media'),
        func.avg(Resposta.fundamentacao_tecnica).label('fundamentacao_media'),
        func.avg(Resposta.concisao).label('concisao_media'),
        func.avg(Resposta.somatorio).label('somatorio_medio'),
        func.sum(func.cast(Resposta.fonte_citada, Integer)).label('fontes_citadas')
    ).join(Resposta).group_by(ModeloLLM.id, ModeloLLM.nome).all()
    
    # Estatísticas por norma técnica
    stats_norma_query = db.query(
        Pergunta.norma_tecnica,
        func.count(Resposta.id).label('total_respostas'),
        func.sum(func.cast(Resposta.resposta_correta, Integer)).label('corretas'),
        func.avg(Resposta.tempo_total).label('tempo_medio'),
        func.avg(Resposta.somatorio).label('somatorio_medio')
    ).join(Resposta).group_by(Pergunta.norma_tecnica).all()
    
    # Processar dados para gráficos
    stats_data = []
    for stat in stats_query:
        taxa_acerto = (stat.corretas / stat.total_respostas * 100) if stat.total_respostas > 0 else 0
        taxa_fontes = (stat.fontes_citadas / stat.total_respostas * 100) if stat.total_respostas > 0 else 0
        
        stats_data.append({
            'modelo': stat.nome,
            'total_respostas': stat.total_respostas,
            'corretas': stat.corretas,
            'taxa_acerto': round(taxa_acerto, 1),
            'tempo_medio': round(float(stat.tempo_medio), 2) if stat.tempo_medio else 0,
            'clareza_media': round(float(stat.clareza_media), 2) if stat.clareza_media else 0,
            'fundamentacao_media': round(float(stat.fundamentacao_media), 2) if stat.fundamentacao_media else 0,
            'concisao_media': round(float(stat.concisao_media), 2) if stat.concisao_media else 0,
            'somatorio_medio': round(float(stat.somatorio_medio), 2) if stat.somatorio_medio else 0,
            'fontes_citadas': stat.fontes_citadas,
            'taxa_fontes': round(taxa_fontes, 1)
        })
    
    # Processar dados por norma técnica
    stats_norma_data = []
    for stat in stats_norma_query:
        taxa_acerto = (stat.corretas / stat.total_respostas * 100) if stat.total_respostas > 0 else 0
        
        stats_norma_data.append({
            'norma_tecnica': stat.norma_tecnica,
            'total_respostas': stat.total_respostas,
            'corretas': stat.corretas,
            'taxa_acerto': round(taxa_acerto, 1),
            'tempo_medio': round(float(stat.tempo_medio), 2) if stat.tempo_medio else 0,
            'somatorio_medio': round(float(stat.somatorio_medio), 2) if stat.somatorio_medio else 0
        })
    
    # Gráfico de taxa de acerto
    if stats_data:
        fig_acerto = px.bar(
            stats_data, 
            x='modelo', 
            y='taxa_acerto',
            title='Taxa de Acerto por Modelo LLM (%)',
            labels={'taxa_acerto': 'Taxa de Acerto (%)', 'modelo': 'Modelo LLM'}
        )
        fig_acerto.update_layout(height=400)
        grafico_acerto = plot(fig_acerto, output_type='div', include_plotlyjs=False)
        
        # Gráfico de tempo médio
        fig_tempo = px.bar(
            stats_data,
            x='modelo',
            y='tempo_medio',
            title='Tempo Médio de Resposta por Modelo (segundos)',
            labels={'tempo_medio': 'Tempo Médio (s)', 'modelo': 'Modelo LLM'}
        )
        fig_tempo.update_layout(height=400)
        grafico_tempo = plot(fig_tempo, output_type='div', include_plotlyjs=False)
        
        # Gráfico radar - qualidade média
        categorias = ['Clareza', 'Fundamentação', 'Concisão', 'Taxa Acerto', 'Taxa Fontes']
        fig_radar = go.Figure()
        
        for stat in stats_data[:5]:  # Limitar a 5 modelos para não poluir
            valores = [
                stat['clareza_media'],
                stat['fundamentacao_media'], 
                stat['concisao_media'],
                stat['taxa_acerto'] / 20,  # Normalizar para escala 0-5
                stat['taxa_fontes'] / 20   # Normalizar para escala 0-5
            ]
            
            fig_radar.add_trace(go.Scatterpolar(
                r=valores,
                theta=categorias,
                fill='toself',
                name=stat['modelo']
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5]
                )),
            showlegend=True,
            title="Comparação de Qualidade entre Modelos",
            height=500
        )
        grafico_radar = plot(fig_radar, output_type='div', include_plotlyjs=False)
        
        # Gráfico por norma técnica
        if stats_norma_data:
            fig_norma = px.bar(
                stats_norma_data,
                x='norma_tecnica',
                y='taxa_acerto',
                title='Taxa de Acerto por Norma Técnica (%)',
                labels={'taxa_acerto': 'Taxa de Acerto (%)', 'norma_tecnica': 'Norma Técnica'},
                color='taxa_acerto',
                color_continuous_scale='Viridis'
            )
            fig_norma.update_layout(height=400)
            grafico_norma = plot(fig_norma, output_type='div', include_plotlyjs=False)
        else:
            grafico_norma = "<p>Nenhum dado disponível para análise</p>"
    else:
        grafico_acerto = "<p>Nenhum dado disponível para análise</p>"
        grafico_tempo = "<p>Nenhum dado disponível para análise</p>"
        grafico_radar = "<p>Nenhum dado disponível para análise</p>"
        grafico_norma = "<p>Nenhum dado disponível para análise</p>"
    
    return templates.TemplateResponse("analises/geral.html", {
        "request": request,
        "stats_data": stats_data,
        "stats_norma_data": stats_norma_data,
        "grafico_acerto": grafico_acerto,
        "grafico_tempo": grafico_tempo,
        "grafico_radar": grafico_radar,
        "grafico_norma": grafico_norma
    })


@router.get("/comparativo", response_class=HTMLResponse)
async def analise_comparativa(request: Request, db: Session = Depends(get_db)):
    """Análise comparativa detalhada entre modelos"""
    
    # Dados para análise comparativa
    dados_query = db.query(
        Pergunta.numero,
        Pergunta.norma_artigo,
        ModeloLLM.nome,
        Resposta.resposta_correta,
        Resposta.tempo_total,
        Resposta.clareza,
        Resposta.fundamentacao_tecnica,
        Resposta.concisao,
        Resposta.somatorio,
        Resposta.fonte_citada
    ).join(Pergunta).join(ModeloLLM).all()
    
    if not dados_query:
        return templates.TemplateResponse("analises/comparativo.html", {
            "request": request,
            "grafico_correlacao": "<p>Nenhum dado disponível</p>",
            "grafico_distribuicao": "<p>Nenhum dado disponível</p>"
        })
    
    # Converter para DataFrame para análise
    df = pd.DataFrame(dados_query, columns=[
        'pergunta_numero', 'norma_artigo', 'modelo', 'resposta_correta',
        'tempo_total', 'clareza', 'fundamentacao_tecnica', 'concisao', 'somatorio', 'fonte_citada'
    ])
    
    # Gráfico de correlação entre métricas
    if len(df) > 1:
        # Preparar dados numéricos
        df_numeric = df[['tempo_total', 'clareza', 'fundamentacao_tecnica', 'concisao', 'somatorio']].fillna(0)
        
        # Matriz de correlação
        corr_matrix = df_numeric.corr()
        
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            title="Matriz de Correlação entre Métricas",
            color_continuous_scale='RdBu'
        )
        fig_corr.update_layout(height=500)
        grafico_correlacao = plot(fig_corr, output_type='div', include_plotlyjs=False)
        
        # Distribuição de somatório por modelo
        fig_dist = px.box(
            df, 
            x='modelo', 
            y='somatorio',
            title='Distribuição de Somatório por Modelo',
            labels={'somatorio': 'Somatório', 'modelo': 'Modelo LLM'}
        )
        fig_dist.update_xaxes(tickangle=45)
        fig_dist.update_layout(height=500)
        grafico_distribuicao = plot(fig_dist, output_type='div', include_plotlyjs=False)
    else:
        grafico_correlacao = "<p>Dados insuficientes para análise de correlação</p>"
        grafico_distribuicao = "<p>Dados insuficientes para análise de distribuição</p>"
    
    return templates.TemplateResponse("analises/comparativo.html", {
        "request": request,
        "grafico_correlacao": grafico_correlacao,
        "grafico_distribuicao": grafico_distribuicao
    })


@router.get("/exportar/csv")
async def exportar_csv(db: Session = Depends(get_db)):
    """Exportar dados completos em CSV"""
    
    # Query completa com todos os dados
    dados = db.query(
        Pergunta.numero,
        Pergunta.texto,
        Pergunta.resposta_esperada,
        Pergunta.norma_artigo,
        ModeloLLM.nome,
        Resposta.tempo_primeira_resposta,
        Resposta.tempo_total,
        Resposta.resposta_correta,
        Resposta.clareza,
        Resposta.fundamentacao_tecnica,
        Resposta.concisao,
        Resposta.fonte_citada,
        Resposta.somatorio,
        Resposta.observacoes,
        Resposta.created_at
    ).join(Pergunta).join(ModeloLLM).order_by(Pergunta.numero, ModeloLLM.nome).all()
    
    # Converter para DataFrame
    df = pd.DataFrame(dados, columns=[
        'Pergunta_Numero', 'Pergunta_Texto', 'Resposta_Esperada', 'Norma_Artigo',
        'Modelo_LLM', 'Tempo_Primeira_Resposta', 'Tempo_Total', 'Resposta_Correta',
        'Clareza', 'Fundamentacao_Tecnica', 'Concisao', 'Fonte_Citada', 'Somatorio', 'Observacoes',
        'Data_Criacao'
    ])
    
    # Converter para CSV
    output = StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type='text/csv',
        headers={"Content-Disposition": "attachment; filename=experimentos_llm.csv"}
    )