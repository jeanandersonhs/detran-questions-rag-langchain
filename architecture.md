# Architecture — Detran Questions RAG

## 1. Visão Geral

Sistema de Retrieval-Augmented Generation (RAG) para auxiliar estudantes na prova teórica do DETRAN. O sistema:

1. Realiza **web scraping** de simulados do DETRAN para capturar o padrão de questões (estrutura textual, estilo, nomenclatura).
2. Monta uma **base vetorial** a partir do Código de Trânsito Brasileiro (CTB) e legislação correlata.
3. Gera **novas questões** no mesmo padrão do DETRAN, classificadas por **dificuldade** (fácil, médio, difícil) e categoria, usando a base vetorial como fonte de conhecimento (RAG).

### Stack

| Camada | Tecnologia |
| --- | --- |
| Frontend | Next.js 16+, TypeScript |
| Backend | Python 3.12, FastAPI, LangChain / LangGraph |
| LLM | Google Gemini (`gemini-2.0-flash`) |
| Embeddings | Google Gemini (`gemini-embedding-2-preview`) |
| Vector Store | PostgreSQL + pgvector (extensão) |
| Infra | Docker, docker-compose |

---

## 2. Diagrama de Contexto

```mermaid
flowchart LR
    subgraph Users
        U[Estudante / Usuário]
    end

    subgraph System["Detran Questions RAG"]
        F[Frontend<br/>Next.js]
        API[Backend API<br/>FastAPI]
        VDB[(PostgreSQL<br/>+ pgvector)]
        SCR[Web Scraper<br/>simulados DETRAN]
    end

    subgraph External
        GEM[Google Gemini API<br/>LLM + Embeddings]
        WEB[Sites de simulados<br/>DETRAN]
        CTB[Legislação de trânsito<br/>CTB / Resoluções]
    end

    U -->|estuda / responde simulados| F
    F -->|REST /api| API
    API --> VDB
    API --> GEM
    SCR -->|coleta questões| WEB
    SCR -->|padrões extraídos| VDB
    CTB -->|documentos PDF/texto| API
```

---

## 3. Diagrama de Componentes

```mermaid
flowchart TB
    subgraph Frontend["Frontend (Next.js)"]
        UI[Páginas / Componentes UI]
        API_CLIENT[Cliente API<br/>NEXT_PUBLIC_API_URL]
    end

    subgraph Backend["Backend (FastAPI)"]
        subgraph Presentation
            ROUTES[Routes<br/>/query · /documents]
            DTOs[DTOs<br/>Pydantic]
        end

        subgraph Application
            UCQ[QueryUseCase<br/>pipeline RAG]
            UCI[IngestUseCase<br/>carga de documentos]
        end

        subgraph Domain
            ENT[Entidades<br/>em definição]
        end

        subgraph Infrastructure
            GAI[GoogleAIClient<br/>LLM + Embeddings<br/>singleton]
            PGV[PgVector_CONFIG<br/>PGVectorStore<br/>schema: rag]
        end
    end

    subgraph Data
        PG[(PostgreSQL + pgvector<br/>tabela: documents_rag)]
    end

    subgraph External
        GEM[Google Gemini API]
    end

    UI --> API_CLIENT
    API_CLIENT --> ROUTES
    ROUTES --> DTOs
    ROUTES --> UCQ
    ROUTES --> UCI
    UCQ --> PGV
    UCQ --> GAI
    UCI --> PGV
    UCI --> GAI
    PGV --> PG
    GAI --> GEM
```

---

## 4. Arquitetura do Backend (Clean Architecture)

O backend segue os princípios de Clean Architecture / Hexagonal, com dependências apontando das camadas externas para as internas.

