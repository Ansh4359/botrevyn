from typing import List, Optional, Dict
from langchain_chroma import Chroma
from app.vectordb.embeddings import get_embedding_model

class CodebaseRetriever:
    def __init__(self, collection_name: str, persist_directory: str):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embeddings = get_embedding_model()
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[str]:
        try:
            docs = self.vectorstore.similarity_search(query, k=k, filter=filter_dict)
            return [f"File: {doc.metadata.get('file_path')}\n{doc.page_content}" for doc in docs]
        except Exception:
            return []

    def search_similar_code(self, code_snippet: str, language: str, k: int = 3) -> List[str]:
        filter_dict = {"language": language}
        return self.search(code_snippet, k=k, filter_dict=filter_dict)

    def get_file_context(self, file_path: str, k: int = 3) -> List[str]:
        return self.search(file_path, k=k)
