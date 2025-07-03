"""Avaliador contextual de respostas usando Instructor"""

import os
import instructor
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, List
import logging
import time

from .models import AvaliacaoContextual, ResultadoAvaliacao
from ..models import Pergunta, Resposta, ModeloLLM
from sqlalchemy.orm import Session

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)


class ContextualEvaluator:
    """Avaliador que considera contexto completo da pergunta (norma, item, flags)"""
    
    def __init__(self, dry_run: bool = False, overwrite: bool = False):
        self.dry_run = dry_run
        self.overwrite = overwrite
        self.client = None
        
        if not dry_run:
            # Inicializar cliente Groq
            api_key = os.getenv("GROQ_API_KEY")
            
            if not api_key:
                raise ValueError("GROQ_API_KEY não configurada")
            
            # Inicializar Groq client
            groq_client = Groq(api_key=api_key)
            
            # Patch com Instructor
            self.client = instructor.from_groq(groq_client)
            
            logger.info(f"ContextualEvaluator inicializado com Groq API")
    
    def _criar_prompt_contextual(self, pergunta: Pergunta, resposta_dada: str) -> str:
        """Cria prompt especializado considerando contexto da pergunta"""
        
        # Aviso especial para respostas duvidosas
        aviso_duvidosa = ""
        if pergunta.flag_resposta_duvidosa:
            aviso_duvidosa = """
⚠️ ATENÇÃO: Esta pergunta está marcada como 'resposta_duvidosa', 
indicando que a resposta esperada oficial pode conter erros ou imprecisões.
Avalie com critério crítico e considere se a resposta do LLM pode estar mais correta.
"""
        
        prompt = f"""Você é um especialista técnico em normas do CBMGO (Corpo de Bombeiros Militar de Goiás).

CONTEXTO DA PERGUNTA:
- Norma Técnica: {pergunta.norma_tecnica}
- Item/Artigo: {pergunta.item}
- Referência Completa: {pergunta.norma_artigo}
- Pergunta: {pergunta.texto}

RESPOSTA ESPERADA (oficial): 
{pergunta.resposta_esperada}

RESPOSTA DO LLM PARA AVALIAR:
{resposta_dada}

{aviso_duvidosa}

⚠️ INSTRUÇÃO CRÍTICA PARA AVALIAÇÃO:
COMPARE DIRETAMENTE a resposta final do LLM com a RESPOSTA ESPERADA oficial: "{pergunta.resposta_esperada}"
- Se as respostas finais são DIFERENTES (valores numéricos, unidades, conceitos), marque resposta_correta = False
- Se as respostas finais são IGUAIS ou EQUIVALENTES, marque resposta_correta = True
- NÃO se deixe influenciar por boa fundamentação técnica se a resposta final está ERRADA

CRITÉRIOS DE AVALIAÇÃO:

1. **Correção Técnica**: 
   - ⚠️ PRIMEIRO: Compare a resposta FINAL do LLM com "{pergunta.resposta_esperada}"
   - A resposta está correta conforme {pergunta.norma_tecnica} - {pergunta.item}?
   - Se valores numéricos: são exatamente iguais ou equivalentes?

2. **Conformidade Normativa**: 
   - Menciona explicitamente a norma correta ({pergunta.norma_tecnica})?
   - Cita o item/artigo específico ({pergunta.item})?
   - **FONTE CITADA**: Cita ESPECIFICAMENTE {pergunta.norma_tecnica} E {pergunta.item}? (citações genéricas, incorretas ou outras normas = NÃO)

3. **Qualidade da Resposta**:
   - **Clareza**: Explicação compreensível e bem estruturada? (independente da correção)
   - **Fundamentação Técnica**: Uso CORRETO de terminologia técnica e conceitos normativos válidos
     * Se resposta_correta = False → fundamentacao_tecnica máximo = 2 (fundamentação incorreta)
     * Se resposta_correta = True → avaliar qualidade da fundamentação (1-5)
   - **Concisão**: Resposta direta sem ser superficial?

4. **Conformidade com Norma**: Alinhamento com os requisitos específicos da {pergunta.norma_tecnica}

5. **Completude Técnica**: Aborda todos os aspectos relevantes da questão?

INSTRUÇÕES ESPECÍFICAS PARA FUNDAMENTAÇÃO TÉCNICA:
- **Se resposta_correta = False:** fundamentacao_tecnica = 1 ou 2 (máximo)
  * 1 = Fundamentação completamente incorreta ou ausente
  * 2 = Alguma terminologia técnica mas aplicada incorretamente
- **Se resposta_correta = True:** avaliar qualidade da fundamentação (1-5)
  * 1 = Resposta certa mas sem fundamentação técnica
  * 2 = Fundamentação básica com poucos termos técnicos
  * 3 = Fundamentação adequada com terminologia correta
  * 4 = Boa fundamentação com conceitos técnicos bem aplicados
  * 5 = Excelente fundamentação com domínio técnico completo

INSTRUÇÕES ESPECÍFICAS PARA FONTE CITADA:
- ✅ fonte_citada = True APENAS se mencionar EXPLICITAMENTE "{pergunta.norma_tecnica}" E "{pergunta.item}"
- ❌ fonte_citada = False se citar:
  * Outras normas (NT-01, NT-17, etc. que não seja {pergunta.norma_tecnica})
  * Outros itens (que não seja {pergunta.item})
  * Citações genéricas ("conforme norma", "segundo CBMGO", etc.)
  * Leis, decretos ou outras fontes que não sejam especificamente {pergunta.norma_tecnica} - {pergunta.item}
  * Nenhuma fonte

INSTRUÇÕES GERAIS:
- **LÓGICA ESTRUTURADA**: resposta_correta determina o limite máximo da fundamentacao_tecnica
- Compare cuidadosamente com a resposta esperada oficial
- Considere o contexto técnico específico da norma
- Se a resposta for parcialmente correta, identifique os pontos específicos
- Seja rigoroso mas justo na avaliação
- Para fonte_citada, seja MUITO RIGOROSO: apenas fontes corretas e específicas
- **CONSISTÊNCIA**: Uma resposta incorreta NÃO pode ter fundamentação técnica alta (máximo 2)
- Forneça justificativas detalhadas para suas avaliações"""

        return prompt
    
    def avaliar_resposta(
        self, 
        pergunta: Pergunta, 
        resposta: Resposta
    ) -> Optional[AvaliacaoContextual]:
        """Avalia uma resposta específica usando contexto completo"""
        
        if not resposta.resposta_dada:
            logger.warning(f"Resposta {resposta.id} não possui texto para avaliar")
            return None
        
        # Rate limiting para Groq (20 RPM = 1 call per 3 seconds) - SEMPRE aplicado
        time.sleep(3.0)
        
        if self.dry_run:
            # Simulação para testes (com delay real para timing correto)
            return AvaliacaoContextual(
                resposta_correta=True,
                norma_mencionada=True,
                item_mencionado=False,
                fonte_citada=True,
                clareza=4,
                fundamentacao_tecnica=4,
                concisao=3,
                conformidade_norma=4,
                completude_tecnica=4,
                observacoes=f"[SIMULAÇÃO] Avaliação simulada para pergunta #{pergunta.numero} - {pergunta.norma_artigo}",
                pontos_corretos=["Resposta tecnicamente correta", "Boa explicação"],
                pontos_incorretos=["Não menciona item específico da norma"]
            )
        
        try:
            prompt = self._criar_prompt_contextual(pergunta, resposta.resposta_dada)
            
            # Usar modelo Groq llama3-70b-8192
            model_name = "llama3-70b-8192"
            
            # Fazer chamada estruturada usando Instructor
            avaliacao = self.client.chat.completions.create(
                model=model_name,
                response_model=AvaliacaoContextual,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }],
                max_tokens=2000,
                temperature=0.1
            )
            
            # Validar consistência lógica
            try:
                avaliacao.validar_consistencia_logica()
                logger.info(f"Avaliação concluída para resposta {resposta.id}")
                return avaliacao
            except ValueError as ve:
                logger.warning(f"Inconsistência na avaliação {resposta.id}: {ve}")
                logger.warning("Retornando avaliação mesmo com inconsistência para análise")
                return avaliacao
            
        except Exception as e:
            logger.error(f"Erro ao avaliar resposta {resposta.id}: {e}")
            return None
    
    def avaliar_respostas_lote(
        self, 
        respostas: List[Resposta], 
        db: Session
    ) -> List[ResultadoAvaliacao]:
        """Avalia múltiplas respostas em lote"""
        
        resultados = []
        
        for resposta in respostas:
            try:
                avaliacao = self.avaliar_resposta(resposta.pergunta, resposta)
                
                if avaliacao:
                    resultado = ResultadoAvaliacao(
                        avaliacao=avaliacao,
                        score_final=avaliacao.calcular_score_total(),
                        pergunta_numero=resposta.pergunta.numero,
                        modelo_nome=resposta.modelo.nome,
                        configuracao=resposta.configuracao,
                        timestamp=datetime.now().isoformat(),
                        norma_tecnica=resposta.pergunta.norma_tecnica,
                        item_norma=resposta.pergunta.item,
                        flag_resposta_duvidosa=resposta.pergunta.flag_resposta_duvidosa
                    )
                    
                    resultados.append(resultado)
                    
                    # Atualizar campos da resposta no banco
                    if not self.dry_run:
                        self._atualizar_resposta_banco(resposta, avaliacao, db)
                        
            except Exception as e:
                logger.error(f"Erro ao processar resposta {resposta.id}: {e}")
                continue
        
        return resultados
    
    def _atualizar_resposta_banco(
        self, 
        resposta: Resposta, 
        avaliacao: AvaliacaoContextual, 
        db: Session
    ):
        """Atualiza campos da resposta no banco com resultado da avaliação"""
        
        # Log dos valores antes da atualização
        logger.info(f"Atualizando resposta {resposta.id} com avaliação:")
        logger.info(f"  - Resposta correta: {avaliacao.resposta_correta}")
        logger.info(f"  - Fonte citada: {avaliacao.fonte_citada}")
        logger.info(f"  - Clareza: {avaliacao.clareza}")
        logger.info(f"  - Fundamentação: {avaliacao.fundamentacao_tecnica}")
        logger.info(f"  - Concisão: {avaliacao.concisao}")
        
        # Atualizar campos da resposta
        resposta.resposta_correta = avaliacao.resposta_correta
        resposta.fonte_citada = avaliacao.fonte_citada
        resposta.clareza = avaliacao.clareza
        resposta.fundamentacao_tecnica = avaliacao.fundamentacao_tecnica
        resposta.concisao = avaliacao.concisao
        resposta.observacoes = avaliacao.observacoes
        
        # Recalcular somatório
        resposta.calcular_somatorio()
        
        # Forçar flush antes do commit para detectar erros
        try:
            db.flush()
            db.commit()
            
            # Verificar se foi salvo corretamente
            db.refresh(resposta)
            logger.info(f"Resposta {resposta.id} atualizada com sucesso:")
            logger.info(f"  - Clareza final: {resposta.clareza}")
            logger.info(f"  - Fundamentação final: {resposta.fundamentacao_tecnica}")
            logger.info(f"  - Concisão final: {resposta.concisao}")
            logger.info(f"  - Somatório: {resposta.somatorio}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar avaliação para resposta {resposta.id}: {e}")
            raise
    
    def avaliar_por_filtros(
        self,
        db: Session,
        modelo_nome: Optional[str] = None,
        configuracao: Optional[str] = None,
        norma_tecnica: Optional[str] = None,
        apenas_interessantes: bool = False,
        apenas_duvidosas: bool = False,
        limit: Optional[int] = None
    ) -> List[ResultadoAvaliacao]:
        """Avalia respostas baseado em filtros específicos"""
        
        # Construir query com filtros
        query = db.query(Resposta).join(Pergunta).join(ModeloLLM)
        
        if modelo_nome:
            query = query.filter(ModeloLLM.nome == modelo_nome)
        
        if configuracao:
            query = query.filter(Resposta.configuracao == configuracao)
            
        if norma_tecnica:
            query = query.filter(Pergunta.norma_tecnica == norma_tecnica)
            
        if apenas_interessantes:
            query = query.filter(Pergunta.flag_interessante == True)
            
        if apenas_duvidosas:
            query = query.filter(Pergunta.flag_resposta_duvidosa == True)
        
        # Filtrar apenas respostas que têm texto
        query = query.filter(Resposta.resposta_dada.isnot(None))
        query = query.filter(Resposta.resposta_dada != "")
        
        if limit:
            query = query.limit(limit)
            
        respostas = query.all()
        
        logger.info(f"Encontradas {len(respostas)} respostas para avaliar")
        
        return self.avaliar_respostas_lote(respostas, db)
    
    def get_responses_to_evaluate(
        self,
        db: Session,
        modelo_nome: str,
        configuracao: str,
        max_responses: Optional[int] = None,
        norma_tecnica: Optional[str] = None,
        apenas_interessantes: bool = False,
        apenas_duvidosas: bool = False
    ) -> List[Resposta]:
        """Obter lista de respostas para avaliar, evitando duplicatas (seguindo padrão do ExperimentRunner)"""
        
        # Query base: respostas com modelo e configuração específicos
        query = db.query(Resposta).join(Pergunta).join(ModeloLLM).filter(
            ModeloLLM.nome == modelo_nome,
            Resposta.configuracao == configuracao
        )
        
        # Aplicar filtros opcionais
        if norma_tecnica:
            query = query.filter(Pergunta.norma_tecnica == norma_tecnica)
            
        if apenas_interessantes:
            query = query.filter(Pergunta.flag_interessante == True)
            
        if apenas_duvidosas:
            query = query.filter(Pergunta.flag_resposta_duvidosa == True)
        
        # Filtrar apenas respostas que têm texto para avaliar
        query = query.filter(Resposta.resposta_dada.isnot(None))
        query = query.filter(Resposta.resposta_dada != "")
        
        # Excluir respostas já avaliadas automaticamente (a menos que overwrite=True)
        if not self.overwrite:
            # Considera "já avaliada" se clareza, fundamentacao_tecnica e concisao não são None
            query = query.filter(
                (Resposta.clareza.is_(None)) |
                (Resposta.fundamentacao_tecnica.is_(None)) |
                (Resposta.concisao.is_(None))
            )
        
        # Ordenar por número da pergunta para consistência
        query = query.order_by(Pergunta.numero)
        
        # Limitar se especificado
        if max_responses:
            query = query.limit(max_responses)
            
        respostas = query.all()
        
        logger.info(f"Encontradas {len(respostas)} respostas para avaliar (modelo: {modelo_nome}, config: {configuracao})")
        
        return respostas
    
    def run_batch_evaluation(
        self,
        db: Session,
        modelo_nome: str,
        configuracao: str,
        max_responses: Optional[int] = None,
        norma_tecnica: Optional[str] = None,
        apenas_interessantes: bool = False,
        apenas_duvidosas: bool = False
    ) -> List[ResultadoAvaliacao]:
        """Executar avaliação em lote para modelo/configuração específicos (seguindo padrão do ExperimentRunner)"""
        
        # Obter respostas para avaliar
        respostas = self.get_responses_to_evaluate(
            db=db,
            modelo_nome=modelo_nome,
            configuracao=configuracao,
            max_responses=max_responses,
            norma_tecnica=norma_tecnica,
            apenas_interessantes=apenas_interessantes,
            apenas_duvidosas=apenas_duvidosas
        )
        
        if not respostas:
            logger.info("Nenhuma resposta encontrada para avaliar com os filtros especificados")
            return []
        
        logger.info(f"Iniciando avaliação em lote de {len(respostas)} respostas")
        
        # Executar avaliação
        return self.avaliar_respostas_lote(respostas, db)