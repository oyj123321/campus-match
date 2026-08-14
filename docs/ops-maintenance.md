# CampusMatch 日常维护与排障

面向：网站上线后你自己当「唯一运维」。  
数据默认在一台机器上的 SQLite 文件里，**没有单独的数据库服务器**。

---

## 1. 日常维护（建议形成习惯）

| 频率 | 做什么 |
|------|--------|
| **每天 / 隔天** | 备份 `instance/campus_match.db`（拷到自己电脑或网盘） |
| **每周** | 打开网站点一遍注册页；看 `/api/health`；确认邮件还能发 |
| **匹配日（如周二）** | 确认 `BATCH_SCHEDULER_ENABLED=true` 已开；或手动 `python batch_job.py --now` |
| **有人投诉时** | 先备份库，再查用户/匹配记录；必要时帮人删号（见下） |
| **改代码后** | **先本机测** → push → 云上 `git pull` → 装依赖（若有）→ `systemctl restart campus-match` → 打开首页/注册冒烟。**禁止不测直推正式站。** 详见 [`beta-launch.md`](beta-launch.md)「改代码：禁止直推正式站」 |

云服务器上常用命令：

```bash
# 服务是否在跑
systemctl status campus-match
systemctl status nginx

# 看最近日志（报错会在这里）
journalctl -u campus-match -n 100 --no-pager

# 健康检查
curl -s http://127.0.0.1:5000/api/health

# 手动跑一轮批量匹配（需在项目目录、venv 里）
cd /opt/campus-match && source .venv/bin/activate
python batch_job.py --now
```

带密钥触发批量（本机或服务器均可，勿泄露密钥）：

```bash
curl -X POST http://你的地址/api/admin/batch-run \
  -H "Content-Type: application/json" \
  -d '{"secret":"你的ADMIN_SECRET"}'
```

催填「已验证但问卷未完成」用户（默认只预览，不会发信）：

```bash
cd /opt/campus-match && source .venv/bin/activate
python scripts/nudge_incomplete.py                 # dry-run
python scripts/nudge_incomplete.py --send          # 真正发信
python scripts/nudge_incomplete.py --email xx@um.edu.mo --send
# 或 API：POST /api/admin/nudge-incomplete  body: {"secret":"...","send":true,"days":3}
```

---

## 2. 数据库在哪、怎么看每个人的数据

### 文件位置

| 环境 | 路径 |
|------|------|
| 本机开发 | `校园项目目录/instance/campus_match.db` |
| 腾讯云部署 | `/opt/campus-match/instance/campus_match.db` |

主要表：

- `users` — 每人一行：邮箱、昵称、性别、取向、微信、学校、问卷 JSON、是否验证等  
- `matches` — 配对记录：双方 id、分数（内部用）、是否有效 `active`  
- `blocklist` — 拉黑  
- `user_tags` — 标签（若有）

### 方法 A：图形界面（推荐新手）

