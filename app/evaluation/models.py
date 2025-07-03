"""Modelos Pydantic para avaliação estruturada de respostas"""

from pydantic import BaseModel, Field
from typing import List


class AvaliacaoContextual(BaseModel):
    """Modelo para avaliação contextual de respostas considerando norma técnica específica"""
    
    # Avaliação de correção técnica
    resposta_correta: bool = Field(
        ..., 
        description="A resposta está tecnicamente correta conforme a norma técnica citada?"
    )
    
    # Avaliação de conformidade com norma
    norma_mencionada: bool = Field(
        ..., 
        description="A resposta menciona explicitamente a norma técnica correta (ex: NT-09)?"
    )
    
    item_mencionado: bool = Field(
        ..., 
        description="A resposta menciona o item/artigo específico da norma (ex: 6.7.3)?"
    )
    
    fonte_citada: bool = Field(
        ..., 
        description="A resposta cita ESPECIFICAMENTE a norma técnica correta E o item/artigo correto (ex: cita NT-09 E 4.9)? Fontes incorretas ou genéricas = False"
    )
    
    # Métricas de qualidade (1-5)
    clareza: int = Field(
        ..., 
        ge=1, 
        le=5, 
        description="Clareza da explicação (1=muito confusa, 5=muito clara)"
    )
    
    fundamentacao_tecnica: int = Field(
        ..., 
        ge=1, 
        le=5, 
        description="Fundamentação técnica CORRETA com terminologia adequada. Se resposta_correta=False, máximo=2. (1=fundamentação incorreta/ausente, 5=fundamentação correta e completa)"
    )
    
    concisao: int = Field(
        ..., 
        ge=1, 
        le=5, 
        description="Concisão da resposta (1=muito verbosa, 5=concisa e direta)"
    )
    
    # Análise específica da norma
    conformidade_norma: int = Field(
        ..., 
        ge=1, 
        le=5, 
        description="Nível de conformidade com a norma técnica específica (1=não conforme, 5=totalmente conforme)"
    )
    
    completude_tecnica: int = Field(
        ..., 
        ge=1, 
        le=5, 
        description="Completude da informação técnica (1=incompleta, 5=completa)"
    )
    
    # Justificativas detalhadas
    observacoes: str = Field(
        ..., 
        description="Análise detalhada considerando norma, item específico e resposta esperada oficial"
    )
    
    pontos_corretos: List[str] = Field(
        ..., 
        description="Lista de aspectos específicos que estão corretos na resposta"
    )
    
    pontos_incorretos: List[str] = Field(
        default_factory=list,
        description="Lista de aspectos incorretos, ausentes ou imprecisos na resposta"
    )
    
    def validar_consistencia_logica(self):
        """Valida consistência lógica entre métricas"""
        # Se resposta incorreta, fundamentação técnica não pode ser alta
        if not self.resposta_correta and self.fundamentacao_tecnica > 2:
            raise ValueError(f"Inconsistência: resposta_correta=False mas fundamentacao_tecnica={self.fundamentacao_tecnica} > 2")
        
        # Se não menciona norma/item, conformidade deve ser baixa
        if not self.norma_mencionada and self.conformidade_norma > 3:
            raise ValueError(f"Inconsistência: norma não mencionada mas conformidade_norma={self.conformidade_norma} > 3")
    
    # Métricas calculadas
    def calcular_score_total(self) -> float:
        """Calcula score total baseado nas métricas (0-10)"""
        # Score baseado nas métricas 1-5
        score_qualidade = (self.clareza + self.fundamentacao_tecnica + self.concisao + 
                          self.conformidade_norma + self.completude_tecnica) / 5
        
        # Bonificações por correção e citações
        bonus_correcao = 1.0 if self.resposta_correta else 0.0
        bonus_fonte = 0.5 if self.fonte_citada else 0.0
        bonus_norma = 0.3 if self.norma_mencionada else 0.0
        bonus_item = 0.2 if self.item_mencionado else 0.0
        
        # Score final de 0-10
        score_final = (score_qualidade * 0.7) + (bonus_correcao * 2.0) + bonus_fonte + bonus_norma + bonus_item
        return min(10.0, max(0.0, score_final))


class ResultadoAvaliacao(BaseModel):
    """Resultado completo da avaliação para persistir no banco"""
    
    avaliacao: AvaliacaoContextual
    score_final: float
    pergunta_numero: int
    modelo_nome: str
    configuracao: str
    timestamp: str
    
    # Contexto da pergunta
    norma_tecnica: str
    item_norma: str
    flag_resposta_duvidosa: bool