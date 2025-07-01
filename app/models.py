from sqlalchemy import Boolean, Column, Integer, String, Text, DECIMAL, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Pergunta(Base):
    """Tabela das perguntas do experimento"""
    __tablename__ = "perguntas"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False, index=True)
    texto = Column(Text, nullable=False)
    resposta_esperada = Column(Text, nullable=False)
    
    # Separação da norma técnica e item específico
    norma_tecnica = Column(String(50), nullable=False, index=True)  # Ex: "NT-09"
    item = Column(String(50), nullable=False, index=True)  # Ex: "6.7.3"
    norma_artigo = Column(String(100), nullable=False)  # Campo combinado para compatibilidade: "NT-09 - 6.7.3"
    
    # Relacionamento com respostas
    respostas = relationship("Resposta", back_populates="pergunta")


class ModeloLLM(Base):
    """Tabela dos modelos de LLM testados"""
    __tablename__ = "modelos_llm"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False, index=True)
    descricao = Column(Text)
    
    # Relacionamento com respostas
    respostas = relationship("Resposta", back_populates="modelo")


class Resposta(Base):
    """Tabela principal com resultados dos experimentos"""
    __tablename__ = "respostas"

    id = Column(Integer, primary_key=True, index=True)
    pergunta_id = Column(Integer, ForeignKey("perguntas.id"), nullable=False)
    modelo_id = Column(Integer, ForeignKey("modelos_llm.id"), nullable=False)
    
    # Métricas de tempo
    tempo_primeira_resposta = Column(DECIMAL(5, 2))  # segundos
    tempo_total = Column(DECIMAL(5, 2))  # segundos
    
    # Métricas de qualidade
    resposta_correta = Column(Boolean, nullable=False, default=False)
    clareza = Column(Integer)  # 1-5
    precisao = Column(Integer)  # 1-5
    concisao = Column(Integer)  # 1-5
    fonte_citada = Column(Boolean, nullable=False, default=False)
    
    # Somatório automático
    somatorio = Column(Integer)  # Soma das métricas
    
    # Observações qualitativas
    observacoes = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    pergunta = relationship("Pergunta", back_populates="respostas")
    modelo = relationship("ModeloLLM", back_populates="respostas")
    
    def calcular_somatorio(self):
        """Calcula o somatório das métricas de qualidade"""
        metricas = [self.clareza, self.precisao, self.concisao]
        # Adiciona pontos por resposta correta e fonte citada
        pontos_extras = 0
        if self.resposta_correta:
            pontos_extras += 1
        if self.fonte_citada:
            pontos_extras += 1
            
        # Soma apenas métricas válidas (não None)
        soma_metricas = sum(m for m in metricas if m is not None)
        self.somatorio = soma_metricas + pontos_extras
        return self.somatorio