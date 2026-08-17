"""后台管理路由（开发期内容运营）。

- GET  /admin                       书籍列表（入口）
- GET  /admin/book/{name}           某书全部句子列表（有无内容标记 + 编辑/新建入口）
- GET  /admin/book/{name}/edit/{id} 编辑单句表单
- POST /admin/book/{name}/edit/{id} 保存编辑
- GET  /admin/book/{name}/new       新建句子表单
- POST /admin/book/{name}/new       保存新建

注：当前为开发期实现，未接入鉴权。上线前需加管理员登录 / token 校验。
"""
import json
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.book import BookSentence
from app.models.user import User
from app.services import book_service
from app.services.book_service import EDITABLE_FIELDS

router = APIRouter(prefix="/admin", tags=["admin"])

_tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=_tpl_dir)


@router.get("/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.id)).all()
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {"request": request, "users": users, "current_user_id": request.state.user_id},
    )


@router.post("/users/{user_id}/role")
async def admin_change_role(
    request: Request, user_id: int, db: Session = Depends(get_db)
):
    # 禁止管理员修改自己的角色，避免把自己降级后无法恢复
    if request.state.user_id == user_id:
        return RedirectResponse("/admin/users?error=不能修改自己的角色", status_code=303)
    target = db.get(User, user_id)
    if target is None:
        return RedirectResponse("/admin/users", status_code=303)
    form = await request.form()
    new_role = form.get("role")
    if new_role not in ("admin", "normal"):
        return RedirectResponse("/admin/users", status_code=303)
    target.role = new_role
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


def _build_data(form) -> dict:
    """从表单构造待写入字段；空串归为 None，meta 尝试解析 JSON。"""
    data: dict = {}
    for f in EDITABLE_FIELDS:
        if f == "meta":
            raw = (form.get("meta") or "").strip()
            if not raw:
                data["meta"] = None
            else:
                try:
                    data["meta"] = json.loads(raw)
                except json.JSONDecodeError:
                    data["meta"] = None  # 解析失败则忽略，避免脏数据
            continue
        val = form.get(f)
        if val is None:
            continue
        val = val.strip() if isinstance(val, str) else val
        if f == "sort":
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = 0
        data[f] = val if val != "" else None
    return data


@router.get("", response_class=HTMLResponse)
def admin_index(request: Request, db: Session = Depends(get_db)):
    books = book_service.list_books(db)
    return templates.TemplateResponse(
        request, "admin_index.html", {"request": request, "books": books}
    )


@router.get("/book/{name}", response_class=HTMLResponse)
def admin_book(request: Request, name: str, db: Session = Depends(get_db)):
    book = book_service.get_book_or_404(db, name)
    sentences = list(
        db.scalars(
            select(BookSentence)
            .where(BookSentence.book_id == book.id)
            .order_by(BookSentence.sort)
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "admin_book.html",
        {
            "request": request,
            "book": book,
            "sentences": sentences,
            "has_content": book_service.has_content,
        },
    )


@router.get("/book/{name}/edit/{sentence_id}", response_class=HTMLResponse)
def admin_edit_form(
    request: Request, name: str, sentence_id: int, db: Session = Depends(get_db)
):
    book = book_service.get_book_or_404(db, name)
    sentence = book_service.get_sentence(db, book, sentence_id)
    if sentence is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="句子不存在或不属于该书")
    return templates.TemplateResponse(
        request,
        "admin_edit.html",
        {
            "request": request,
            "book": book,
            "sentence": sentence,
            "is_new": False,
            "meta_text": json.dumps(sentence.meta, ensure_ascii=False, indent=2)
            if sentence.meta
            else "",
        },
    )


@router.post("/book/{name}/edit/{sentence_id}")
async def admin_edit_save(
    request: Request, name: str, sentence_id: int, db: Session = Depends(get_db)
):
    book = book_service.get_book_or_404(db, name)
    sentence = book_service.get_sentence(db, book, sentence_id)
    if sentence is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="句子不存在或不属于该书")
    form = await request.form()
    book_service.update_sentence(db, sentence, _build_data(form))
    return RedirectResponse(url=f"/admin/book/{name}", status_code=303)


@router.get("/book/{name}/new", response_class=HTMLResponse)
def admin_new_form(request: Request, name: str, db: Session = Depends(get_db)):
    book = book_service.get_book_or_404(db, name)
    # 预填 sort 为当前最大 +1
    max_sort = db.scalar(
        select(BookSentence.sort)
        .where(BookSentence.book_id == book.id)
        .order_by(BookSentence.sort.desc())
        .limit(1)
    )
    blank = BookSentence(sort=(max_sort or 0) + 1)
    return templates.TemplateResponse(
        request,
        "admin_edit.html",
        {
            "request": request,
            "book": book,
            "sentence": blank,
            "is_new": True,
            "meta_text": "",
        },
    )


@router.post("/book/{name}/new")
async def admin_new_save(request: Request, name: str, db: Session = Depends(get_db)):
    book = book_service.get_book_or_404(db, name)
    form = await request.form()
    book_service.create_sentence(db, book, _build_data(form))
    return RedirectResponse(url=f"/admin/book/{name}", status_code=303)
