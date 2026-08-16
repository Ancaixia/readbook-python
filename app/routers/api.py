"""API 路由：/api/book/*

业务接口（与 Laravel 端 BookController 语义一致）：
- GET  /{book_name}/nav            导航列表（目录）
- GET  /{book_name}/detail/{id}    单句详情（原文/拼音/译注/字词/导读/拓展/典故）
- POST /{book_name}/footprint/save 保存阅读足迹（upsert + 时长累加 + 置位最近阅读）
- GET  /{book_name}/stat           阅读统计（已读句数 / 总时长 / 进度 / 最近阅读）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.book import (
    BookSentenceOut,
    FootprintSaveIn,
    FootprintStatOut,
    NavItem,
)
from app.services import book_service

router = APIRouter(prefix="/api/book", tags=["book"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/{book_name}/nav")
def nav(book_name: str, db: Session = Depends(get_db)) -> dict:
    book = book_service.get_book_or_404(db, book_name)
    items = [NavItem(**row) for row in book_service.get_nav(db, book)]
    return {
        "book": {
            "id": book.id,
            "name": book.name,
            "title": book.title,
            "author": book.author,
            "dynasty": book.dynasty,
            "cover_image": book.cover_image,
            "description": book.description,
        },
        "sentences": [item.model_dump() for item in items],
        "total": len(items),
    }


@router.get("/{book_name}/detail/{sentence_id}", response_model=BookSentenceOut)
def detail(book_name: str, sentence_id: int, db: Session = Depends(get_db)):
    book = book_service.get_book_or_404(db, book_name)
    sentence = book_service.get_sentence(db, book, sentence_id)
    if sentence is None:
        raise HTTPException(status_code=404, detail="句子不存在或不属于该书")
    return sentence


@router.post("/{book_name}/footprint/save")
def save_footprint(
    book_name: str, payload: FootprintSaveIn, db: Session = Depends(get_db)
) -> dict:
    if payload.user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id 必须为正整")
    book = book_service.get_book_or_404(db, book_name)
    fp = book_service.save_footprint(
        db,
        book,
        user_id=payload.user_id,
        sentence_id=payload.sentence_id,
        read_duration=payload.read_duration,
        read_start_time=payload.read_start_time,
        read_end_time=payload.read_end_time,
    )
    return {
        "ok": True,
        "user_id": fp.user_id,
        "sentence_id": fp.sentence_id,
        "read_duration": fp.read_duration,
        "is_last_read": fp.is_last_read,
    }


@router.get("/{book_name}/stat", response_model=FootprintStatOut)
def stat(book_name: str, user_id: int = 0, db: Session = Depends(get_db)):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    book = book_service.get_book_or_404(db, book_name)
    return FootprintStatOut(**book_service.get_stat(db, book, user_id))
