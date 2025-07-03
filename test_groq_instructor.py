#!/usr/bin/env python3
"""
Script de teste para verificar compatibilidade entre Groq e Instructor
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_groq_instructor():
    """Testa se Instructor funciona com Groq"""
    
    try:
        import instructor
        from groq import Groq
        from pydantic import BaseModel, Field
        
        print("✅ Imports bem-sucedidos")
        
        # Modelo de teste simples
        class TestResponse(BaseModel):
            resposta: str = Field(..., description="Uma resposta simples")
            score: int = Field(..., ge=1, le=5, description="Score de 1 a 5")
        
        # Verificar se GROQ_API_KEY está configurada
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "sua_chave_groq_aqui":
            print("❌ GROQ_API_KEY não configurada ou usando valor de exemplo")
            print("Configure sua chave real da Groq no arquivo .env")
            return False
        
        # Tentar inicializar cliente
        groq_client = Groq(api_key=api_key)
        print("✅ Cliente Groq inicializado")
        
        # Tentar usar Instructor
        client = instructor.from_groq(groq_client)
        print("✅ Instructor configurado com Groq")
        
        # Fazer uma chamada de teste simples
        print("🧪 Testando chamada de API...")
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            response_model=TestResponse,
            messages=[{
                "role": "user",
                "content": "Avalie a seguinte frase: 'Este é um teste'. Dê uma resposta e um score de 1 a 5."
            }],
            max_tokens=100,
            temperature=0.1
        )
        
        print(f"✅ Resposta recebida:")
        print(f"   - Resposta: {response.resposta}")
        print(f"   - Score: {response.score}")
        print(f"   - Tipo: {type(response)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testando compatibilidade Groq + Instructor...")
    print("=" * 50)
    
    success = test_groq_instructor()
    
    print("=" * 50)
    if success:
        print("🎉 Teste concluído com sucesso!")
        print("A integração Groq + Instructor está funcionando.")
    else:
        print("💥 Teste falhou!")
        print("Verifique as dependências e configurações.")