from functools import lru_cache
from app.config import get_settings

@lru_cache()
def get_embedding_model():
    settings = get_settings()
    llm_provider = getattr(settings, "llm_provider", "google").lower()
    
    if llm_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small")
    else:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001")
