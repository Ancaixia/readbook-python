"""SSR 页面路由（Jinja2）。

骨架阶段仅提供首页占位；业务阶段将补充：
- 书籍列表页
- 单句阅读页（原文 + 译注 + 音频/视频）
- 公众号分享卡页（OG + 二维码）
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

_tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=_tpl_dir)


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    # TODO(业务阶段): 从 DB 查询已上线书籍列表并渲染
    return templates.TemplateResponse(
        "index.html", {"request": request, "app_name": "ReadBook"}
    )
