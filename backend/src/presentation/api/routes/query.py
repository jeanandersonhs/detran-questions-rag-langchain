from fastapi import APIRouter, HTTPException, status
from typing import Callable

from application.dtos.query_dto import QuestionRequest, AnswerResponse
from application.use_cases.query import QueryUseCase


def create_query_router(query_use_case: QueryUseCase) -> APIRouter:
    """
    Factory function to create a query router with injected dependencies.
    
    Args:
        query_use_case: The QueryUseCase instance to handle RAG operations
        
    Returns:
        APIRouter configured with query endpoints
    """
    router = APIRouter(prefix="/query", 
                       tags=["Query"],
                       responses={400: {"description": "Bad Request"}, 
                                  500: {"description": "Internal Server Error"}}
                        )
    
    
    
    @router.post(
        "/",
        response_model=AnswerResponse,
        status_code=status.HTTP_200_OK,
        summary="Answer a question using RAG",
        description="Submits a question and returns an answer from the RAG pipeline with source documents"
    )
    async def post_query(request: QuestionRequest) -> AnswerResponse:
        """
        Handle POST requests to answer questions using the RAG pipeline.

        Args:
            request: QuestionRequest containing the query text (validated by Pydantic)

        Returns:
            AnswerResponse with the generated answer and source documents

        Raises:
            HTTPException: 500 if there's an error in the RAG pipeline
        """
        try:
            return await query_use_case.execute(request)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing query: {str(e)}"
            ) from e
        
    
    return router
