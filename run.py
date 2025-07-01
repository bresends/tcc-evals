#!/usr/bin/env python3
"""
Script principal para executar o sistema TCC Questions
"""
import uvicorn
import sys
import os

def main():
    """Executar a aplicação"""
    
    # Verificar se o .env existe
    if not os.path.exists('.env'):
        print("❌ Arquivo .env não encontrado!")
        print("Crie um arquivo .env com a configuração DATABASE_URL")
        sys.exit(1)
    
    print("🚀 Iniciando TCC Questions - Sistema de Catalogação LLM")
    print("📊 Acesse: http://localhost:8000")
    print("📋 Dashboard: http://localhost:8000/dashboard")
    print("🔬 Experimentos: http://localhost:8000/experimentos")
    print("📈 Análises: http://localhost:8000/analises")
    print()
    print("Pressione Ctrl+C para parar o servidor")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Servidor parado. Até logo!")

if __name__ == "__main__":
    main()