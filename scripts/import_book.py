"""书籍导入脚本（真实导入）。

用法：
    python scripts/import_book.py qianziwen

逻辑：
1. 读取 data/<book_name>.json（字段对齐 qianziwen.json）。
2. upsert books 一条（书名/作者/朝代等来自内置元数据，便于扩展）。
3. 批量 upsert book_sentences（bg_image_key -> bg_image_prompt 映射）。
4. 幂等：已存在同名书则更新句子，不会重复建书。

依赖：需先创建库表。应用启动时 Base.metadata.create_all 已建表；
若用 Alembic，请先 migrate。
"""
import json
import os
import sys

from sqlalchemy import select

# 允许以脚本方式运行（将项目根加入 sys.path）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models.book import Book, BookSentence  # noqa: E402

# 脚本独立运行，确保表存在（应用启动时也会在 main.py 创建）
Base.metadata.create_all(bind=engine)

# 书籍元数据（后续新增书籍在此登记；句子内容仍来自 data/*.json）
BOOK_META = {
    "qianziwen": {
        "title": "千字文",
        "author": "周兴嗣",
        "dynasty": "南北朝",
        "description": "《千字文》由一千个不重复的汉字组成，四字一句、对仗工整，"
        "涵盖天文、地理、历史、伦理、修身诸方面，是传统蒙学经典。",
    },
}


def import_book(book_name: str) -> None:
    data_path = os.path.join(ROOT, "data", f"{book_name}.json")
    if not os.path.exists(data_path):
        raise SystemExit(f"未找到种子文件: {data_path}")

    with open(data_path, encoding="utf-8") as f:
        records = json.load(f)

    meta = BOOK_META.get(book_name, {})
    db = SessionLocal()
    try:
        # upsert 书籍
        book = db.scalar(select(Book).where(Book.name == book_name))
        if book is None:
            book = Book(name=book_name)
            db.add(book)
        book.title = meta.get("title", book_name)
        book.author = meta.get("author")
        book.dynasty = meta.get("dynasty")
        book.description = meta.get("description")
        book.status = 1
        db.flush()

        # upsert 句子
        count = 0
        for rec in records:
            sent = db.scalar(
                select(BookSentence).where(
                    BookSentence.book_id == book.id,
                    BookSentence.sort == rec["sort"],
                )
            )
            if sent is None:
                sent = BookSentence(book_id=book.id, sort=rec["sort"])
                db.add(sent)
            sent.original = rec.get("original", "")
            sent.pinyin = rec.get("pinyin")
            sent.translate_text = rec.get("translate_text")
            sent.word_explain = rec.get("word_explain")
            sent.intro_reading = rec.get("intro_reading")
            sent.extended_reading = rec.get("extended_reading")
            sent.story = rec.get("story")
            # 关键映射：源数据 bg_image_key（AI 出图提示词）-> bg_image_prompt
            sent.bg_image_prompt = rec.get("bg_image_key")
            sent.bg_image = rec.get("bg_image")
            sent.video_prompt = rec.get("video_prompt")
            sent.video_url = rec.get("video_url")
            sent.meta = rec.get("meta")
            count += 1

        db.commit()
        print(f"导入完成：book={book_name} title={book.title} 句子数={count}")
    finally:
        db.close()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法: python scripts/import_book.py <book_name>")
    import_book(sys.argv[1])


if __name__ == "__main__":
    main()
