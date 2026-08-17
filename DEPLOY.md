# ReadBook Python 端 · 生产部署指南（腾讯云 Ubuntu · 2G 内存 · 已有域名）

目标：把 `readbook-python`（FastAPI）以**生产模式**跑在腾讯云 Ubuntu 上，用 **nginx 反代 + HTTPS**，对外提供 `/`（阅读页）、`/api/book/*`（小程序 / Flutter 调用）、`/admin`（后台，需登录）。

> 2G 内存很紧张，所以：**SQLite 够用（别上 MySQL/Redis）、gunicorn 只开 2 个 worker、不装重型组件**。

> 与 CentOS 的区别（已按 Ubuntu 调整）：包管理器用 `apt`（不是 `dnf`）；防火墙用 `ufw`（不是 `firewalld`）；certbot 在 Ubuntu 官方源直接有（无需 `epel-release`）；运行用户用 `www-data`（Ubuntu 上 nginx 默认用户，不是 `nginx`）。

---

## 0. 前置条件
- 一台 Ubuntu 22.04 / 24.04 LTS 腾讯云 CVM（2G 内存、有公网 IP）。
- 一个已解析到该服务器公网 IP 的域名（如 `book.yixialogic.cn`），A 记录指向服务器。
- 服务器已放行**安全组**的 `80`、`443` 端口（腾讯云控制台 → 安全组 → 入站规则）。
- 本地代码已放到服务器 `/opt/readbook/readbook-python`（获取方式见下方 **0.1**）。

---

## 0.1 把代码弄到服务器：上传目录 vs git 拉取

两种方式都可行，按你的情况选：

**A. 上传本地目录（scp / rsync）** —— 适合代码还没进版本库、或不想把代码放到公网/远程仓库
- 优点：无需 git 远程仓库、无需推代码；`.env` 等敏感文件也能直接带走。
- 缺点：每次更新手动传；容易漏文件 / 版本不一致；回滚麻烦。
- 命令（排除不需要传的）：
  ```bash
  # rsync（推荐：增量、可排除，快且干净）
  rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
        --exclude '.env' --exclude '*.db' \
        /本地路径/readbook-python/  用户@服务器IP:/opt/readbook/readbook-python/

  # scp（整目录搬运，慢且不排除，一般仅首次用）
  scp -r /本地路径/readbook-python 用户@服务器IP:/opt/readbook/
  ```
  > `.venv` 不要传（服务器上自己建）；`.env` 和 `*.db` 不要传（服务器本地生成 / 导入）。

**B. 从 git 仓库拉取** —— 适合代码已用 git 管理、更新频繁
- 优点：更新只需 `git pull` + `systemctl restart readbook`；版本可追溯、易回滚（`git checkout <commit>`）；协作友好。
- 缺点：需要远程仓库（GitHub 私有库 / 腾讯云 CODING / Gitee）；`.env` 不能入库（服务器本地 `cp .env.example .env`）。
- 命令：
  ```bash
  # 服务器上（首次）
  sudo apt install -y git
  git clone <你的仓库地址> /opt/readbook/readbook-python
  cd /opt/readbook/readbook-python && cp .env.example .env

  # 之后每次更新
  cd /opt/readbook/readbook-python && git pull && sudo systemctl restart readbook
  ```
  > 仓库里务必 `.gitignore` 掉 `.venv/`、`__pycache__/`、`*.pyc`、`.env`、`*.db`。

**怎么选**：代码若已在 git 里（哪怕只是本地 git + 推到私有仓库），优先 **B（git 拉取）**，部署和更新都省心；若只想尽快跑起来、代码还没入库，用 **A（rsync 上传）** 最快。本项目不依赖任何远程仓库，A、B 都可行。

---

## 1. 系统依赖与 Python 环境

```bash
# Ubuntu：更新索引并装基础依赖
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx

# 建项目虚拟环境（与服务端开发一致，隔离依赖）
cd /opt/readbook/readbook-python
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install gunicorn            # 生产 WSGI/ASGI 服务器

# 导入种子数据（仅首次）
cp .env.example .env
.venv/bin/python scripts/import_book.py qianziwen
```

> 生产**不要用 `--reload`**（那是开发模式，会多开一个文件监听进程、吃内存）。
> Ubuntu 默认 python3 版本（22.04=3.10 / 24.04=3.12）均满足 FastAPI 要求，直接用 `python3` 即可，无需指定小版本。

---

## 2. 生成安全密钥（重要）

编辑 `.env`，把 `secret_key` 换成随机值（否则任何人能用同样的默认密钥伪造登录 cookie）：

```bash
.venv/bin/python -c "import secrets; print('SECRET_KEY=', secrets.token_hex(32))"
# 把输出写进 .env： secret_key=xxxx
```

如需小程序微信登录，另在 `.env` 填：
```
WECHAT_APPID=你的小程序AppID
WECHAT_SECRET=你的小程序AppSecret
```
（取自微信公众平台 → 开发 → 开发管理 → 开发设置。留空则微信登录接口返回错误，小程序自动降级为未登录仍可浏览。）

