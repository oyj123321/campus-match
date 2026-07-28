# CampusMatch 熟人公测上线 Checklist

> 目标：同校 20～50 人小范围真跑一周。不是对外广告公测。  
> 功能已够用；下面全是**运维与安全**，漏一项就容易翻车。

---

## 0. 一句话决策

| 阶段 | 何时进入 | 关键开关 |
|------|----------|----------|
| **熟人冷启动** | 现在 | `INSTANT_MATCH_ENABLED=true`，保留「提前揭晓」 |
| **仪式周** | 预约人数 ≥15～20 | 仍可即时；主推周二揭晓 |
| **对外公测** | 邮件/域名/删号反馈都稳 | 可考虑 `INSTANT_MATCH_ENABLED=false` |

---

## 1. 上线前必做（全部勾完再发链接）

### A. 安全与进程

- [ ] `FLASK_DEBUG=false`（禁止把验证码以 debug 方式乱暴露；关闭自动重载）
- [ ] `SECRET_KEY` 换成足够长的随机串（勿用仓库默认值）
- [ ] `ADMIN_SECRET` 设好；不要发给用户
- [ ] 确认进程只监听需要的地址；有公网反代时再暴露 80/443
- [ ] 健康检查：`GET /api/health` 返回正常

生成密钥示例（本机执行一次）：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### B. 邮件（公测命门）

- [ ] QQ 邮箱开启 SMTP，拿到**授权码**（不是 QQ 密码）
- [ ] `.env`：`MAIL_ENABLED=true` + `MAIL_USERNAME` / `MAIL_PASSWORD`
- [ ] 用**真实学校邮箱**自测：注册验证码能收到
- [ ] 完成问卷后点匹配（或预约后跑批量），匹配通知能收到
- [ ] 垃圾箱也查一遍；提醒同学看 Junk

### C. 数据库与演示数据

- [ ] **公测库不要留 Alice/Bob 等种子号**（假邮箱会进池、邮件 550、污染体验）
- [ ] 新库启动：不要跑 `seed.py`；或单独用开发库测种子
- [ ] 备份：定期复制 `instance/campus_match.db`（或你配置的 `DATABASE_URL`）

清种子（仅当你确认库里只有演示号时用；有真人后勿盲删）：

```bash
# 开发机示例：删库重建（会清空所有用户！）
# 先备份再操作
# del instance\campus_match.db   # Windows
# python -c "from app import init_db; init_db()"
```

### D. 公网地址

- [ ] 设好 `PUBLIC_URL`（与浏览器实际打开的一致，含 https）
- [ ] serveo 仅作临时：`python tunnel.py`；断线要重开并更新 URL
- [ ] 更稳：云主机 + Nginx/Caddy HTTPS，再把 `PUBLIC_URL` 指过去

### E. 匹配节奏（推荐冷启动配置）

- [ ] `MATCH_MODE=one_to_one`
- [ ] `MATCH_WEEKLY_NEW_LIMIT=1`
- [ ] `MATCH_COOLDOWN_HOURS=12`（可按情况改成 6）
- [ ] `REVEAL_REQUIRE_OPT_IN=true`
- [ ] `INSTANT_MATCH_ENABLED=true`（人少必须开）
- [ ] `CROSS_SCHOOL_MATCHING_ENABLED=true` 或先 `false`（第一周建议只开本校，降低预期管理成本）
- [ ] 周二揭晓：要么 `BATCH_SCHEDULER_ENABLED=true`，要么你手动：

```bash
python batch_job.py --now
```

### F. 产品文案 / 同学须知（发群前）

- [ ] 说明：一对一、每周额度、微信仅配对成功可见
- [ ] 说明：可搜昵称拉黑；跨校需双方都开
- [ ] 说明：账号删除暂联系运营（页脚邮箱）
- [ ] 告知支持学校邮箱域名列表（澳大 / 科大等）

---

## 2. 推荐 `.env`（熟人公测档）

复制为项目根目录 `.env` 后填空。**不要提交 `.env` 到 Git。**

```env
# === 安全 ===
SECRET_KEY=这里粘贴上面生成的随机串
FLASK_DEBUG=false
ADMIN_SECRET=再生成一串只给你自己用

# === 邮件 ===
MAIL_ENABLED=true
MAIL_SERVER=smtp.qq.com
MAIL_PORT=587
MAIL_USERNAME=你的QQ号@qq.com
MAIL_PASSWORD=SMTP授权码
MAIL_FROM=你的QQ号@qq.com

# === 公网（与真实访问 URL 一致）===
PUBLIC_URL=https://你的域名或serveo地址

# === 匹配 / 揭晓（冷启动）===
MATCH_MODE=one_to_one
MATCH_WEEKLY_NEW_LIMIT=1
MATCH_COOLDOWN_HOURS=12
MATCH_MIN_SCORE=0.15
REVEAL_REQUIRE_OPT_IN=true
INSTANT_MATCH_ENABLED=true
CROSS_SCHOOL_MATCHING_ENABLED=false
BATCH_MATCH_DAY=1
BATCH_MATCH_HOUR=21
BATCH_SCHEDULER_ENABLED=true

# === 防刷 ===
REGISTER_RATE_LIMIT=5
REGISTER_RATE_WINDOW=3600
```

人够、仪式感优先时，把这两行改掉即可：

```env
INSTANT_MATCH_ENABLED=false
CROSS_SCHOOL_MATCHING_ENABLED=true
```

---

## 3. 发链接当天：10 分钟冒烟

用**两个真实学校邮箱**（可找朋友）：

1. 注册 → 收验证码 → 登录  
2. 填资料 + 答完问卷 → 提交  
3. 「预约本周匹配」能点  
4. （冷启动）「提前揭晓」能出一人，页上有说明书 + 破冰 + 微信  
5. 邮件通知至少自己这边成功  
6. 搜昵称拉黑对方 → 再匹配不应再配到  
7. `/api/health` 正常  

任一步失败：**先别拉群。**

---

## 4. 公测一周盯什么

| 指标 | 怎么看 | 红线 |
|------|--------|------|
| 验证通过人数 | 首页统计 / 库表 | 验证码大量进垃圾箱 → 换发信或改文案 |
| 问卷完成率 | 有邮箱 vs 有向量 | &lt;50% → 问卷太长或中途掉线 |
| 有效配对 | `matches.active` | 池子太小 → 继续即时 + 拉人 |
| 邮件失败 | 匹配页邮件状态 | 真人邮箱失败 → 立刻查 SMTP |
| 投诉 | 微信被误曝光 / 撞名拉黑 | 立刻修，必要时暂停匹配 |

---

## 5. 明确还没做、但可开测

- 自助删号（现在联系运营）
- 更正式隐私政策页
- 老用户「请重交问卷」强提示
- 分享裂变海报
- serveo 稳定性（应用层已就绪，管道另说）

这些不挡 **20～50 人熟人测**；挡的是「全网公开招生」。

---

## 6. 启动命令备忘

```bash
# 安装
pip install -r requirements.txt

# 配好 .env 后
python -c "from app import init_db; init_db()"

# 前台跑（简易）
python app.py

# 需要公网隧道时另开终端
python tunnel.py

# 手动揭晓一轮
python batch_job.py --now
```

Windows 也可用 `bg_server.py` 后台起服务（若你平时这么用）。

---

## 7. 对外一句话（可直接转发）

> CampusMatch 熟人内测：学校邮箱验证身份 → 约 40 题问卷 → 每周一对一匹配，并给相处说明书和破冰话题。微信只在配对成功后互见。需要删号或反馈请联系运营邮箱。
