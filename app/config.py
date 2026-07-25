from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables / .env.

    gemini_api_key has no default — fail fast and clearly at startup if it's
    missing, rather than let a request fail deep inside the AI layer.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"


settings = Settings()
