import os
import shutil
import tempfile
from typing import List
from git import Repo
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from app.models.pr_context import PRContext, FileContent
from app.vectordb.embeddings import get_embedding_model
from app.tools.code_analyzer import detect_language

class CodebaseIndexer:
    def __init__(self, collection_name: str, persist_directory: str):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embeddings = get_embedding_model()
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def index_repository(self, repo_full_name: str, token: str) -> int:
        temp_dir = tempfile.mkdtemp()
        try:
            repo_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
            Repo.clone_from(repo_url, temp_dir, depth=1)
            
            docs_to_index = []
            for root, _, files in os.walk(temp_dir):
                if ".git" in root:
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    lang = detect_language(rel_path)
                    
                    if lang == "unknown" and not rel_path.endswith((".md", ".txt", ".yml", ".yaml", ".json")):
                        continue
                        
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        docs = self._chunk_code(content, lang, rel_path)
                        for doc in docs:
                            doc.metadata["repo_name"] = repo_full_name
                        docs_to_index.extend(docs)
                    except Exception:
                        pass
            
            if docs_to_index:
                self.vectorstore.add_documents(docs_to_index)
                
            return len(docs_to_index)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def index_files(self, files: List[FileContent], repo_name: str) -> int:
        docs_to_index = []
        for file in files:
            lang = detect_language(file.filename)
            docs = self._chunk_code(file.content, lang, file.filename)
            for doc in docs:
                doc.metadata["repo_name"] = repo_name
            docs_to_index.extend(docs)
            
        if docs_to_index:
            self.vectorstore.add_documents(docs_to_index)
            
        return len(docs_to_index)

    def update_from_pr(self, pr_context: PRContext) -> int:
        return self.index_files(pr_context.files, pr_context.repo_full_name)

    def _chunk_code(self, content: str, language: str, file_path: str) -> List[Document]:
        separators = self._get_language_separators(language)
        splitter = RecursiveCharacterTextSplitter(
            separators=separators,
            chunk_size=1500,
            chunk_overlap=200,
            keep_separator=True
        )
        
        chunks = splitter.split_text(content)
        docs = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "file_path": file_path,
                "language": language,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            docs.append(Document(page_content=chunk, metadata=metadata))
            
        return docs

    def _get_language_separators(self, language: str) -> List[str]:
        if language in ["python"]:
            return ["\nclass ", "\ndef ", "\n\n", "\n", " "]
        elif language in ["javascript", "go", "java", "cpp", "c", "csharp", "rust"]:
            return ["\nclass ", "\nfunc ", "\nfunction ", "\n\n", "\n", " "]
        else:
            return ["\n\n", "\n", " "]
