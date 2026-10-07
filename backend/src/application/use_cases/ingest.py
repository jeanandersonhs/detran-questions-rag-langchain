import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from infraestructure.database.pg_vector import PgVector_CONFIG

class IngestUseCase:
    def __init__(self, data_path: str | None = None):
        """Ingest documents into the vector database.

        Loads PDF/text files from ``data_path`` (or ``DATA_PATH``), splits them
        into chunks and stores them in the same vector store used by queries.

        Args:
            data_path: Directory containing the source documents. """

        self.data_path = data_path or os.getenv("DATA_PATH", "data/documents")


    def load_documents(self):
        documents = []

        for file in os.listdir(self.data_path):
            path = os.path.join(self.data_path, file) # Process the file and extract text

            if file.endswith(".pdf"):
                # Use PyPDF2 or similar to extract text from PDF
                loader = PyPDFLoader(path)
            else:
                # Use a simple text loader for other formats
                loader = TextLoader(path)

            documents.extend(loader.load())
        return documents



    def split_documents(self, documents):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100)
        return text_splitter.split_documents(documents)



    def ingest(self) -> int:
        documents = self.load_documents()
        chunks = self.split_documents(documents)

        PgVector_CONFIG.get_vector_store().add_documents(chunks)
        return len(chunks)


if __name__ == "__main__":
    total = IngestUseCase().ingest()
    print(f"{total} chunks indexed.")
