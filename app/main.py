"""FastAPI 应用入口。

- 启动时根据模型建表（开发期；生产应使用 Alembic 迁移）。
- 挂载静态目录 /static。
- 注册 API 与页面路由。
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

from app.core.database import Base, engine
from app.routers import api, pages, admin

app = FastAPI(title="ReadBook API")

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
