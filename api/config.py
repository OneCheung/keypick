"""
Application configuration settings
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")  # type: ignore[call-overload]
    DEBUG: bool = Field(default=True, env="DEBUG")  # type: ignore[call-overload]

    # Server configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")  # type: ignore[call-overload]
    PORT: int = Field(default=8000, env="PORT")  # type: ignore[call-overload]

    # CORS settings
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000", env="CORS_ORIGINS"
    )  # type: ignore[call-overload]

    # Database configuration (Supabase)
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")  # type: ignore[call-overload]
    SUPABASE_ANON_KEY: str = Field(default="", env="SUPABASE_ANON_KEY")  # type: ignore[call-overload]
    SUPABASE_SERVICE_KEY: str | None = Field(default=None, env="SUPABASE_SERVICE_KEY")  # type: ignore[call-overload]

    # Redis configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")  # type: ignore[call-overload]
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")  # type: ignore[call-overload]

    # KeyPick API Security
    KEYPICK_API_KEYS: str = Field(default="", env="KEYPICK_API_KEYS")  # type: ignore[call-overload]  # KeyPick 自己的 API Keys（逗号分隔）

    # Dify configuration (Optional - only if KeyPick needs to call Dify)
    DIFY_API_URL: str = Field(default="https://api.dify.ai/v1", env="DIFY_API_URL")  # type: ignore[call-overload]
    DIFY_CRAWLER_APP_KEY: str | None = Field(default=None, env="DIFY_CRAWLER_APP_KEY")  # type: ignore[call-overload]
    DIFY_REPORT_APP_KEY: str | None = Field(default=None, env="DIFY_REPORT_APP_KEY")  # type: ignore[call-overload]

    # Langfuse configuration (Optional - usually configured in Dify)
    LANGFUSE_PUBLIC_KEY: str | None = Field(default=None, env="LANGFUSE_PUBLIC_KEY")  # type: ignore[call-overload]
    LANGFUSE_SECRET_KEY: str | None = Field(default=None, env="LANGFUSE_SECRET_KEY")  # type: ignore[call-overload]
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com", env="LANGFUSE_HOST")  # type: ignore[call-overload]

    # MediaCrawler configuration
    MEDIACRAWLER_PATH: str = Field(default="./MediaCrawler", env="MEDIACRAWLER_PATH")  # type: ignore[call-overload]
    MEDIACRAWLER_TIMEOUT: int = Field(default=3600, env="MEDIACRAWLER_TIMEOUT")  # type: ignore[call-overload]

    # API Security
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")  # type: ignore[call-overload]
    API_KEYS: str = Field(default="", env="API_KEYS")  # type: ignore[call-overload]  # Comma-separated in env

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")  # type: ignore[call-overload]
    LOG_FILE: str | None = Field(default="logs/keypick.log", env="LOG_FILE")  # type: ignore[call-overload]

    # Task configuration
    MAX_CONCURRENT_TASKS: int = Field(default=5, env="MAX_CONCURRENT_TASKS")  # type: ignore[call-overload]
    TASK_RESULT_TTL: int = Field(default=86400, env="TASK_RESULT_TTL")  # type: ignore[call-overload]  # 24 hours

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")  # type: ignore[call-overload]
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")  # type: ignore[call-overload]
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # type: ignore[call-overload]  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_cors_origins(self) -> list[str]:
        """Get list of CORS origins from environment"""
        if self.CORS_ORIGINS:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    def get_keypick_api_keys(self) -> list[str]:
        """Get list of KeyPick API keys from environment"""
        if self.KEYPICK_API_KEYS:
            return [key.strip() for key in self.KEYPICK_API_KEYS.split(",") if key.strip()]
        return []

    def get_api_keys(self) -> list[str]:
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
