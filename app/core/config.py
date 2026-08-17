"""应用配置（pydantic-settings 读取 .env）。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "ReadBook"
    database_url: str = "sqlite:///./readbook.db"
    debug: bool = True

    # Session cookie 签名密钥。生产环境务必改为随机长字符串（可用
    # `python -c "import secrets; print(secrets.token_hex(32))"` 生成）。
    secret_key: str = "dev-secret-change-me-please"


settings = Settings()
