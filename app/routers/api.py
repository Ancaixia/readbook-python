"""API 路由：/api/book/*

骨架阶段：
- /health 可用（用于探活）。
- 业务接口（nav / detail / footprint / stat）返回 501 TODO，待下一阶段实现。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/book", tags=["book"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ===== 业务接口：骨架占位，下一阶段实现 =====


@router.get("/{book_name}/nav")
def nav(book_name: str, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=501,
        detail="TODO: 实现导航列表（返回该书所有句子的 sort + 原文摘要）",
    )


@router.get("/{book_name}/detail/{sentence_id}")
def detail(book_name: str, sentence_id: int, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=501,
        detail="TODO: 实现单句详情（原文/拼音/译注/字词/导读/拓展/典故）",
    )


@router.post("/{book_name}/footprint/save")
def save_footprint(book_name: str, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=501,
        detail="TODO: 实现阅读足迹保存（upsert + 时长累加 + 置位 is_last_read）",
    )


@router.get("/{book_name}/stat")
def stat(book_name: str, user_id: int = 0, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=501,
        detail="TODO: 实现阅读统计（已读句数 / 总时长 / 最近阅读）",
    )
