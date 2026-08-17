"""密码哈希与 Session Cookie 签名（零额外依赖，仅用标准库）。

- 密码：pbkdf2_hmac('sha256', password, salt, 100000)，salt 随机 16 字节。
- Session：cookie = "<user_id>|<expires_ts>.<hmac_sha256(secret_key, payload)>"，
  服务端用 secret_key 验签 + 校验过期，无需查库即可信任 user_id。
"""
import hashlib
import hmac
import os
import time

from app.core.config import settings

SESSION_COOKIE = "rb_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 天
PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> tuple[str, str]:
    """返回 (salt_hex, password_hash_hex)。"""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, stored_hash_hex: str) -> bool:
    """恒定时间比对，防止时序攻击。"""
    try:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            PBKDF2_ITERATIONS,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), stored_hash_hex)


def _sign(payload: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_token(user_id: int) -> str:
    expires = int(time.time()) + SESSION_MAX_AGE
    payload = f"{user_id}|{expires}"
    return f"{payload}.{_sign(payload)}"


def verify_session_token(token: str | None) -> int | None:
    """校验签名与过期，返回 user_id；失败返回 None。"""
    if not token or token.count(".") != 1:
        return None
    try:
        payload, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(_sign(payload), signature):
            return None
        user_id_str, expires_str = payload.split("|")
        if int(expires_str) < int(time.time()):
            return None
        return int(user_id_str)
    except (ValueError, TypeError):
        return None
