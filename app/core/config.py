"""应用配置（pydantic-settings 读取 .env）。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "ReadBook"
    database_url: str = "sqlite:///./readbook.db"
    debug: bool = True


settings = Settings()