1. 把 `.db` 文件拷到自己电脑（先备份再拷）  
2. 安装免费工具：**[DB Browser for SQLite](https://sqlitebrowser.org/)**（或 VS Code 插件 SQLite Viewer）  
3. 打开文件 → 「浏览数据」→ 选表 `users` / `matches`

### 方法 B：命令行（服务器上）

```bash
apt install -y sqlite3   # 若未安装
cd /opt/campus-match
sqlite3 instance/campus_match.db
```

进入后常用 SQL：

```sql
-- 有多少人、多少已验证
SELECT COUNT(*) AS total FROM users;
SELECT COUNT(*) AS verified FROM users WHERE email_verified = 1;

-- 列表（别对外泄露微信）
SELECT id, school, email, name, gender, looking_for, email_verified, wechat_id, created_at
FROM users
ORDER BY id DESC
LIMIT 50;

-- 某人详情（问卷在 answers_json 里）
SELECT id, email, name, answers_json, important_qids_json, opt_in_week, allow_cross_school
FROM users
WHERE email = '某人@um.edu.mo';

-- 当前有效配对
SELECT m.id, m.user1_id, m.user2_id, m.score, m.active, m.created_at,
       u1.email AS email1, u2.email AS email2
FROM matches m
JOIN users u1 ON u1.id = m.user1_id
JOIN users u2 ON u2.id = m.user2_id
WHERE m.active = 1
ORDER BY m.created_at DESC;

.quit
```

### 方法 C：Python 一眼看（在项目目录、venv 里）

```bash
cd /opt/campus-match && source .venv/bin/activate
python - <<'PY'
from app import app, init_db
from models import User, Match
init_db()
with app.app_context():
    for u in User.query.order_by(User.id.desc()).limit(20):
        print(u.id, u.school, u.email, u.name, u.gender,
              "verified" if u.email_verified else "pending",
              "问卷" if u.feature_vector else "未完成")
PY
```

**隐私：** 微信号、邮箱仅你作为运营可看；不要截图发群，不要把整个 `.db` 传给不相关的人。

### 帮人删号（示例）

先备份 `.db`，再在 sqlite 里（把 id 换成真实用户）：

```sql
-- 查看
SELECT id, email, name FROM users WHERE email = 'xxx@um.edu.mo';

-- 删其配对与拉黑后删用户（按实际 id）
DELETE FROM matches WHERE user1_id = 123 OR user2_id = 123;
DELETE FROM blocklist WHERE user_id = 123 OR blocked_user_id = 123;
DELETE FROM user_tags WHERE user_id = 123;
DELETE FROM users WHERE id = 123;
```

---

## 3. 常见问题与处理

| 现象 | 可能原因 | 你怎么做 |
|------|----------|----------|
| 网站打不开 | 服务挂了 / 服务器欠费关机 / Nginx 挂了 | `systemctl status campus-match nginx`；腾讯云看实例是否运行；`systemctl restart ...` |
| 只有你能开、同学不能 | 防火墙没放行 80/443；只绑了 127.0.0.1 却没反代 | 轻量防火墙放行 80；确认 Nginx 在监听 80 |
| 验证码收不到 | SMTP 配错、进垃圾箱、QQ 授权码失效、学校邮箱拦截 | 查 `.env` 邮件配置；垃圾箱；用自己学校邮箱自测；看 `journalctl` 报错 |
| 匹配页空白 / 没人 | 池子太小、本周额度用尽、取向对不上、跨校关了 | 看 `users` 里已完成问卷人数；提醒预约/下周再试；冷启动保持即时匹配开启 |
| 「本周额度已用完」 | 双向每周 1 次，正常 | 等下周；或查是否误配多次 |
| 匹配通知邮件失败 | 对方假邮箱 / SMTP 限流 | 以**网页结果为准**；种子号本来就会失败 |
| 改问卷后老用户配不上 | 特征向量维度变化 | 让老用户重新提交问卷；见路线图「重交问卷」 |
| 磁盘满 / 异常慢 | 日志过大、备份堆太多 | 清旧 journal、挪走旧备份；机器仍 2G 内存别同机跑太多东西 |
| 误删数据 / 库损坏 | 没备份或写坏 | 用前一天的 `.db` 备份覆盖后重启服务 |
| 域名打不开（上海） | 未 ICP 备案 | 先用 `http://公网IP`；备案完成再上域名 HTTPS |
| 被人刷注册 | 限流不够或密钥泄露 | 已有注册限流；必要时关公网、加强 `REGISTER_RATE_LIMIT`；轮换 `SECRET_KEY` 仅影响登录态 |

---

## 4. 安全底线（维护时永远记住）

- `.env`、`ADMIN_SECRET`、邮箱授权码、`.db` 备份：**不要提交 Git、不要发群**
- `FLASK_DEBUG=false`（生产）
- 定期备份数据库；大改动前先拷一份再操作
- 投诉「误曝光微信 / 被骚扰」：协助拉黑、必要时删号或暂停匹配

---

## 5. 和「换校定制」的关系

每所学校建议：**独立云主机或至少独立 `.db`**，避免用户池串在一起。  
部署仍按 [`deploy-tencent-lighthouse.md`](deploy-tencent-lighthouse.md)；公测节奏按 [`beta-launch.md`](beta-launch.md)。
