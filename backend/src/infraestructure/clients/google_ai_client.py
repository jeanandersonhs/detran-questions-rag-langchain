"""Shared accessors for Google AI embeddings and chat models."""
import os
from pathlib import Path
from typing import ClassVar, Protocol

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


class EmbeddingsProtocol(Protocol):
    """Protocol for embeddings interface following Interface Segregation principle."""
    def embed_query(self, text: str) -> list[float]: ...


class LLMProtocol(Protocol):
    """Protocol for LLM interface following Interface Segregation principle."""
    async def ainvoke(self, messages) -> str: ...


def _load_project_env() -> None:
    """Load the nearest project .env without depending on the process cwd."""
    current_file = Path(__file__).resolve()
    candidate_paths = (
        current_file.parents[2] / ".env",  # backend/src/.env
        current_file.parents[3] / ".env",  # backend/.env
        current_file.parents[4] / ".env",  # repo/.env
    )

    for env_path in candidate_paths:
        if env_path.exists():
            load_dotenv(env_path)
            return

    load_dotenv()


_load_project_env()


class GoogleAIClient:
    """
    Shared factory for Google Generative AI services.

    This class centralizes creation of external clients and reuses a single
    embeddings/LLM instance per process. Consumers should call the class methods
    directly instead of instantiating this type.
    """

    _embeddings: ClassVar[EmbeddingsProtocol | None] = None
    _llm: ClassVar[LLMProtocol | None] = None

    @classmethod
    def _get_api_key(cls) -> str:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        return api_key

    @classmethod
    def get_embeddings(cls) -> EmbeddingsProtocol:
        """Return a shared embeddings client."""
        if cls._embeddings is None:
            cls._embeddings = GoogleGenerativeAIEmbeddings(
                model="gemini-embedding-2-preview",
                google_api_key=cls._get_api_key(),
            )
        return cls._embeddings

    @classmethod
    def get_llm(cls) -> LLMProtocol:
        """Return a shared chat model client."""
        if cls._llm is None:
            cls._llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0.1,
                convert_system_message_to_human=True,
                google_api_key=cls._get_api_key(),
            )
        return cls._llm