> 账号与角色：第一个注册用户自动成为 `admin`（可在后台「用户」页修改他人角色）；
> 普通用户 `normal` 可登录小程序记录阅读足迹。本地开发库若没有任何 admin，启动时会自动把最早注册的用户提升为 admin。

---

## 3. 用 gunicorn 跑 FastAPI（ASGI：`uvicorn` worker）

建立 **systemd** 服务，开机自启、崩溃自拉。

`/etc/systemd/system/readbook.service`：
```ini
[Unit]
Description=ReadBook FastAPI
After=network.target

[Service]
# Ubuntu 上 nginx 默认用户是 www-data。让 gunicorn 也以 www-data 运行，
# 需保证该用户对 /opt/readbook 有读权限、对 sqlite 库文件有写权限。
# 更稳妥的做法：建专用用户（见下方说明），并把 User 改成该用户。
User=www-data
Group=www-data
WorkingDirectory=/opt/readbook/readbook-python
Environment=PATH=/opt/readbook/readbook-python/.venv/bin
ExecStart=/opt/readbook/readbook-python/.venv/bin/gunicorn app.main:app \
          -k uvicorn.workers.UvicornWorker \
          -w 2 \
          -b 127.0.0.1:8000 \
          --timeout 60
# 2G 内存：2 个 worker 足够；如 OOM 可降到 1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> 推荐：建一个专用系统用户，避免和 www-data 权限纠缠：
> ```bash
> sudo useradd -r -s /usr/sbin/nologin readbook
> sudo chown -R readbook:readbook /opt/readbook
> ```
> 然后把上面 service 文件的 `User=www-data` / `Group=www-data` 改成 `User=readbook` / `Group=readbook`。
> （若用 www-data，需执行 `sudo chown -R www-data:www-data /opt/readbook/readbook-python` 并确保 .venv 也可读。）

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now readbook
sudo systemctl status readbook      # 应显示 active (running)
curl http://127.0.0.1:8000/api/book/health   # 期望 {"status":"ok"}
```

> 注意：本项目的静态目录 `/static` 由 FastAPI 自身挂载（`StaticFiles`），gunicorn 后面也能直接返回；但生产更推荐让 nginx 直接托管静态文件（见第 4 步），减轻 Python 负担。

---

## 4. nginx 反向代理 + HTTPS（certbot）

`/etc/nginx/conf.d/readbook.conf`：
```nginx
server {
    listen 80;
    server_name book.yixialogic.cn;     # 改成你的域名
    # certbot 会自动加 80->443 跳转，此处保留即可
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name book.yixialogic.cn;

    ssl_certificate     /etc/letsencrypt/live/book.yixialogic.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/book.yixialogic.cn/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # 可选：让 nginx 直接托管静态资源（生产推荐，省 Python）
    location /static/ {
        alias /opt/readbook/readbook-python/app/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

申请免费证书（certbot）：
```bash
# Ubuntu 官方源自带 certbot，无需 epel-release
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d book.yixialogic.cn    # 自动改 nginx 配置 + 续期
sudo nginx -t && sudo systemctl reload nginx
```

完成后：
- 浏览器访问 `https://book.yixialogic.cn/` → 阅读页
- `https://book.yixialogic.cn/api/book/qianziwen/nav` → JSON（小程序/Flutter 调用）
- `https://book.yixialogic.cn/admin` → 后台登录页

---

## 5. 防火墙

腾讯云主要靠**安全组**放行 80/443（已在第 0 步说明）。系统层若启用了 `ufw`（Ubuntu 默认**未启用**），再放行端口：

```bash
# ufw（Ubuntu 默认防火墙，默认未启用；若启用才需要下面命令）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
# 腾讯云还需在「安全组」放行 80/443（入站）——这是云平台的虚拟防火墙，与系统 ufw 是两回事
```

> 若不确定是否启用了 ufw，可用 `sudo ufw status` 查看；显示 `inactive` 则系统层没挡，只需管安全组即可。

---

## 6. 小程序 / Flutter 接入

- 小程序的 `app.js` 与 Flutter 的 `lib/api/api_client.dart` 里把 `baseUrl` 改成 `https://book.yixialogic.cn`。
- **微信小程序额外要求**：在「微信公众平台 → 开发设置 → 服务器域名」把 `https://book.yixialogic.cn` 加入 **request 合法域名**。
- Flutter / 浏览器直接调 HTTPS 即可，无需额外配置。

---

## 7. 日常运维

```bash
# 看日志
sudo journalctl -u readbook -f
# 重新部署（拉新代码后）
sudo systemctl restart readbook
# 证书续期（certbot 通常已装定时器，可手动试）
sudo certbot renew --dry-run
```

## 8. 2G 内存优化清单
- gunicorn worker `-w 2`（OOM 就降到 1）。
- 用 SQLite，不上 MySQL/Redis。
- nginx 直接托管 `/static`，减少 Python 请求。
- 关闭 FastAPI 的 `--reload`；`debug=false`（`.env` 里设）。
- 如日后访问量大，再加 Redis 缓存 `/api/book/*` 响应、或对象存储放 AI 出图。
