# CampusMatch 技术架构文档

> v1.0 — 2026-07-27

## 系统全景

```
┌─────────────────────────────────────────────────────┐
│                    用户界面层                        │
│  index.html  │  questionnaire.html  │  matches.html  │
│  (注册+验证) │  (基本资料+32题问卷)  │  (匹配结果)    │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP + Session Cookie
┌──────────────────────▼──────────────────────────────┐
│                  Flask 应用层 (app.py)               │
│  /api/register  /api/verify  /api/questionnaire      │
│  /api/match     /api/matches  /api/me               │
└───┬──────────┬──────────┬───────────┬───────────────┘
    │          │          │           │
    ▼          ▼          ▼           ▼
┌────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
│ models │ │questionnaire│ │matcher │ │ email   │
│ (ORM)  │ │(特征向量)   │ │(相似度)│ │(SMTP)   │
└───┬────┘ └──────┘ └────┬─────┘ └────┬─────┘
    │                     │             │
    ▼                     ▼             ▼
┌─────────┐    ┌──────────────┐  ┌───────────┐
│ SQLite  │    │ 余弦相似度   │  │ QQ SMTP   │
│ campus_ │    │ 匈牙利算法   │  │ smtp.qq   │
│ match.db│    │ 一票否决     │  │ .com:587  │
└─────────┘    └──────────────┘  └───────────┘
```

## 数据流

### 注册 → 验证 → 问卷 → 匹配

```
1. POST /api/register {email}
   → 检查学校域名 → 生成6位验证码 → SMTP发送 → 返回 OK

2. POST /api/verify {email, token}
   → 验证码比对 + 过期检查(10分钟) → 设置 session → 返回 OK

3. POST /api/questionnaire {answers, important_qids}
   → 构建81维特征向量 → 保存到 users.feature_vector_json
   → 同时提取兴趣标签 → UserTag 表

4. POST /api/match → 获取同校异性用户
   → 余弦相似度 Top-N → 一票否决过滤
   → 生成兼容性分析 → 保存 Match 记录
   → SMTP 发送双方邮箱（微信号+匹配度+理由）
```

### 特征向量构建

```
32题问卷
  ├── Q1-Q24 (scale 1-5)  → 24维
  ├── Q25-Q32 (multi 选择) → 8题 × 平均8选项 = ~57维
  └── "对我很重要" 标记   → 对应维度权重 ×2
──────────────────────────────────
  合计 ≈ 81维归一化向量
```

## 数据库

### ER 图

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    User      │1──*│   UserTag    │    │    Match     │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ id (PK)      │    │ id (PK)      │    │ id (PK)      │
│ email (UQ)   │    │ user_id (FK) │    │ user1_id(FK) │──┐
│ school       │    │ tag          │    │ user2_id(FK) │──┤ 都指向
│ email_ver..  │    └──────────────┘    │ score        │  │ User
│ verif_token  │                        │ mode         │  │
│ name         │                        │ insight_json │  │
│ gender       │                        │ notified     │  │
│ wechat_id    │                        │ created_at   │  │
│ bio          │                        └──────────────┘  │
│ answers_json │                              │           │
│ feature_vec  │                         ┌────┘      ┌────┘
│ important_.. │                         ▼           ▼
│ created_at   │                  User.user1  User.user2
└──────────────┘
```

### 关键字段

| 表 | 字段 | 类型 | 说明 |
|----|------|------|------|
| users | answers_json | TEXT (JSON) | `{"1":3,"25":["科幻","悬疑"]}` |
| users | feature_vector_json | TEXT (JSON) | `[0.5, 0.2, ..., 0.8]` 81维 |
| users | important_qids_json | TEXT (JSON) | `[5,6,8]` 标记为重要的问题ID |
| matches | insight_json | TEXT (JSON) | `{"strengths":[...],"differences":[...]}` |

## 匹配引擎

### 实时模式 (realtime)

```
余弦相似度(user_vec, candidate_vec)
  = dot(A,B) / (||A|| × ||B||)

结果: Top-5 降序排列 (min_score=0.15)
```

### 批量模式 (batch)

```
匈牙利算法 (Kuhn-Munkres):
  1. 异性用户分成两组 (二部图)
  2. 构建兼容度矩阵 M[i][j] = cosine(女_i, 男_j)
  3. 转最小化问题: cost[i][j] = 1.0 - M[i][j]
  4. O(n³) 求解全局最优匹配
  5. 每人最多匹配一人

参考: SJTU Date 每周二晚9点执行
```

### 一票否决

标记为 dealbreaker 的 scale 题（包括婚姻观、孩子观、出轨观、抽烟），两人差距 ≥ 3 时直接跳过。

## 部署架构

```
┌────────────────────────────────┐
│  用户浏览器                     │
│  https://xxx.serveousercont…   │
└───────────┬────────────────────┘
            │ HTTPS
┌───────────▼────────────────────┐
│  serveo.net (SSH 反向隧道)     │
│  ssh -R 80:localhost:5000      │
└───────────┬────────────────────┘
            │ localhost:5000
┌───────────▼────────────────────┐
│  Flask (pythonw 无窗口)        │
│  127.0.0.1:5000                │
│  开发模式 (debug=True)          │
└────────────────────────────────┘
```

### 持久化运行 (Windows)

```
pythonw.exe app.py     ← 无窗口后台
bg_server.py           ← 一键启动器
tunnel.py              ← 隧道管理器

# 环境变量通过 .env 文件注入
# config.py 启动时自动加载
```

## 扩展点

| 位置 | 方式 | 成本 |
|------|------|------|
| 加学校 | config.py 一行域名 | 0 |
| 加题目 | questionnaire.py QUESTIONS 列表 append | 0 |
| 换匹配算法 | matcher.py 替换相似度函数 | 0 |
| 换数据库 | config.py 改 DATABASE_URL → PostgreSQL | 服务器 |
| 加支付 | app.py 新路由 + 微信 JSAPI | 微信商户申请 |
| 换域名 | 买域名 + Nginx 反代 | ~60元/年 |
| 换真服务器 | 阿里云轻量 2C4G + gunicorn | ~50元/月 |

## 安全考虑

- `.env` 文件在 `.gitignore` 中，SMTP 凭据不入库
- 验证码 10 分钟过期
- 邮箱域名白名单防止未授权学校注册
- Session-based 登录，无密码
- Flask debug mode 仅本地，生产部署需关闭
- serveo 隧道为临时方案，正式上线需自备域名+HTTPS
