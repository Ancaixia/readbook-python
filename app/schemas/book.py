"""Pydantic 出入参契约（接口与前端/Flutter 共享的数据结构）。"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str
    author: Optional[str] = None
    dynasty: Optional[str] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None
    sort: int = 0
    status: int = 1


class BookSentenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    sort: int
    original: str
    pinyin: Optional[str] = None
    translate_text: Optional[str] = None
    word_explain: Optional[str] = None
    intro_reading: Optional[str] = None
    extended_reading: Optional[str] = None
    story: Optional[str] = None
    bg_image_prompt: Optional[str] = None
    bg_image: Optional[str] = None
    video_prompt: Optional[str] = None
    video_url: Optional[str] = None
    meta: Optional[Any] = None


class NavItem(BaseModel):
    """导航列表单条：id + 排序 + 原文摘要。"""

    id: int
    sort: int
    original: str


class FootprintSaveIn(BaseModel):
    user_id: int
    sentence_id: int
    read_start_time: Optional[datetime] = None
    read_end_time: Optional[datetime] = None
    read_duration: int = 0


class FootprintStatOut(BaseModel):
    total_sentences: int = 0
    read_sentences: int = 0
    total_duration: int = 0
    last_read: Optional[NavItem] = None
