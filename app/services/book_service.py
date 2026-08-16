"""书籍阅读业务服务层。

把"导航 / 详情 / 足迹 / 统计"的纯逻辑收拢到这里，
API 路由与页面路由都只做参数解析与响应包装，便于复用与单测。
（与 Laravel 端 BookController 的语义保持一致。）
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.book import Book, BookSentence, UserBookFootprint


def get_book(db: Session, name: str) -> Book | None:
    """按英文标识取书；不存在返回 None。"""
    return db.scalar(select(Book).where(Book.name == name))


def get_book_or_404(db: Session, name: str) -> Book:
    book = get_book(db, name)
    if book is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"书籍不存在：{name}")
    return book


def list_books(db: Session) -> list[Book]:
    """首页用：返回全部已上线书籍（按 sort 升序）。"""
    return list(
        db.scalars(select(Book).where(Book.status == 1).order_by(Book.sort, Book.id))
    )


def get_nav(db: Session, book: Book) -> list[dict]:
    """导航列表：每句只返回 id / sort / 原文 / 拼音，供目录与翻页。"""
    rows = db.execute(
        select(
            BookSentence.id,
            BookSentence.sort,
            BookSentence.original,
            BookSentence.pinyin,
        )
        .where(BookSentence.book_id == book.id)
        .order_by(BookSentence.sort)
    ).mappings().all()
    return [
        {
            "id": r["id"],
            "sort": r["sort"],
            "original": r["original"],
            "pinyin": r["pinyin"],
        }
        for r in rows
    ]


def get_sentence(db: Session, book: Book, sentence_id: int) -> BookSentence | None:
    """取单句；必须属于该书，否则返回 None。"""
    return db.scalar(
        select(BookSentence).where(
            BookSentence.id == sentence_id, BookSentence.book_id == book.id
        )
    )


def save_footprint(
    db: Session,
    book: Book,
    *,
    user_id: int,
    sentence_id: int,
    read_duration: int = 0,
    read_start_time: datetime | None = None,
    read_end_time: datetime | None = None,
) -> UserBookFootprint:
    """保存/累加阅读足迹。

    - 同一 (user, book, sentence) 唯一，首次创建、重复阅读累加 read_duration。
    - 每次保存把该书内其它足迹的 is_last_read 置 0，仅当前句为 1（最近阅读）。
    """
    sentence = get_sentence(db, book, sentence_id)
    if sentence is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404, detail=f"句子不存在：book={book.name}, id={sentence_id}"
        )

    fp = db.scalar(
        select(UserBookFootprint).where(
            UserBookFootprint.user_id == user_id,
            UserBookFootprint.book_id == book.id,
            UserBookFootprint.sentence_id == sentence_id,
        )
    )
    if fp is None:
        fp = UserBookFootprint(
            user_id=user_id,
            book_id=book.id,
            sentence_id=sentence_id,
            sort=sentence.sort,
        )
        db.add(fp)

    if read_duration:
        fp.read_duration = (fp.read_duration or 0) + read_duration
    if read_start_time:
        fp.read_start_time = read_start_time
    if read_end_time:
        fp.read_end_time = read_end_time

    # 置位"最近阅读"：该书内其余足迹全部归零，仅当前句为 1
    fp.is_last_read = True
    db.query(UserBookFootprint).filter(
        UserBookFootprint.user_id == user_id,
        UserBookFootprint.book_id == book.id,
        UserBookFootprint.sentence_id != sentence_id,
    ).update({UserBookFootprint.is_last_read: False})

    db.commit()
    db.refresh(fp)
    return fp


def get_stat(db: Session, book: Book, user_id: int) -> dict:
    """阅读统计：总句数 / 已读句数 / 总时长 / 最近阅读句。"""
    total_sentences = db.scalar(
        select(func.count(BookSentence.id)).where(BookSentence.book_id == book.id)
    ) or 0

    read_sentences = (
        db.scalar(
            select(func.count(UserBookFootprint.id)).where(
                UserBookFootprint.user_id == user_id,
                UserBookFootprint.book_id == book.id,
            )
        )
        or 0
    )

    total_duration = (
        db.scalar(
            select(func.coalesce(func.sum(UserBookFootprint.read_duration), 0)).where(
                UserBookFootprint.user_id == user_id,
                UserBookFootprint.book_id == book.id,
            )
        )
        or 0
    )

    last = db.scalar(
        select(BookSentence)
        .join(
            UserBookFootprint,
            UserBookFootprint.sentence_id == BookSentence.id,
        )
        .where(
            UserBookFootprint.user_id == user_id,
            UserBookFootprint.book_id == book.id,
            UserBookFootprint.is_last_read == True,  # noqa: E712
        )
        .order_by(UserBookFootprint.updated_at.desc())
    )

    last_item = (
        {"id": last.id, "sort": last.sort, "original": last.original}
        if last
        else None
    )
    progress = round(read_sentences / total_sentences, 4) if total_sentences else 0

    return {
        "total_sentences": total_sentences,
        "read_sentences": read_sentences,
        "total_duration": int(total_duration),
        "progress": progress,
        "last_read": last_item,
    }


# 后台管理可编辑字段（与 BookSentence 模型对齐）
EDITABLE_FIELDS = [
    "original",
    "pinyin",
    "translate_text",
    "word_explain",
    "intro_reading",
    "extended_reading",
    "story",
    "bg_image_prompt",
    "bg_image",
    "video_prompt",
    "video_url",
    "sort",
    "meta",
]

# 判定"已填充详细内容"的依据字段
CONTENT_FIELDS = (
    "translate_text",
    "word_explain",
    "intro_reading",
    "extended_reading",
    "story",
)


def has_content(sentence: BookSentence) -> bool:
    """句子是否已填充任一详细内容（译注/字词/导读/拓展/故事）。"""
    return any(getattr(sentence, f) for f in CONTENT_FIELDS)


def update_sentence(
    db: Session, sentence: BookSentence, data: dict
) -> BookSentence:
    """按 data 中的字段原地更新句子（仅更新存在的键）。"""
    for f in EDITABLE_FIELDS:
        if f in data:
            setattr(sentence, f, data[f])
    db.commit()
    db.refresh(sentence)
    return sentence


def create_sentence(db: Session, book: Book, data: dict) -> BookSentence:
    """在指定书下新建一句；book_id 固定取该书。"""
    sent = BookSentence(book_id=book.id)
    for f in EDITABLE_FIELDS:
        if f in data:
            setattr(sent, f, data[f])
    db.add(sent)
    db.commit()
    db.refresh(sent)
    return sent
