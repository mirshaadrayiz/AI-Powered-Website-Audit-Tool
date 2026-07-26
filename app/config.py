from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    App configuration, loaded from environment variables / .env.
    """

    # env_ignore_empty: a key present but blank in .env (GEMINI_MODEL=) falls
    # back to the default below, instead of resolving to "" and sending an
    # empty model name to Gemini.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"


settings = Settings()
