# CampusMatch 日常维护与排障

面向：网站上线后你自己当「唯一运维」。  
数据默认在一台机器上的 SQLite 文件里，**没有单独的数据库服务器**。

---

## 1. 日常维护（建议形成习惯）

### 私有运营后台

在服务器 `.env` 配置足够长且只由你保存的 `ADMIN_SECRET`，重启服务后打开：

```text
https://campusmatch.com.cn/admin
```

输入 `ADMIN_SECRET` 后可查看注册、匹配池、近 7 日匿名流量、系统状态和邮件状态。管理员会话 8 小时后失效。流量从本功能上线后开始统计，不能补回历史数据；后台不会显示完整学生邮箱、联系方式、问卷答案或验证码。

本地邮件保护上限可在 `.env` 调整；阿里云初始日额度为 2000 时配置：

```text
MAIL_DAILY_LIMIT=2000
```

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
# 邮件额度保护与台账

阿里云首次切换：拉取代码后运行 `bash scripts/configure-aliyun-mail.sh`，在隐藏输入提示中填写 SMTP 密码。脚本会先备份 `.env`，再写入华东 1 的 465 SSL 配置。重启前可运行 `python scripts/test_mail_delivery.py --to 你的测试邮箱`；确认收到后执行 `sudo systemctl restart campus-match`。回退时恢复脚本打印的 `.env.backup.*` 文件并重启。

- Resend 与阿里云 DirectMail 发送统一经过本地保护：最近 24 小时最多 `MAIL_DAILY_LIMIT` 次发送尝试。Resend 未设置时兼容 `RESEND_DAILY_LIMIT`；阿里云默认 2000。70% 用量在管理员后台提醒，85% 起暂停非验证码邮件，剩余容量供验证码使用。普通 QQ SMTP 暂不使用这套限额。
- 这是保守的滚动 24 小时上限，不是服务商官方重置周期。失败和发送结果不明的尝试也占用预留。其他程序共用账号的发信、升级前已发邮件不在本地台账内；首次上线应核对官方用量，必要时临时降低 `MAIL_DAILY_LIMIT`，满 24 小时后恢复。
- `instance/mail_operations.db` 保存台账和队列，必须随数据库备份并保持可写；不要删除以“清零”。多进程必须共享该文件，多台服务器需改用共享额度服务后才能启用。
- 台账只记录收件域名、邮件类型和提交状态；不保存验证码、邮件正文或服务商原始错误。服务商接受不代表到达收件箱，隔离区情况仍需通过 Resend 与收件学校核对。
- 成功匹配的通知在额度不足时排队，每分钟检查，每轮最多 10 封，仍遵守 85% 阈值。补发是提醒登录查看当前结果，不包含旧联系方式；7 天后过期，已删除或未验证的账号不补发。排队不是已发送，原有匹配的 notified 字段不会因入队被标记为成功。
- 验证码从不排队；发送失败返回 503，不暴露验证码，新生成但发送失败的码会清除。问卷提醒、未匹配通知不入队，原调用方可稍后重试；回访仅在双方提交成功后标记完成，同内容 7 天内成功发送会去重。
- 网络结果不明的队列不会自动重发，后台显示异常，避免重复投递。后台提醒需打开页面查看，本次未配置外部推送渠道。
- 当前 `python app.py` 启动方式会启动队列线程。若改为 WSGI 部署，需要单独运行初始化和队列工作进程，不能只导入 `app`。
