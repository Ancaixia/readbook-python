"""数据模型：与 Laravel 端对齐的 4 张表。

字段说明（详见 V1.1 设计文档）：
- Book：书籍元信息（name 为英文标识，如 qianziwen）
- BookSentence：句子级内容（原文/拼音/译注/字词/导读/拓展/典故/出图提示词/出图URL/出视频...）
- UserBookFootprint：用户阅读足迹（按 user+book+sentence 唯一，时长累加）
- WechatArticle：公众号发文记录
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)  # 英文标识
    title = Column(String(128), nullable=False)  # 中文名，如 千字文
    author = Column(String(128), nullable=True)
    dynasty = Column(String(64), nullable=True)
    cover_image = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    sort = Column(Integer, default=0)
    status = Column(Integer, default=1)  # 1=上线
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sentences = relationship(
        "BookSentence", backref="book", cascade="all, delete-orphan"
    )


class BookSentence(Base):
    __tablename__ = "book_sentences"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), index=True, nullable=False)
    sort = Column(Integer, nullable=False)
    original = Column(Text, nullable=False)
    pinyin = Column(Text, nullable=True)
    translate_text = Column(Text, nullable=True)
    word_explain = Column(Text, nullable=True)
    intro_reading = Column(Text, nullable=True)
    extended_reading = Column(Text, nullable=True)
    story = Column(Text, nullable=True)
    bg_image_prompt = Column(Text, nullable=True)  # 源数据 bg_image_key（AI 出图提示词）
    bg_image = Column(String(512), nullable=True)  # AI 出图后回填
    video_prompt = Column(Text, nullable=True)
    video_url = Column(String(512), nullable=True)  # 出视频后回填
    meta = Column(JSON, nullable=True)  # 书籍特有字段（如百家姓的姓氏/郡望/名人）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserBookFootprint(Base):
    __tablename__ = "user_book_footprints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), index=True, nullable=False)
    sentence_id = Column(
        Integer, ForeignKey("book_sentences.id"), index=True, nullable=False
    )
    sort = Column(Integer, default=0)
    read_start_time = Column(DateTime, nullable=True)
    read_end_time = Column(DateTime, nullable=True)
    read_duration = Column(Integer, default=0)  # 秒，重复阅读累加
    is_last_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WechatArticle(Base):
    __tablename__ = "wechat_articles"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), index=True, nullable=False)
    sentence_id = Column(
        Integer, ForeignKey("book_sentences.id"), index=True, nullable=True
    )
    media_id = Column(String(255), nullable=True)
    article_url = Column(String(512), nullable=True)
    status = Column(Integer, default=0)  # 0=草稿 1=已发布
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
