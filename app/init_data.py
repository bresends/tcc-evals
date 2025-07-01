"""
Script para popular o banco com dados iniciais
"""
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, ModeloLLM

# Lista dos 10 modelos LLM mencionados no TCC
MODELOS_INICIAIS = [
    {"nome": "gemini-2.5-pro", "descricao": "Google Gemini 2.5 Pro - Modelo avançado do Google"},
    {"nome": "gemini-2.5-flash", "descricao": "Google Gemini 2.5 Flash - Versão otimizada para velocidade"},
    {"nome": "gpt-4.0", "descricao": "OpenAI GPT-4.0 - Modelo de linguagem avançado da OpenAI"},
    {"nome": "gpt-4.1", "descricao": "OpenAI GPT-4.1 - Versão atualizada do GPT-4"},
    {"nome": "o3", "descricao": "OpenAI O3 - Modelo experimental da OpenAI"},
    {"nome": "claude-opus-4", "descricao": "Anthropic Claude Opus 4 - Modelo de alta capacidade"},
    {"nome": "deepseek-r1", "descricao": "DeepSeek R1 - Modelo de raciocínio avançado"},
    {"nome": "deepseek-v3", "descricao": "DeepSeek V3 - Versão 3 do modelo DeepSeek"},
    {"nome": "grok-3", "descricao": "xAI Grok 3 - Modelo de linguagem da xAI"},
    {"nome": "qwen-3-235B", "descricao": "Alibaba Qwen 3 235B - Modelo com 235 bilhões de parâmetros"}
]


def init_modelos_llm():
    """Inicializar modelos LLM no banco de dados"""
    db = SessionLocal()
    
    try:
        # Verificar se já existem modelos
        existing_count = db.query(ModeloLLM).count()
        if existing_count > 0:
            print(f"Já existem {existing_count} modelos no banco. Pulando inicialização.")
            return
        
        # Criar modelos
        modelos_criados = 0
        for modelo_data in MODELOS_INICIAIS:
            # Verificar se o modelo já existe
            existing = db.query(ModeloLLM).filter(ModeloLLM.nome == modelo_data["nome"]).first()
            if not existing:
                modelo = ModeloLLM(**modelo_data)
                db.add(modelo)
                modelos_criados += 1
        
        db.commit()
        print(f"✅ {modelos_criados} modelos LLM criados com sucesso!")
        
        # Listar modelos criados
        todos_modelos = db.query(ModeloLLM).all()
        print("\n📋 Modelos disponíveis:")
        for modelo in todos_modelos:
            print(f"  - {modelo.nome}: {modelo.descricao}")
            
    except Exception as e:
        print(f"❌ Erro ao criar modelos: {e}")
        db.rollback()
    finally:
        db.close()


def criar_pergunta_exemplo():
    """Criar uma pergunta de exemplo para testar o sistema"""
    db = SessionLocal()
    
    try:
        from .models import Pergunta
        
        # Verificar se já existe
        existing = db.query(Pergunta).filter(Pergunta.numero == 1).first()
        if existing:
            print("Pergunta exemplo já existe.")
            return
        
        pergunta_exemplo = Pergunta(
            numero=1,
            texto="Considere a necessidade de compartimentação entre duas edificações com fachadas paralelas coincidentes. Levando em consideração que as fachadas são iguais e têm as seguintes dimensões: altura = 5m e largura = 10m. Considerando também que cada uma das fachadas paralelas possuem 8 janelas de 1m x 3m. Responda qual é a distância que as edificações devem ter uma da outra para que estejam devidamente compartimentadas horizontalmente, conforme NT-09",
            resposta_esperada="7 metros",
            norma_artigo="NT09 - 6.7.3"
        )
        
        db.add(pergunta_exemplo)
        db.commit()
        print("✅ Pergunta exemplo criada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar pergunta exemplo: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Inicializando dados do sistema...")
    
    # Garantir que as tabelas existam
    Base.metadata.create_all(bind=engine)
    
    # Inicializar dados
    init_modelos_llm()
    criar_pergunta_exemplo()
    
    print("\n✨ Inicialização concluída!")