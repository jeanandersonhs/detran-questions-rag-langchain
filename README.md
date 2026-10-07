# Gerar simulados do detran
Objetivo do projeto é fazer um webscraping em simulados do detran. 

Montar um banco vetorial por meio do código de trânsito brasileira. E assim com base nas questões do webscraping, gerar questões com mesmo padrão de texto por dificuldade( fácil, médio, dificil) para auxiliar aos estudos para prova teórica do detran.



# Tecnologias 
- Next.js 16+
- Typescript
- Python 3.12
- Langchain
- Docker
- Pg vector

# Rodando localmente (Docker)

Pré-requisito: apenas Docker + Docker Compose (não é preciso instalar Postgres nem Python).

```bash
cp backend/.env.example backend/.env   # preencha GOOGLE_API_KEY
docker compose up -d --build           # sobe Postgres (pgvector) + backend
```

- API: http://localhost:8000 (docs em http://localhost:8000/docs)
- Postgres: `localhost:5432`, banco `rag_db`, usuário/senha `postgres`/`postgres`
- O schema `rag` e a extensão `vector` são criados por `infra/postgres/init.sql`; a tabela `rag.documents_rag` é criada no primeiro uso.

Indexar documentos (coloque PDFs/TXTs em `backend/data/documents/`):

```bash
docker compose run --rm backend python src/application/use_cases/ingest.py
```

Comandos úteis:

```bash
docker compose logs -f backend                       # logs da API
docker compose exec postgres psql -U postgres rag_db # console SQL
docker compose down                                  # para tudo (mantém os dados)
docker compose down -v                               # para tudo e apaga o banco
```
