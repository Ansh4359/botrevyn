import os
from functools import lru_cache
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # GitHub App & OAuth Configuration
    github_app_id: str = Field("", env="GITHUB_APP_ID")
    github_private_key: str = Field("", env="GITHUB_PRIVATE_KEY")
    github_client_id: str = Field("", env="GITHUB_CLIENT_ID")
    github_client_secret: str = Field("", env="GITHUB_CLIENT_SECRET")
    github_webhook_secret: str = Field("", env="GITHUB_WEBHOOK_SECRET")
    jwt_secret: str = Field("super-secret-default-key-change-in-prod", env="JWT_SECRET")
    
    # Fallback / Old Auth (Optional now)
    github_token: str = Field("", env="GITHUB_TOKEN")
    
    google_api_key: str = Field("", env="GOOGLE_API_KEY")
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    
    llm_provider: str = Field("google", env="LLM_PROVIDER")
    llm_model: str = Field("gemini-3.1-flash-lite", env="LLM_MODEL")
    
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    chromadb_path: str = Field("./data/chromadb", env="CHROMADB_PATH")
    
    log_level: str = Field("INFO", env="LOG_LEVEL")
    auto_fix_enabled: bool = Field(True, env="AUTO_FIX_ENABLED")
    auto_fix_require_approval: bool = Field(False, env="AUTO_FIX_REQUIRE_APPROVAL")
    dashboard_enabled: bool = Field(True, env="DASHBOARD_ENABLED")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    def get_llm(self, **kwargs) -> Any:
        if self.llm_provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=self.llm_model, google_api_key=self.google_api_key, **kwargs)
        elif self.llm_provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=self.llm_model, api_key=self.openai_api_key, **kwargs)
        elif self.llm_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=self.llm_model, api_key=self.anthropic_api_key, **kwargs)
        elif self.llm_provider == "ollama":
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model=self.llm_model, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
            
    def get_embeddings(self) -> Any:
        if self.llm_provider == "google":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=self.google_api_key)
        elif self.llm_provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(api_key=self.openai_api_key)
        else:
            raise ValueError(f"Unsupported embeddings provider for: {self.llm_provider}")

@lru_cache()
def get_settings() -> Settings:
    return Settings()
