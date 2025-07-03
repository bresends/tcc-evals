from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class PerguntaBase(BaseModel):
    numero: int = Field(..., ge=1, le=92, description="Número da pergunta (1-92)")
    texto: str = Field(..., min_length=10, description="Texto da pergunta")
    resposta_esperada: str = Field(..., min_length=1, description="Resposta esperada")
    norma_artigo: str = Field(..., min_length=1, description="Norma e artigo de referência")


class PerguntaCreate(PerguntaBase):
    pass


class Pergunta(PerguntaBase):
    id: int
    
    class Config:
        from_attributes = True


class ModeloLLMBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100, description="Nome do modelo LLM")
    descricao: Optional[str] = None


class ModeloLLMCreate(ModeloLLMBase):
    pass


class ModeloLLM(ModeloLLMBase):
    id: int
    
    class Config:
        from_attributes = True


class RespostaBase(BaseModel):
    pergunta_id: int = Field(..., ge=1, description="ID da pergunta")
    modelo_id: int = Field(..., ge=1, description="ID do modelo LLM")
    configuracao: str = Field(..., min_length=1, max_length=50, description="Configuração experimental")
    resposta_dada: Optional[str] = Field(None, description="Resposta gerada pelo modelo")
    tempo_primeira_resposta: Optional[Decimal] = Field(None, ge=0, description="Tempo primeira resposta (s)")
    tempo_total: Optional[Decimal] = Field(None, ge=0, description="Tempo total (s)")
    resposta_correta: bool = Field(False, description="Resposta está correta?")
    clareza: Optional[int] = Field(None, ge=1, le=5, description="Clareza (1-5)")
    fundamentacao_tecnica: Optional[int] = Field(None, ge=1, le=5, description="Fundamentação técnica (1-5)")
    concisao: Optional[int] = Field(None, ge=1, le=5, description="Concisão (1-5)")
    fonte_citada: bool = Field(False, description="Fonte foi citada?")
    observacoes: Optional[str] = None


class RespostaCreate(RespostaBase):
    pass


class Resposta(RespostaBase):
    id: int
    somatorio: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    pergunta: Pergunta
    modelo: ModeloLLM
    
    class Config:
        from_attributes = True


class RespostaUpdate(BaseModel):
    configuracao: Optional[str] = Field(None, min_length=1, max_length=50)
    resposta_dada: Optional[str] = None
    tempo_primeira_resposta: Optional[Decimal] = None
    tempo_total: Optional[Decimal] = None
    resposta_correta: Optional[bool] = None
    clareza: Optional[int] = Field(None, ge=1, le=5)
    fundamentacao_tecnica: Optional[int] = Field(None, ge=1, le=5)
    concisao: Optional[int] = Field(None, ge=1, le=5)
    fonte_citada: Optional[bool] = None
    observacoes: Optional[str] = None


# Schemas para análises e relatórios
class EstatisticaModelo(BaseModel):
    modelo_nome: str
    total_respostas: int
    respostas_corretas: int
    percentual_acerto: float
    tempo_medio_primeira: Optional[float] = None
    tempo_medio_total: Optional[float] = None
    clareza_media: Optional[float] = None
    fundamentacao_media: Optional[float] = None
    concisao_media: Optional[float] = None
    somatorio_medio: Optional[float] = None
    fontes_citadas: int
    percentual_fontes: float


class ComparacaoModelos(BaseModel):
    estatisticas: list[EstatisticaModelo]
    melhor_modelo_acerto: str
    melhor_modelo_tempo: str
    melhor_modelo_qualidade: str