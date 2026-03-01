from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PDF Agent Backend"
    app_env: str = "development"
    app_port: int = 8000
    database_url: str = "sqlite:///./local.db"
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    command_rate_limit_per_minute: int = 60
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60
    v2_execution_mode: str = "off"
    v2_canary_percent: int = 0
    queue_backend: str = "rq"
    queue_redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "pdf-agent"
    queue_job_timeout_seconds: int = 1800

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
