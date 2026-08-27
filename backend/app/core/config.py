from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central app config, loaded from environment variables / .env.
    See .env.example for the full list of variables.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql+asyncpg://walkrun:walkrun_dev_pw@db:5432/walkrun"
    jwt_secret: str = "change-me"

    line_login_channel_id: str = ""
    line_login_channel_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""


settings = Settings()
