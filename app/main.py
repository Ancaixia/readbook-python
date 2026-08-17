"""FastAPI 应用入口。

- 启动时根据模型建表（开发期；生产应使用 Alembic 迁移）。
- 挂载静态目录 /static。
- 注册 API 与页面路由。
"""
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, RedirectResponse
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
from app.core.session import SESSION_COOKIE, verify_session_token
from app.models.user import User
from app.routers import api, pages, admin, auth

app = FastAPI(title="ReadBook API")


def _migrate_user_role() -> None:
    """开发期轻量迁移：给 users 表补 role 列；若没有任何 admin 则提升最早用户。

    生产环境应改用 Alembic，这里仅保证本地开发库平滑升级。
    """
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("users")]
    if "role" not in cols:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'normal'")
            )
    with SessionLocal() as db:
        any_admin = db.scalar(select(User).where(User.role == "admin"))
        if any_admin is None:
            first = db.scalar(select(User).order_by(User.id).limit(1))
            if first is not None:
                first.role = "admin"
                db.commit()


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    """保护 /admin 后台：未登录跳登录页；已登录但非 admin 跳首页。

    其它路径（首页、阅读页、公开 API、/auth 自身）均放行，
    保证阅读体验与 Flutter 客户端不受影响。
    """
    token = request.cookies.get(SESSION_COOKIE)
    user_id = verify_session_token(token)
    request.state.user_id = user_id
    request.state.user_role = None
    path = request.url.path
    if path.startswith("/admin"):
        if user_id is None:
            return RedirectResponse("/auth/login", status_code=303)
        db: Session = SessionLocal()
        try:
            u = db.get(User, user_id)
            role = u.role if u else None
        finally:
            db.close()
        request.state.user_role = role
        if role != "admin":
            return RedirectResponse("/", status_code=303)
    return await call_next(request)


# 开发期自动建表；生产环境请用 Alembic 迁移
Base.metadata.create_all(bind=engine)
_migrate_user_role()


class NoCacheStaticFiles(StaticFiles):
    """开发期静态文件：禁用浏览器缓存，改完刷新即可见效，避免拿到旧 CSS/JS。"""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", NoCacheStaticFiles(directory=_static_dir), name="static")

app.include_router(api.router)
app.include_router(pages.router)
app.include_router(admin.router)
app.include_router(auth.router)
