"""认证路由：用户名/密码 注册、登录、登出。

本期仅实现用户名密码登录；User 表已预留 phone / wechat_openid 字段，
后续可在此扩展电话验证码、微信 OAuth 登录（绑定同一 user 即可）。
"""
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.session import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    create_session_token,
    hash_password,
    verify_password,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

_tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=_tpl_dir)

_MIN_PWD_LEN = 6


def _set_session(resp: RedirectResponse, user_id: int) -> None:
    resp.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(
        request, "login.html", {"request": request, "error": error}
    )


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.salt, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"request": request, "error": "用户名或密码错误"}
        )
    resp = RedirectResponse("/admin", status_code=303)
    _set_session(resp, user.id)
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str = ""):
    return templates.TemplateResponse(
        request, "register.html", {"request": request, "error": error}
    )


@router.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""
    password2 = form.get("password2") or ""

    errors = []
    if not username:
        errors.append("请输入用户名")
    if len(password) < _MIN_PWD_LEN:
        errors.append(f"密码至少 {_MIN_PWD_LEN} 位")
    if password != password2:
        errors.append("两次输入的密码不一致")
    if not errors:
        exists = db.scalar(select(User).where(User.username == username))
        if exists is not None:
            errors.append("该用户名已被注册")

    if errors:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "request": request,
                "error": "；".join(errors),
                "username": username,
            },
        )

    salt, pwd_hash = hash_password(password)
    user = User(username=username, password_hash=pwd_hash, salt=salt)
    db.add(user)
    db.commit()
    db.refresh(user)

    resp = RedirectResponse("/admin", status_code=303)
    _set_session(resp, user.id)
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse("/auth/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp
