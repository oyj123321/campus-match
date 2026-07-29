# 腾讯云轻量机部署指南（68 元档 / 上海）

面向：已购买 **轻量应用服务器 2核2G**，系统选 **Ubuntu 22.04**。  
目标：同学用浏览器打开你的网站；数据存在**云服务器**上，不在你自己的 Windows 电脑。

> 更完整的公测 checklist 见 [`beta-launch.md`](beta-launch.md)。

---

## 0. 先搞清三样东西

| 名称 | 是什么 | 你要填/买的 |
|------|--------|-------------|
| **公网 IP** | 腾讯云控制台里那串数字，如 `1.2.3.4` | 买机后自动有 |
| **公开网址** | 别人怎么访问：先用 `http://公网IP`，以后换成 `https://域名` | 域名可选，约 50～100 元/年 |
| **数据库** | `instance/campus_match.db` 文件，跟代码一起在**这台云机**上 | 不用另买「数据库服务器」 |

上海机房用**自己的域名**做正式 HTTPS 站点，通常要先完成 **ICP 备案**（要几周）。  
**本周先拉熟人试：** 用 `http://公网IP` 即可，不必先买域名、也不必先备案。

---

## 1. 控制台准备（网页上点）

1. 登录 [腾讯云轻量](https://console.cloud.tencent.com/lighthouse)，记下 **公网 IP**。
2. 防火墙 / 防火墙规则放行：
   - **22**（SSH，仅你自己连）
   - **80**（HTTP）
   - **443**（以后上 HTTPS 用）
3. 重置并保存 **root 密码**（或绑定 SSH 密钥）。

本机（Windows PowerShell）试连：

```powershell
ssh root@你的公网IP
```

能进去再往下做。

---

## 2. 服务器初始化（SSH 里执行）

```bash
apt update && apt upgrade -y
apt install -y git python3 python3-pip python3-venv nginx
```

（下面用 **Nginx 反代**；Flask 只监听本机 5000，更安全。）

---

## 3. 拉取代码并安装依赖

```bash
mkdir -p /opt && cd /opt
git clone https://github.com/oyj123321/campus-match.git
cd campus-match

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

**不要**在公测库执行 `seed.py`（会灌演示号）。

---

## 4. 配置 `.env`

```bash
cd /opt/campus-match
cp .env.example .env
nano .env   # 或 vim
```

最少填这些（把例子换成你的）：

```env
SECRET_KEY=这里粘贴随机串
FLASK_DEBUG=false
ADMIN_SECRET=再生成一串只给你自己

MAIL_ENABLED=true
MAIL_SERVER=smtp.qq.com
MAIL_PORT=587
MAIL_USERNAME=你的QQ号@qq.com
MAIL_PASSWORD=SMTP授权码
MAIL_FROM=你的QQ号@qq.com

# 先用 IP；以后有域名再改成 https://你的域名
PUBLIC_URL=http://你的公网IP

MATCH_MODE=one_to_one
MATCH_WEEKLY_NEW_LIMIT=1
MATCH_COOLDOWN_HOURS=12
REVEAL_REQUIRE_OPT_IN=true
INSTANT_MATCH_ENABLED=true
CROSS_SCHOOL_MATCHING_ENABLED=false
BATCH_SCHEDULER_ENABLED=true
BATCH_MATCH_DAY=1
BATCH_MATCH_HOUR=21
REGISTER_RATE_LIMIT=5
REGISTER_RATE_WINDOW=3600
```

生成密钥（在服务器上执行，复制输出）：

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

初始化空库：

```bash
cd /opt/campus-match
source .venv/bin/activate
python -c "from app import init_db; init_db()"
```

---

## 5. 让 Flask 常驻（systemd）

```bash
nano /etc/systemd/system/campus-match.service
```

写入：

```ini
[Unit]
Description=CampusMatch
After=network.target

[Service]
User=root
WorkingDirectory=/opt/campus-match
Environment=PATH=/opt/campus-match/.venv/bin
ExecStart=/opt/campus-match/.venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

说明：当前 `app.py` 监听 `127.0.0.1:5000`（只本机可访问），外面由 Nginx 转发，这样正确。

```bash
systemctl daemon-reload
systemctl enable --now campus-match
systemctl status campus-match
```

看日志：

```bash
journalctl -u campus-match -f
```

---

## 6. Nginx 反代（公开 HTTP）

```bash
nano /etc/nginx/sites-available/campus-match
```

写入（把 `你的公网IP` 可写成 `_` 也行）：

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 4m;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重载：

```bash
ln -sf /etc/nginx/sites-available/campus-match /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

浏览器打开：`http://你的公网IP`  
健康检查：`http://你的公网IP/api/health`

---

## 7.（可选）域名 + HTTPS

1. 在腾讯云 / 阿里云 / Namecheap 等买域名（约 50～100 元/年）。
2. DNS **A 记录** `@` → 服务器公网 IP（生效可能要几分钟～几小时）。
3. **上海等内地机房：** 用域名对外提供网站服务前，按腾讯云指引做 **ICP 备案**；未备案时域名可能被拦截，**IP 访问通常仍可用**。
4. 备案通过后，可用 Certbot / Caddy 上 HTTPS，并把 `.env` 的 `PUBLIC_URL` 改成 `https://你的域名`，再：

```bash
systemctl restart campus-match
```

未备案前：**继续用 `http://公网IP`，不要强上域名。**

---

## 8. 备份（很重要）

数据就是这一个文件：

```text
/opt/campus-match/instance/campus_match.db
```

每天拷走一份（示例：拷到自家电脑）：

```powershell
scp root@你的公网IP:/opt/campus-match/instance/campus_match.db D:\backup\campus_match_%date%.db
```

---

## 9. 以后更新代码

```bash
cd /opt/campus-match
source .venv/bin/activate
git pull
pip install -r requirements.txt
systemctl restart campus-match
```

---

## 费用一览（你这档）

| 项目 | 大约 |
|------|------|
| 轻量 2核2G 首年活动 | **68 元/年**（你看到的那档） |
| 域名（可选） | **50～100 元/年** |
| HTTPS 证书 | **0**（Let’s Encrypt） |
| 公开「网址」本身 | IP 免费；域名另计 |

---

## 10. 给其他学校定制（复用本仓库）

换校时一般只改配置，不必重写部署流程：

1. 在 `config.py` / 环境相关配置里扩展 **学校邮箱域名白名单**（`SCHOOL_DOMAINS`）
2. 问卷文案、首页地标/品牌如需本地化，改 `questionnaire.py`、`templates/`、`static/i18n.js`
3. **每所学校建议单独一台轻量机 + 单独数据库**（或至少不同 `instance/*.db`），避免用户池串校
4. 按本文第 3～6 步再部署一遍；`.env` 里换 `PUBLIC_URL`、邮件发件人、运营密钥

公测节奏与开关仍以 [`beta-launch.md`](beta-launch.md) 为准。

---

## 常见问题

**打不开网页？**  
查防火墙 80 是否放行、`systemctl status campus-match` / `nginx` 是否 active。

**邮件发不出？**  
先本机用真实学校邮箱测 QQ SMTP；查垃圾箱；确认 `MAIL_ENABLED=true`。

**还想用本机旧数据？**  
把本机 `instance/campus_match.db` 用 `scp` 上传覆盖云上同名文件后重启服务（先备份云上文件）。

**本机 tunnel 还要开吗？**  
上云后**不用**再开 `tunnel.py`；公开入口就是云 IP / 域名。
