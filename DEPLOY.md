# ReadBook Python 端 · 生产部署指南（腾讯云 CentOS · 2G 内存 · 已有域名）

目标：把 `readbook-python`（FastAPI）以**生产模式**跑在腾讯云 CentOS 上，用 **nginx 反代 + HTTPS**，对外提供 `/`（阅读页）、`/api/book/*`（小程序 / Flutter 调用）、`/admin`（后台，需登录）。

> 2G 内存很紧张，所以：**SQLite 够用（别上 MySQL/Redis）、gunicorn 只开 2 个 worker、不装重型组件**。

---

## 0. 前置条件
- 一台 CentOS 7/8 腾讯云 CVM（2G 内存、有公网 IP）。
- 一个已解析到该服务器公网 IP 的域名（如 `book.yixialogic.cn`），A 记录指向服务器。
- 服务器已放行安全组 / 防火墙的 `80`、`443` 端口。
- 本地代码已 `git` 推到服务器（或 `scp` / 腾讯云 CFS 等），放在 `/opt/readbook/readbook-python`。

---

## 1. 系统依赖与 Python 环境

```bash
# CentOS
sudo dnf install -y python3.11 python3.11-pip nginx   # 或用 python3.11-venv
# 若没有 venv 包：
sudo dnf install -y python3.11-venv

# 建项目虚拟环境（与服务端开发一致，隔离依赖）
cd /opt/readbook/readbook-python
python3.11 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install gunicorn            # 生产 WSGI/ASGI 服务器

# 导入种子数据（仅首次）
cp .env.example .env
.venv/bin/python scripts/import_book.py qianziwen
```

> 生产**不要用 `--reload`**（那是开发模式，会多开一个文件监听进程、吃内存）。

---

## 2. 生成安全密钥（重要）

编辑 `.env`，把 `secret_key` 换成随机值（否则任何人能用同样的默认密钥伪造登录 cookie）：

```bash
.venv/bin/python -c "import secrets; print('SECRET_KEY=', secrets.token_hex(32))"
# 把输出写进 .env： secret_key=xxxx
```

---

## 3. 用 gunicorn 跑 FastAPI（ASGI：`uvicorn` worker）

建立 **systemd** 服务，开机自启、崩溃自拉。

`/etc/systemd/system/readbook.service`：
```ini
[Unit]
Description=ReadBook FastAPI
After=network.target

[Service]
# CentOS 上通常用 nginx 用户（dnf install nginx 会自动创建）；
# 也可建专用 deploy 用户。请确保该用户对 /opt/readbook 有读权限。
User=nginx
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

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now readbook
sudo systemctl status readbook      # 应显示 active (running)
curl http://127.0.0.1:8000/api/book/health   # 期望 {"status":"ok"}
```

> 注意：本项目的静态目录 `/static` 由 FastAPI 自身挂载（`StaticFiles`），gunicorn 后面也能直接返回；但生产更推荐让 nginx 直接托管静态文件（见第 5 步），减轻 Python 负担。

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
sudo dnf install -y epel-release
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d book.yixialogic.cn    # 自动改 nginx 配置 + 续期
sudo nginx -t && sudo systemctl reload nginx
```

完成后：
- 浏览器访问 `https://book.yixialogic.cn/` → 阅读页
- `https://book.yixialogic.cn/api/book/qianziwen/nav` → JSON（小程序/Flutter 调用）
- `https://book.yixialogic.cn/admin` → 后台登录页

---

## 5. 防火墙

```bash
# firewalld（CentOS 默认）
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
# 腾讯云还需在「安全组」放行 80/443（入站）
```

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
