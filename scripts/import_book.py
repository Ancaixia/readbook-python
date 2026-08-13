"""书籍导入脚本（骨架占位）。

业务阶段实现：
1. 读取 data/<book_name>.json（字段对齐 qianziwen.json）。
2. 写入 books 一条 + 批量写入 book_sentences（bg_image_key -> bg_image_prompt 映射）。
3. 幂等：已存在则跳过 / 更新。

运行：python scripts/import_book.py qianziwen
"""
import json
import os
import sys

from sqlalchemy.orm import Session

# 允许以脚本方式运行（将项目根加入 sys.path）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.core.database import SessionLocal  # noqa: E402
from app.models.book import Book, BookSentence  # noqa: E402


def import_book(book_name: str) -> None:
    data_path = os.path.join(ROOT, "data", f"{book_name}.json")
    if not os.path.exists(data_path):
        raise SystemExit(f"未找到种子文件: {data_path}")

    # TODO(业务阶段): 解析 JSON 并 upsert 到 Book / BookSentence
    print(f"TODO: 解析 {data_path} 并导入（待实现）")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法: python scripts/import_book.py <book_name>")
    book_name = sys.argv[1]
    # 占位：暂不实际写库，避免骨架阶段产生副作用
    import_book(book_name)


if __name__ == "__main__":
    main()
