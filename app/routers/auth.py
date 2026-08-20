"""认证路由：用户名/密码 注册、登录、登出；微信小程序登录。

- 第一个注册用户自动成为 admin；admin 可在后台管理其他用户的角色。
- 微信登录：用小程序 wx.login 的 code 换 openid，自动建/取用户，返回 user_id/role。
"""
import json
import os
import secrets
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
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

    # 第一个注册用户自动成为 admin
    any_user = db.scalar(select(User).order_by(User.id).limit(1))
    role = "admin" if any_user is None else "normal"

    salt, pwd_hash = hash_password(password)
    user = User(username=username, password_hash=pwd_hash, salt=salt, role=role)
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


def _exchange_wechat_code(code: str) -> str | None:
    """用 wx.login 返回的 code 换取 openid（标准库实现，零额外依赖）。"""
    if not settings.wechat_appid or not settings.wechat_secret:
        return None
    url = "https://api.weixin.qq.com/sns/jscode2session?" + urllib.parse.urlencode(
        {
            "appid": settings.wechat_appid,
            "secret": settings.wechat_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("openid")
    except Exception:
        return None


@router.post("/wechat")
async def wechat_login(request: Request, db: Session = Depends(get_db)):
    """微信小程序登录：code -> openid -> 自动建/取用户 -> 返回 user_id/role。

    小程序 wx.request 不自动管理 cookie，故 user_id 直接随 JSON 返回，
    由小程序本地存储并在上报足迹时带上；同时设置 session cookie 以备网页端复用。
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = (body.get("code") or "").strip()
    if not code:
        return JSONResponse({"ok": False, "error": "缺少 code"}, status_code=400)

    openid = _exchange_wechat_code(code)
    if not openid:
        return JSONResponse(
            {
                "ok": False,
                "error": "微信登录校验失败，请确认后端已配置 WECHAT_APPID/WECHAT_SECRET",
            },
            status_code=400,
        )

    user = db.scalar(select(User).where(User.wechat_openid == openid))
    if user is None:
        # 第一个微信用户也自动成为 admin
        any_user = db.scalar(select(User).order_by(User.id).limit(1))
        role = "admin" if any_user is None else "normal"
        # 随机密码，保证 password_hash/salt 非空（微信用户不走密码登录）
        rsalt, rhash = hash_password(secrets.token_hex(16))
        user = User(
            wechat_openid=openid,
            username=f"wx_{openid}",
            role=role,
            password_hash=rhash,
            salt=rsalt,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    resp = JSONResponse(
        {
            "ok": True,
            "user_id": user.id,
            "role": user.role,
            "username": user.username,
            "nickname": user.nickname or "",
        }
    )
    _set_session(resp, user.id)
    return resp


@router.post("/profile")
async def update_profile(request: Request, db: Session = Depends(get_db)):
    """小程序更新昵称/头像（无 cookie 场景：由前端带 user_id 标识用户）。

    注意：小程序 wx.request 不自动管理 cookie，故这里用请求体里的 user_id
    定位用户（个人项目够用；如需更强安全可改用 session 校验）。
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    user_id = body.get("user_id")
    nickname = (body.get("nickname") or "").strip()
    avatar_url = (body.get("avatar_url") or "").strip()

    if not user_id:
        return JSONResponse({"ok": False, "error": "缺少 user_id"}, status_code=400)
    if nickname and len(nickname) > 32:
        return JSONResponse({"ok": False, "error": "昵称最长 32 字符"}, status_code=400)

    user = db.get(User, user_id)
    if user is None:
        return JSONResponse({"ok": False, "error": "用户不存在"}, status_code=404)

    if nickname:
        user.nickname = nickname
    if avatar_url:
        user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)

    return JSONResponse(
        {
            "ok": True,
            "user_id": user.id,
            "role": user.role,
            "username": user.username,
            "nickname": user.nickname or "",
            "avatar_url": user.avatar_url or "",
        }
    )
