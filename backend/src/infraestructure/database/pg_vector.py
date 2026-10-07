import os
from typing import ClassVar

from langchain_postgres import PGEngine, PGVectorStore
from sqlalchemy import create_engine, inspect

from infraestructure.clients.google_ai_client import GoogleAIClient


class PgVector_CONFIG:
    """Configuration for PostgreSQL vector store.

    Resources are created on first use (not at import time) so the app can be
    imported without a running database.
    """

    DEFAULT_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/rag_db"
    my_schema = "rag"
    table_name = "documents_rag"

    _vector_store: ClassVar[PGVectorStore | None] = None

    @classmethod
    def _get_url(cls) -> str:
        return os.getenv("DATABASE_URL_POSTGRES", cls.DEFAULT_URL)

    @classmethod
    def _ensure_table(cls, pg_engine: PGEngine) -> None:
        """Create the vector table on first run, sized to the embedding model."""
        sync_engine = create_engine(cls._get_url())
        try:
            if inspect(sync_engine).has_table(cls.table_name, schema=cls.my_schema):
                return
        finally:
            sync_engine.dispose()

        vector_size = len(GoogleAIClient.get_embeddings().embed_query("dimension probe"))
        pg_engine.init_vectorstore_table(
            table_name=cls.table_name,
            vector_size=vector_size,
            schema_name=cls.my_schema,
        )

    @classmethod
    def get_vector_store(cls) -> PGVectorStore:
        """Return the shared PGVectorStore instance, creating it if needed."""
        if cls._vector_store is None:
            pg_engine = PGEngine.from_connection_string(url=cls._get_url())
            cls._ensure_table(pg_engine)
            cls._vector_store = PGVectorStore.create_sync(
                engine=pg_engine,
                table_name=cls.table_name,
                embedding_service=GoogleAIClient.get_embeddings(),
                schema_name=cls.my_schema,
            )
        return cls._vector_store
