# CampusMatch 熟人公测上线 Checklist

> 目标：同校 20～50 人小范围真跑一周。不是对外广告公测。  
> 功能已够用；下面全是**运维与安全**，漏一项就容易翻车。

---

## ⚠️ 大范围公测硬门槛（2026-07-29 记录）

**现在阶段 = 熟人内测，还不是大范围公测。**  
下面任一项未过，就不要广而告之、不要发全校群：

| # | 硬门槛 | 现状（记录时） | 不过会怎样 |
|---|--------|----------------|------------|
| 1 | **学校邮箱稳定收到验证码/匹配信** | QQ SMTP 能发成功，但澳大侧常被微软隔离 | 大量人卡在注册 |
| 2 | **域名 + HTTPS** | 仅公网 IP | 难传播、不专业、部分环境不信任 |
| 3 | **内地机域名 ICP 备案**（若继续用内地轻量） | 未办 | 正式挂域名可能被拦 |
| 4 | **更稳发信**（企业邮 / Resend 等） | 个人 QQ | 隔离率高、扩量必炸 |
| 5 | **自助删号 / 明确投诉通道** | 基本靠运营人工 | 人一多应付不过来 |
| 6 | **移动端排版可用** | 长期偏 PC，手机端已见错位 | 多数同学用手机打开会劝退 |
| 7 | **改动先自测再上正式站** | 见下一节 | 易把正式库/正式体验弄挂 |

熟人 20～50 人：硬门槛可边跑边补。  
**对外公测 / 大群拉人：上表尽量勾完。**

### 紧急优先级（下一步产品）

1. **移动端优化**（首页 / 问卷 / 匹配结果在窄屏下可读、可点、不挤）  
2. 发信投递（隔离 → 企业邮或专业 SMTP）  
3. 域名 + HTTPS（+ 备案流程启动）

---

## 改代码：禁止直推正式站

正式站 = 腾讯云 `http://公网IP`（以后是域名），上面有**真人数据**。

| 环境 | 用途 | 怎么用 |
|------|------|--------|
| **本机** | 日常改功能、改 UI | `python app.py` → `http://127.0.0.1:5000`；可用 `cmtest01@um.edu.mo` 等内测号免验证码 |
| **正式云** | 只给同学用的稳定版 | 本机测通 → 提交 GitHub → 服务器 `git pull` → `systemctl restart` |

**纪律：**

1. 新功能 / 改样式 / 改匹配逻辑 → **先在本机测完**（含手机浏览器或窄窗模拟）  
2. 再 `commit` / `push`  
3. 最后才上云 `git pull` + 重启  
4. **不要**改完代码不测就直接在服务器上改，或 pull 完不冒烟就发群  

内测号（免真邮件）：本地名为 `cmtest` / `beta` / `test` + 数字，如 `cmtest01@um.edu.mo`。注册后直接进问卷。

本机拉正式库备份（只读排查用）：见 [`scripts/README-backup.md`](../scripts/README-backup.md)。**不要把本机实验库覆盖到云上**，除非你明确要还原灾备。

### 本机 vs 云：怎么分清、为何「一改就刷新变了」

本地改代码 **不会** 自动同步到云。两边是两份文件：

| 你改的是 | 磁盘位置 | 浏览器应打开 |
|----------|----------|--------------|
| Cursor / 本机项目 | `D:\claude\projects\campus-match\...` | **仅** `http://127.0.0.1:5000` |
| 云上正式版 | 服务器 `/opt/campus-match/...` | **仅** `http://公网IP`（如 `106.53.82.216`） |

**若你一改代码、刷新网页立刻看到新效果：**  
多半地址栏是 `127.0.0.1` / `localhost`（本机 Flask 在跑，Debug 还会自动重载）。  
这是**正常的本机开发体验**，不是云被自动更新了。

**自检（推荐做一次）：**

1. 本机改一句首页文案并保存  
2. 刷新 `http://127.0.0.1:5000` → 应看到新文案  
3. 刷新 `http://公网IP` → 应仍是旧文案  
4. 只有服务器执行 `git pull` + `systemctl restart campus-match` 后，云才会变成新版  

**给同学的链接永远发云地址，不要发 127.0.0.1**（别人电脑打不开你的本机）。

### 标准发布口令（抄着用）

本机测通后：

```powershell
# 本机
cd D:\claude\projects\campus-match
git add ...
git commit -m "说明这次改了什么"
git push
```

服务器（TAT / SSH）：

```bash
cd /opt/campus-match
git pull
sudo systemctl restart campus-match
curl -s http://127.0.0.1:5000/api/health
```

再用手机/电脑打开**公网 IP** 冒烟一遍，再告诉同学「已更新」。

---

## 本周最小上线（按顺序做）

| 步 | 做什么 | 建议 |
|----|--------|------|
| 1 | **云主机** | 轻量即可：2 核 / 2G 内存 / 40G 盘，Ubuntu 22.04。国内可选腾讯云轻量 / 阿里云；港澳或海外可选 Vultr / Bandwagon。月费大约几十元起。 |
| 2 | **域名 + HTTPS** | 买一个短域名，DNS A 记录指到服务器 IP；装 **Caddy**（自动 HTTPS）或 Nginx + Let’s Encrypt。`PUBLIC_URL` 必须与浏览器地址一致。 |
| 3 | **部署本项目** | 逐步命令见 **[`deploy-tencent-lighthouse.md`](deploy-tencent-lighthouse.md)**（针对腾讯云 68 元轻量机）。概要：`git clone` → `.env` → `init_db` → systemd + Nginx。**不要跑 seed.py 进公测库。** |
| 4 | **专用发信** | 先用 QQ 邮箱 SMTP 授权码也能测；更稳：企业邮 / Resend / SendGrid。发件名建议像 `CampusMatch 通知`，并自测学校邮箱收件箱 + 垃圾箱。 |
| 5 | **备份** | 每天复制一次 `instance/campus_match.db`（或云盘定时任务）。硬盘坏了没备份等于从零开始。 |
| 6 | **冒烟后再拉群** | 走完下面「发链接当天：10 分钟冒烟」；失败先别发链接。 |

临时方案（本周人极少、先验证产品）：可继续 `python tunnel.py`（serveo），但 URL 会变、易断，**只适合自己测，不适合正式拉群。**

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

- [ ] 说明：一对一、每周额度（双向各限一次）、微信仅配对成功可见
- [ ] 说明：结果只给契合点与破冰话题，**不展示匹配度分数**
- [ ] 说明：可搜昵称拉黑；跨校需双方都开（若本周关闭跨校则写明「仅本校」）
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
# MATCH_MIN_SCORE=0.15
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
4. （冷启动）「提前揭晓」能出一人，页上有契合点 + 破冰 + 微信（**无百分比分数**）  
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

> CampusMatch 熟人内测：学校邮箱验证身份 → 约 39 题问卷 → 每周一对一匹配，只给契合点与破冰话题（不晒分数）。微信只在配对成功后互见。需要删号或反馈请联系运营邮箱。
