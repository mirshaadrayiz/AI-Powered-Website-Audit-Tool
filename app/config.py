from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment variables / .env.

    gemini_api_key has no default — fail fast and clearly at startup if it's
    missing, rather than let a request fail deep inside the AI layer.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str
    # "latest" alias, not a pinned version — avoids the model-retirement
    # whiplash of hardcoding a specific snapshot. Override via GEMINI_MODEL
    # in .env to pin a specific version instead.
    gemini_model: str = "gemini-flash-latest"


settings = Settings()
