# CampusMatch 校园恋爱匹配

基于深度问卷的校园恋爱匹配平台。学校邮箱注册 → 39题心理问卷 → 余弦相似度匹配 → 邮件通知结果。

**参考 SJTU Date (交大) / FDU Date (复旦) / MatchUs (浙大) 已验证模式。**

## 功能

| 模块 | 说明 |
|------|------|
| 学校邮箱验证 | 域名白名单识别学校，QQ SMTP 真实发送验证码 |
| 择偶取向 | 希望匹配男/女/不限；双向接受才进入候选池 |
| 深度问卷 | 39题五维度（核心价值观/生活习惯/情感风格/兴趣爱好/相处预期） |
| 特征向量 | 81维特征向量 + "对我很重要" 权重翻倍 |
| 余弦相似度 | 实时 Top-N 匹配 + 匈牙利算法全局最优匹配（备用） |
| 一票否决 | 出轨观/孩子观/抽烟 等硬过滤 |
| 匹配反馈 | 邮件通知双方，含匹配度 + 共同点 + 差异分析（页面为准） |
| 运营节奏 | 每周新建匹配额度 + 冷却；周二批量匹配任务 |
| 爬虫模块 | 多源搜索策略，自动提取学校兴趣标签（供冷启动） |
| 公网可访问 | serveo 隧道，零成本公网部署 |

## 快速开始

```bash
# 1. 安装依赖
cd campus-match
pip install -r requirements.txt

# 2. 配置邮件（可选）
cp .env.example .env
# 编辑 .env 填入 QQ 邮箱 SMTP 授权码

# 3. 初始化种子数据
python seed.py

# 4. 启动
python app.py
# → http://127.0.0.1:5000
```

## 公网部署

```bash
# 启动公网隧道（零成本，立即可用）
python tunnel.py
# → 获得 https://xxx.serveousercontent.com 公网地址
```

## 文档

| 文档 | 用途 |
|------|------|
| [`docs/beta-launch.md`](docs/beta-launch.md) | 熟人公测 checklist、推荐 `.env`、冒烟测试 |
| [`docs/deploy-tencent-lighthouse.md`](docs/deploy-tencent-lighthouse.md) | 腾讯云轻量机部署（含给其他学校复用要点） |
| [`docs/mvp-roadmap.md`](docs/mvp-roadmap.md) | MVP 路线图 |
| [`CHANGELOG.md`](CHANGELOG.md) | 版本变更记录 |

换校定制：改 `config.py` 里学校域名白名单，建议每校独立部署/独立数据库；步骤见部署文档第 10 节。

## 项目结构

```
campus-match/
├── app.py              # Flask 主应用 (481行)
├── config.py           # 学校域名 + 环境变量 (74行)
├── models.py           # SQLAlchemy 数据模型 (126行)
├── questionnaire.py    # 32题定义 + 特征向量化 (446行)
├── matcher.py          # 余弦相似度 + 匈牙利算法 (230行)
├── email_service.py    # SMTP 邮件 + HTML 模板 (143行)
├── crawler.py          # 多源搜索 + 标签提取 (235行)
├── seed.py             # 种子数据生成器
├── batch_job.py        # 每周批量匹配任务
├── bg_server.py        # Windows 后台启动器
├── tunnel.py           # serveo 公网隧道管理器
├── requirements.txt
├── .env.example        # 环境变量模板
├── templates/          # Jinja2 页面 (6个)
│   ├── index.html      # 注册+验证 (同一页)
│   ├── questionnaire.html  # 基本资料+32题问卷
│   ├── matches.html    # 匹配结果+历史
│   ├── verify.html     # 验证页（备用）
│   ├── profile.html    # 旧版资料页（备用）
│   └── base.html       # 母版框架
└── static/style.css    # CSS (183行)
```

## 支持学校

| 阶段 | 学校 | 状态 |
|------|------|------|
| Phase 1 | 澳门大学 | ✅ |
| | 澳门科技大学 | ✅ |
| | 澳门理工大学 | ✅ |
| | 澳门旅游大学 | ✅ |
| | 澳门城市大学 | ✅ |
| Phase 2 | 香港大学 | 🔜 |
| | 香港中文大学 | 🔜 |
| | 香港科技大学 | 🔜 |
| Phase 3 | 深圳/珠海高校 | 📋 |

加一所学校只需在 `config.py` 的 `SCHOOL_DOMAINS` 加一行域名。

## 匹配算法

```
用户问卷答案 → 81维特征向量 → 余弦相似度 → Top-N排序
                                    ↓
                          一票否决过滤（出轨/孩子/抽烟）
                                    ↓
                          邮件通知双方（微信号+匹配度+理由）
```

备选模式：匈牙利算法全局最优匹配（批量模式，每人只匹配一个人）。

## 技术栈

- **后端**: Python / Flask / SQLAlchemy / SQLite
- **前端**: Jinja2 / Vanilla JS / CSS
- **邮件**: QQ SMTP (smtplib)
- **公网**: serveo SSH 隧道
- **部署**: pythonw 无窗口后台运行

## 参考资料

- [SJTU Date / CampusDate](https://trycampusdate.com) — 交大，65题 + Gale-Shapley，每周二匹配
- [FDU Date](https://trycampusdate.com) — 复旦，同上平台
- [MatchUs](https://matchus.cc) — 浙大起步，全国600+校，41万用户
- [斯坦福 Date Drop](https://www.stanforddaily.com/2021/02/14/date-drop-stanford-matchmaking/) — 灵感来源

## License

Private repository. All rights reserved.
