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

    # Mixed into every passkey before hashing, so a leaked database dump alone
    # cannot be used to recover passkeys. Changing this invalidates all issued
    # passkeys — never rotate it mid-event.
    passkey_pepper: str = "change-me"


settings = Settings()
