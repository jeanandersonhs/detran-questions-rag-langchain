import unittest

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from application.dtos.query_dto import QuestionRequest
from application.use_cases.query import QueryUseCase


class QueryUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_retrieves_once_and_passes_context_to_model(self):
        queries = []
        prompts = []
        documents = [Document(page_content="Trecho de estudo.", metadata={"source": "ctb.pdf"})]

        async def retrieve(query):
            queries.append(query)
            return documents

        async def generate(prompt):
            prompts.append(prompt.to_string())
            return AIMessage(content="Resposta fundamentada [1].")

        use_case = QueryUseCase(retriever=RunnableLambda(retrieve), llm=RunnableLambda(generate))
        response = await use_case.execute(QuestionRequest(query="  Minha pergunta?  "))
        self.assertEqual(queries, ["Minha pergunta?"])
        self.assertEqual(len(prompts), 1)
        self.assertIn("[1] Fonte: ctb.pdf\nTrecho de estudo.", prompts[0])
        self.assertIn("Minha pergunta?", prompts[0])
        self.assertEqual(response.question, "  Minha pergunta?  ")
        self.assertEqual(response.answer, "Resposta fundamentada [1].")
        self.assertEqual(response.sources[0].source, "ctb.pdf")
        self.assertEqual(response.sources[0].content, documents[0].page_content)

    async def test_empty_retrieval_skips_model(self):
        def unexpected_model_call(_):
            self.fail("Model must not run without documents")

        use_case = QueryUseCase(
            retriever=RunnableLambda(lambda _: []), llm=RunnableLambda(unexpected_model_call)
        )
        response = await use_case.execute(QuestionRequest(query="Pergunta?"))
        self.assertEqual(response.answer, QueryUseCase.NO_CONTEXT_ANSWER)
        self.assertEqual(response.sources, [])

    async def test_whitespace_is_rejected_before_retrieval(self):
        def unexpected_call(_):
            self.fail("Dependencies must not run for blank queries")

        use_case = QueryUseCase(
            retriever=RunnableLambda(unexpected_call), llm=RunnableLambda(unexpected_call)
        )
        with self.assertRaisesRegex(ValueError, "Query cannot be empty"):
            await use_case.execute(QuestionRequest(query="   "))

    async def test_dependency_failure_preserves_cause(self):
        async def retrieve(_):
            raise ConnectionError("Database unavailable")

        use_case = QueryUseCase(
            retriever=RunnableLambda(retrieve), llm=RunnableLambda(lambda _: "unused")
        )
        with self.assertRaises(RuntimeError) as raised:
            await use_case.execute(QuestionRequest(query="Pergunta?"))
        self.assertIsInstance(raised.exception.__cause__, ConnectionError)


if __name__ == "__main__":
    unittest.main()
