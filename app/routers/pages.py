"""SSR 页面路由（Jinja2）。

- GET  /                         书籍列表首页
- GET  /book/{name}              单书阅读页（目录 + 逐句富文本阅读）
- GET  /share/{name}/{id}        公众号分享卡页（OG + 二维码 + 复制链接）

页面与 /api/book/* 共用同一套业务服务；Flutter 客户端则直接消费 API。
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import book_service

router = APIRouter(tags=["pages"])

_tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=_tpl_dir)


def _abs_url(request: Request, path: str) -> str:
    return str(request.base_url).rstrip("/") + path


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    books = book_service.list_books(db)
    return templates.TemplateResponse(
        request, "index.html", {"request": request, "books": books}
    )


@router.get("/book/{book_name}", response_class=HTMLResponse)
def reader(request: Request, book_name: str, db: Session = Depends(get_db)):
    book = book_service.get_book_or_404(db, book_name)
    nav = book_service.get_nav(db, book)
    return templates.TemplateResponse(
        request,
        "reader.html",
        {
            "request": request,
            "book": book,
            "nav": nav,
            "share_base": _abs_url(request, f"/share/{book.name}"),
        },
    )


@router.get("/share/{book_name}/{sentence_id}", response_class=HTMLResponse)
def share(
    request: Request, book_name: str, sentence_id: int, db: Session = Depends(get_db)
):
    book = book_service.get_book_or_404(db, book_name)
    sentence = book_service.get_sentence(db, book, sentence_id)
    if sentence is None:
        raise HTTPException(status_code=404, detail="句子不存在或不属于该书")

    # 上一句 / 下一句（用于分享页内翻页）
    nav = book_service.get_nav(db, book)
    idx = next((i for i, n in enumerate(nav) if n["id"] == sentence.id), None)
    prev_id = nav[idx - 1]["id"] if idx and idx > 0 else None
    next_id = nav[idx + 1]["id"] if idx is not None and idx < len(nav) - 1 else None

    return templates.TemplateResponse(
        request,
        "share.html",
        {
            "request": request,
            "book": book,
            "sentence": sentence,
            "prev_id": prev_id,
            "next_id": next_id,
            "page_url": _abs_url(request, f"/share/{book.name}/{sentence.id}"),
            "reader_url": _abs_url(request, f"/book/{book.name}"),
        },
    )
