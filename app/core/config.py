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

    # 微信小程序登录凭证（在微信公众平台「开发 → 开发管理 → 开发设置」获取）。
    # 用于后端用 wx.login 返回的 code 换取 openid。留空则微信登录接口返回错误。
    wechat_appid: str = ""
    wechat_secret: str = ""


settings = Settings()
