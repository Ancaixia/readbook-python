"""FastAPI 应用入口。

- 启动时根据模型建表（开发期；生产应使用 Alembic 迁移）。
- 挂载静态目录 /static。
- 注册 API 与页面路由。
"""
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, RedirectResponse

from app.core.database import Base, engine
from app.core.session import SESSION_COOKIE, verify_session_token
from app.routers import api, pages, admin, auth

app = FastAPI(title="ReadBook API")


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    """仅保护 /admin 后台：未登录访问 /admin 一律重定向到登录页。

    其它路径（首页、阅读页、公开 API、/auth 自身）均放行，
    保证阅读体验与 Flutter 客户端不受影响。
    """
    token = request.cookies.get(SESSION_COOKIE)
    user_id = verify_session_token(token)
    request.state.user_id = user_id  # 供模板渲染「登录/退出」状态
    if request.url.path.startswith("/admin") and user_id is None:
        return RedirectResponse("/auth/login", status_code=303)
    return await call_next(request)


# 开发期自动建表；生产环境请用 Alembic 迁移
Base.metadata.create_all(bind=engine)


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
