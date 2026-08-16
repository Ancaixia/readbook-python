# ReadBook（Python / FastAPI）

「数据阅读系统」的 **Python + FastAPI** 实现（与 `readbook-laravel`、`readbook-go` 同源，业务模型一致）。

提供 **页面（Jinja2 SSR，便于 SEO / 公众号分享）** 与 **API** 两套出口，供 Web 直接浏览、Flutter 客户端调用。

## 已实现的业务
- 数据模型（对齐设计）：`books` / `book_sentences` / `user_book_footprints` / `wechat_articles`
- 导入脚本 `scripts/import_book.py`：读取 `data/<book>.json`，建书 + 批量写句子（`bg_image_key → bg_image_prompt` 映射），幂等
- API：`/api/book/{name}/nav`、`/detail/{id}`、`/footprint/save`、`/stat`
- 页面：`/`（书籍列表）、`/book/{name}`（阅读页）、`/share/{name}/{id}`（公众号分享卡页，含 OG 元信息 + 复制链接）

## 目录结构
```
readbook-python/
├── app/
│   ├── core/        # config（pydantic-settings）、database（SQLAlchemy engine/session）
│   ├── models/      # SQLAlchemy 模型（4 张表）
│   ├── schemas/     # Pydantic 出入参契约
│   ├── routers/     # api（/api/book/*）、pages（SSR 页面）
│   ├── services/    # 业务逻辑（book_service.py）
│   ├── templates/   # Jinja2 模板（base / index / reader / share）
│   ├── static/      # 静态资源
│   └── main.py      # 应用入口，挂载路由与静态目录，启动时建表
├── data/            # 种子数据（qianziwen.json）
├── scripts/         # import_book.py（真实导入）
├── requirements.txt
├── .env.example
└── .venv/           # 本地虚拟环境（已在 .gitignore 排除，勿提交）
```

## 本地运行
> 依赖装在项目本地 `.venv`，**请用这个 venv 运行**（不要用系统 Anaconda 的 python，否则找不到 fastapi 等包）。

```powershell
cd readbook-python
.\.venv\Scripts\Activate.ps1          # 激活虚拟环境（或下文直接用 venv 的 python）
# 若 .venv 不存在：python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt

cp .env.example .env                  # 默认使用本地 SQLite（readbook.db）
.\.venv\Scripts\python.exe scripts/import_book.py qianziwen   # 导入千字文 125 句
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8200
```
- 首页：http://127.0.0.1:8200/
- 阅读页：http://127.0.0.1:8200/book/qianziwen
- 分享卡页：http://127.0.0.1:8200/share/qianziwen/1
- 健康检查：http://127.0.0.1:8200/api/book/health

## API 速览
| 方法 | 路径 | 说明 |
|---|---|---|
| GET  | `/api/book/{name}/nav` | 书籍信息 + 全部句子目录（id/sort/原文/拼音） |
| GET  | `/api/book/{name}/detail/{id}` | 单句详情（原文/拼音/译注/字词/导读/拓展/典故） |
| POST | `/api/book/{name}/footprint/save` | 保存阅读足迹（upsert + 时长累加 + 置位最近阅读） |
| GET  | `/api/book/{name}/stat?user_id=` | 统计：已读句数 / 总时长 / 进度 / 最近阅读 |

## 进度
- [x] 骨架：目录 / 配置 / 模型 / schema / 路由 / 模板
- [x] 业务代码：导入脚本、4 个 book 接口、阅读页与分享卡页
- [ ] Flutter 客户端（将调用本仓库 `/api/book/*`）
- [ ] 大并发增强（Redis 缓存 / 异步 SQLAlchemy / 限流 / 压测）
```