```
backend/src/
├── main.py                        # Bootstrap da aplicação FastAPI (CORS, rotas, /api)
├── presentation/
│   └── api/routes/
│       ├── routes.py              # Fábrica central de rotas (injeção de use cases)
│       ├── query.py               # POST /query — endpoint RAG
│       └── documents.py           # Rotas de documentos (pendente)
├── application/
│   ├── use_cases/
│   │   ├── query.py               # QueryUseCase — orquestra o pipeline RAG
│   │   └── ingest.py              # IngestUseCase — load, split, embed, indexar
│   └── dtos/
│       ├── query_dto.py           # QuestionRequest, DocumentSource, AnswerResponse
│       └── document_dto.py        # (pendente)
├── domain/
│   └── entities/                  # Entidades de domínio (pendente)
└── infraestructure/               # (sic — mantido o nome atual do projeto)
    ├── clients/
    │   └── google_ai_client.py    # GoogleAIClient — fábrica singleton Gemini
    └── database/
        └── pg_vector.py           # PgVector_CONFIG — conexão/vector store
```

### Responsabilidades por camada

| Camada | Responsabilidade | Exemplos |
| --- | --- | --- |
| `presentation` | Transporte HTTP, validação de entrada, mapeamento DTO ↔ use case | `routes/query.py` |
| `application` | Casos de uso e DTOs; orquestra domínio e infraestrutura | `QueryUseCase`, `IngestUseCase` |
| `domain` | Regras de negócio puras, entidades (em evolução) | `entities/` |
| `infraestructure` | Adaptadores externos: clientes de IA, banco, loaders | `GoogleAIClient`, `PgVector_CONFIG` |

### Decisões relevantes

- **Injeção via fábrica**: `create_api_router()` instancia os use cases e injeta nas rotas (`routes.py`), facilitando testes e desacoplamento.
- **Singleton de clientes IA**: `GoogleAIClient` usa `ClassVar` + `classmethod` para reutilizar uma única instância de LLM e embeddings por processo (`google_ai_client.py`), evitando recriação custosa.
- **Protocols para isolamento**: `EmbeddingsProtocol` e `LLMProtocol` (tipagem estrutural) desacoplam a aplicação das implementações concretas de LangChain.
- **Vector store centralizado**: `PgVector_CONFIG` inicializa o `PGVectorStore` no schema `rag`, tabela `documents_rag` (`pg_vector.py`).

---

## 5. Modelos de IA

| Papel | Modelo | Parâmetros |
| --- | --- | --- |
| Geração (LLM) | `gemini-2.0-flash` | `temperature=0.1` |
| Embeddings | `gemini-embedding-2-preview` | — |

Chave via variável de ambiente `GOOGLE_API_KEY` (carregada do `.env` do projeto).

---

## 6. Armazenamento Vetorial

- **Banco**: PostgreSQL 16 com extensão `pgvector` (imagem `pgvector/pgvector:pg16`).
- **Estrutura**: schema `rag`, tabela `documents_rag`, collection `documents`.
- **Conexão**: `DATABASE_URL_POSTGRES` (fallback local em dev).
- **Chunking**: `RecursiveCharacterTextSplitter` com `chunk_size=1000`, `chunk_overlap=100`.
- **Busca**: similaridade (`search_type="similarity"`) com `k=3` documentos.

---

## 7. Fluxos Principais

### 7.1 Ingestão e Indexação (base de conhecimento)

```mermaid
sequenceDiagram
    participant OP as Operador
    participant ING as IngestUseCase
    participant SPLIT as TextSplitter
    participant GAI as GoogleAIClient
    participant PGV as PGVector

    OP->>ING: ingest()
    ING->>ING: load_documents()<br/>PDF (PyPDFLoader) / texto (TextLoader)
    ING->>SPLIT: split_documents()
    SPLIT-->>ING: chunks (1000/100)
    ING->>GAI: get_embeddings()
    GAI-->>ING: embeddings
    ING->>PGV: add_documents(chunks)
    PGV-->>ING: vetores indexados
```

### 7.2 Consulta RAG (pergunta → resposta com fontes)

