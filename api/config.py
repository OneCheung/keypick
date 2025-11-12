"""
Application configuration settings
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Server configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # CORS settings
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        env="CORS_ORIGINS"
    )

    # Database configuration (Supabase)
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(default="", env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_KEY")

    # Redis configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")

    # KeyPick API Security
    KEYPICK_API_KEYS: str = Field(default="", env="KEYPICK_API_KEYS")  # KeyPick 自己的 API Keys（逗号分隔）

    # Dify configuration (Optional - only if KeyPick needs to call Dify)
    DIFY_API_URL: str = Field(default="https://api.dify.ai/v1", env="DIFY_API_URL")
    DIFY_CRAWLER_APP_KEY: Optional[str] = Field(default=None, env="DIFY_CRAWLER_APP_KEY")
    DIFY_REPORT_APP_KEY: Optional[str] = Field(default=None, env="DIFY_REPORT_APP_KEY")

    # Langfuse configuration (Optional - usually configured in Dify)
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None, env="LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None, env="LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com", env="LANGFUSE_HOST")

    # MediaCrawler configuration
    MEDIACRAWLER_PATH: str = Field(default="./MediaCrawler", env="MEDIACRAWLER_PATH")
    MEDIACRAWLER_TIMEOUT: int = Field(default=3600, env="MEDIACRAWLER_TIMEOUT")

    # API Security
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    API_KEYS: str = Field(default="", env="API_KEYS")  # Comma-separated in env

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default="logs/keypick.log", env="LOG_FILE")

    # Task configuration
    MAX_CONCURRENT_TASKS: int = Field(default=5, env="MAX_CONCURRENT_TASKS")
    TASK_RESULT_TTL: int = Field(default=86400, env="TASK_RESULT_TTL")  # 24 hours

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_cors_origins(self) -> List[str]:
        """Get list of CORS origins from environment"""
        if self.CORS_ORIGINS:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    def get_keypick_api_keys(self) -> List[str]:
        """Get list of KeyPick API keys from environment"""
        if self.KEYPICK_API_KEYS:
            return [key.strip() for key in self.KEYPICK_API_KEYS.split(",") if key.strip()]
        return []

    def get_api_keys(self) -> List[str]:
        """Get list of API keys (for backward compatibility)"""
        keypick_keys = self.get_keypick_api_keys()
        if keypick_keys:
            return keypick_keys
        # Fallback to old API_KEYS if exists
        if self.API_KEYS:
            if isinstance(self.API_KEYS, str):
                return [key.strip() for key in self.API_KEYS.split(",") if key.strip()]
            return self.API_KEYS
        return []

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


# Create global settings instance
settings = Settings()