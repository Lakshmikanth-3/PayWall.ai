from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./agent_guard.db"
    SECRET_KEY: str = "paywall-ai-secret-key-2026-razorpay"
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = ""
    # Meterless Nightshift (primary AI provider; OpenAI-compatible local runtime)
    METERLESS_BASE_URL: str = ""
    METERLESS_RUNTIME_TOKEN: str = ""
    METERLESS_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    # Zetaris (data layer): REST URL of the local install, org id and credentials
    ZETARIS_BASE_URL: str = ""
    ZETARIS_ORG_ID: str = "1"
    ZETARIS_USERNAME: str = ""
    ZETARIS_PASSWORD: str = ""
    ZETARIS_SCHEMA: str = "paywall"
    SAMPLE_MODE: bool = False
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    ALLOW_ORIGINS: str = "http://localhost:3000"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Decision thresholds
    ALLOW_THRESHOLD: int = 30
    REVIEW_THRESHOLD: int = 70

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