```mermaid
sequenceDiagram
    participant C as Cliente
    participant API as POST /query
    participant UC as QueryUseCase
    participant VS as Vector Store
    participant GAI as GoogleAIClient

    C->>API: { query }
    API->>UC: execute(QuestionRequest)
    UC->>VS: similarity_search(k=3)
    VS-->>UC: documentos relevantes
    UC->>GAI: LLM (contexto + pergunta)
    GAI-->>UC: resposta
    UC-->>API: AnswerResponse{question, answer, sources}
    API-->>C: 200 OK
```

### 7.3 Web Scraping e Geração de Questões (planejado)

Pipeline ainda não implementado no código; é o objetivo final do projeto:

1. **Scraper** coleta simulados do DETRAN e extrai padrões (estrutura, estilo, alternativas).
2. Padrões são persistidos na base vetorial com metadados de **dificuldade** e **categoria**.
3. **Gerador** usa RAG (CTB + padrões) para criar novas questões no mesmo estilo.
4. Questões geradas alimentam simulados exibidos no frontend.

---

## 8. API

### Endpoints atuais

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/api/query/` | Responde pergunta via RAG; retorna `AnswerResponse` com `sources` |

### DTOs principais (`application/dtos/query_dto.py`)

- **`QuestionRequest`** — `query: str` (1–1000 caracteres).
- **`AnswerResponse`** — `question`, `answer`, `sources: List[DocumentSource]`.
- **`DocumentSource`** — `content`, `source` (metadado do documento).

### Próximos endpoints (planejados)

- `POST /api/documents/` — upload de documentos para ingestão (rota `documents.py` pendente).
- `GET /api/simulados/` — listar/gerar simulados.
- `POST /api/questions/generate` — geração de questões por dificuldade/categoria.

---

## 9. Infraestrutura (docker-compose)

```mermaid
flowchart LR
    subgraph docker-compose
        FE[frontend<br/>Next.js :3000]
        BE[backend<br/>FastAPI :8000]
        DB[(postgres<br/>pgvector :5432)]
    end

    FE -->|depends_on| BE
    BE -->|depends_on| DB
    BE -->|DATABASE_URL<br/>OPENAI_API_KEY| DB
```

- **postgres**: imagem `pgvector/pgvector:pg16`, banco `rag_db`, volume persistente `postgres_data`.
- **backend**: build `./backend`, porta 8000, volume `uploads` + código montado.
- **frontend**: build `./frontend`, porta 3000, `NEXT_PUBLIC_API_URL=http://backend:8000`.

---

## 10. Variáveis de Ambiente

| Variável | Uso | Onde |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Autenticação Gemini (LLM + embeddings) | backend (`.env`) |
| `DATABASE_URL_POSTGRES` | Conexão do vector store | backend |
| `CORS_ORIGINS` | Origens permitidas (default `http://localhost:3000`) | backend |
| `NEXT_PUBLIC_API_URL` | URL da API no frontend | frontend |
| `OPENAI_API_KEY` | Definida no compose (reservada p/ modelos OpenAI) | compose |

---

## 11. Dívidas Técnicas e Evolução

- **`IngestUseCase`**: `DATA_PATH` é variável local (`ingest.py`); documentos carregados mas ingestão não exposta via API.
- **`QueryUseCase`**: `qa_chain` comentado — fluxo de prompt/contexto do LLM ainda precisa ser finalizado (`query.py`).
- **`documents.py`**: rota vazia; registrar no `routes.py`.
- **`domain/`**: camada de entidades ainda vazia — definir modelo de domínio (Questão, Simulado, Categoria, Dificuldade).
- **Padronização**: decidir entre `langchain_postgres.PGVectorStore` (usado em `query.py`/`pg_vector.py`) e `langchain_community.vectorstores.PGVector` (usado em `ingest.py`).
- **Web scraper e gerador de questões**: componentes planejados, ainda não iniciados.
