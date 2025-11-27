import asyncio
import os
import sys
from sqlalchemy import text # type: ignore
from dotenv import load_dotenv

# Adiciona o diretório app ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.database_service import engine, AsyncSessionLocal

load_dotenv()

async def migrate_database():
    """Migra o banco de dados adicionando novos campos à tabela users"""
    
    print(" [MIGRATION] Iniciando migração do banco de dados...")
    
    async with engine.begin() as conn:
        try:
            # Verifica se a coluna 'nome' já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='nome'
            """)
            result = await conn.execute(check_query)
            nome_exists = result.fetchone() is not None
            
            if nome_exists:
                print(" [MIGRATION] Campos já existem. Nenhuma migração necessária.")
                return
            
            print(" [MIGRATION] Adicionando novos campos à tabela users...")
            
            # Adiciona as novas colunas
            migration_sql = text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS nome VARCHAR(100),
                ADD COLUMN IF NOT EXISTS sobrenome VARCHAR(100),
                ADD COLUMN IF NOT EXISTS email VARCHAR(255),
                ADD COLUMN IF NOT EXISTS senha_hash VARCHAR(255),
                ADD COLUMN IF NOT EXISTS is_active VARCHAR(10) DEFAULT 'ACTIVE',
                ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'USER',
                ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE,
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
            """)
            
            await conn.execute(migration_sql)
            
            # Cria índice único no email se não existir
            try:
                index_sql = text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);
                """)
                await conn.execute(index_sql)
            except Exception as e:
                print(f" [MIGRATION] Aviso ao criar índice: {e}")
            
            # Atualiza registros existentes com valores padrão se necessário
            update_sql = text("""
                UPDATE users 
                SET 
                    nome = COALESCE(nome, 'Usuário'),
                    sobrenome = COALESCE(sobrenome, 'Anônimo'),
                    email = COALESCE(email, 'user_' || id::text || '@temp.local'),
                    senha_hash = COALESCE(senha_hash, '$2b$12$placeholder_hash_para_usuarios_antigos'),
                    is_active = COALESCE(is_active, 'ACTIVE'),
                    role = COALESCE(role, 'USER'),
                    updated_at = COALESCE(updated_at, created_at)
                WHERE nome IS NULL OR sobrenome IS NULL OR email IS NULL;
            """)
            
            await conn.execute(update_sql)
            
            # Torna email NOT NULL após preencher valores
            try:
                alter_not_null = text("""
                    ALTER TABLE users 
                    ALTER COLUMN nome SET NOT NULL,
                    ALTER COLUMN sobrenome SET NOT NULL,
                    ALTER COLUMN email SET NOT NULL,
                    ALTER COLUMN senha_hash SET NOT NULL;
                """)
                await conn.execute(alter_not_null)
            except Exception as e:
                print(f" [MIGRATION] Aviso ao definir NOT NULL: {e}")
                print(" [MIGRATION] Alguns campos podem ter valores NULL. Execute novamente após corrigir.")
            
            print(" [MIGRATION] Migração concluída com sucesso!")
            print(" [MIGRATION] Nota: Usuários antigos foram atualizados com valores padrão.")
            print(" [MIGRATION] Recomenda-se que usuários antigos façam registro novamente ou atualizem seus dados.")
            
        except Exception as e:
            print(f" [MIGRATION ERROR] Erro durante a migração: {e}")
            raise

async def main():
    """Função principal"""
    try:
        await migrate_database()
    except Exception as e:
        print(f" [MIGRATION ERROR] Falha na migração: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

