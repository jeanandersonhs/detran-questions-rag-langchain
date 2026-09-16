from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class QuestionRequest(BaseModel):
    """Data Transfer Object for incoming question requests."""
    query: str = Field(..., max_length=1000, description="The question to be answered")

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Query cannot be empty or blank")
        return stripped

    class Config:
        json_schema_extra = {
            "example": {
                "query": "O que é habilitação provisória?"
            }
        }


class DocumentSource(BaseModel):
    """Data Transfer Object for document sources in the response."""
    content: str = Field(..., description="The relevant document content")
    source: Optional[str] = Field(None, description="The source of the document (e.g., file name)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Machine learning is a subset of artificial intelligence...",
                "source": "document_1.pdf"
            }
        }


class AnswerResponse(BaseModel):
    """Data Transfer Object for question-answer responses."""
    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="The generated answer from the RAG pipeline")
    sources: List[DocumentSource] = Field(default_factory=list, description="List of source documents used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is machine learning?",
                "answer": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience...",
                "sources": [
                    {
                        "content": "Machine learning is a subset of artificial intelligence...",
                        "source": "document_1.pdf"
                    }
                ]
            }
        }
