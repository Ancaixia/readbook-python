# ReadBook（Python / FastAPI）

「数据阅读系统」的 **Python + FastAPI** 实现（与 `readbook-laravel`、`readbook-go` 同源，业务模型一致）。
当前为 **骨架阶段**：项目结构、数据模型、接口契约已就位，业务实现待后续补充。

## 技术定位（对应 V1.1 设计）
- FastAPI 提供 **页面（Jinja2 SSR，便于 SEO / 分享）** 与 **API** 两套出口。
- 数据模型与 Laravel 端对齐：`books` / `book_sentences` / `user_book_footprints` / `wechat_articles`。
- 后续 Flutter 客户端将调用本仓库的 `/api/book/...` 接口。

## 目录结构
```
readbook-python/
├── app/
│   ├── core/        # config（pydantic-settings）、database（SQLAlchemy engine/session）
│   ├── models/      # SQLAlchemy 模型（4 张表，字段已对齐设计）
│   ├── schemas/     # Pydantic 出入参契约
│   ├── routers/     # api（/api/book/*）、pages（SSR 页面）
│   ├── services/    # 业务逻辑占位（后续填充）
│   ├── templates/   # Jinja2 模板（base / index 占位）
│   ├── static/      # 静态资源
│   └── main.py      # 应用入口，挂载路由与静态目录，启动时建表
├── data/            # 种子数据（qianziwen.json）
├── scripts/         # import_book.py（导入脚本，待实现）
├── requirements.txt
└── .env.example
```

## 本地运行
```bash
pip install -r requirements.txt
cp .env.example .env          # 默认使用本地 SQLite
uvicorn app.main:app --reload --port 8200
```
- 首页：http://127.0.0.1:8200/
- 健康检查：http://127.0.0.1:8200/api/book/health
- 业务接口（nav/detail/footprint/stat）当前返回 `501 TODO`，将在下一阶段实现。

## 进度
- [x] 骨架：目录 / 配置 / 模型 / schema / 路由占位 / 模板
- [ ] 业务代码：导入脚本、4 个 book 接口、阅读页与分享卡页
- [ ] Flutter 客户端
