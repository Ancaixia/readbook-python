"""用户模型：后台登录 + 预留第三方登录扩展。

- username / password_hash / salt：用户名密码登录（本期实现）。
- phone：预留，后续电话/短信验证码登录。
- wechat_openid：预留，后续微信 OAuth 登录绑定。
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    func,
)

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    phone = Column(String(32), unique=True, index=True, nullable=True)  # 预留电话登录
    wechat_openid = Column(String(128), unique=True, index=True, nullable=True)  # 预留微信登录
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
