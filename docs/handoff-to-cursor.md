# CampusMatch 项目交接文档

> 给 Cursor。这是 Claude 写的项目全貌 + 你接下来要做的事。

---

## 项目背景

**CampusMatch — 校园恋爱匹配平台。** 参考 SJTU Date (交大, 65题+匈牙利算法, 7天7000人) 和 MatchUs (浙大, 70万用户, 19.9元/次) 的已验证模式。目前定位**澳门大学起步 → 澳门高校 → 香港 → 大湾区唯一跨境校园恋爱匹配平台**。

**三天走了从零到 v1.9.9，41 个 commit。技术栈：** Python/Flask/SQLAlchemy/SQLite + Jinja2/Vanilla JS/CSS + QQ SMTP 真实邮件 + serveo 公网隧道。

---

## 商业模式

| | 免费 | VIP (¥9.9/月) |
|--|------|--------------|
| 基础匹配（余弦+匈牙利） | ✅ | ✅ |
| 反馈闭环 | ✅ | ✅ |
| LLM 陪审团（个性化相处说明书） | — | ✅ |
| 动态破冰话题 | — | ✅ |
| 问卷真实性检测 | — | ✅ |
| 自然语言理想型输入 | — | ✅ |

详见 `docs/multi-agent-vip-features.md`

---

## 用户冷启动策略（现在最大的问题）

交大怎么火的：没推广。产品自己炸了。"系统发对象"这个概念自传播。媒体主动报道。

**我们怎么冷启动：**
- 交大验证过的事：**女生来了，男生自然会来。** 他们首轮女生成功率69%、男生39%。
- **第一步：恋爱人格报告。** 女生填完问卷立刻得到人格分析（"守护者型 ESCP"），不需要等匹配、不为了找男友。填问卷的回报从"可能匹配到一个人"变成"立刻看到自己的恋爱人格"——社交货币，可截图发朋友圈。女生发了朋友圈，男生就来了。
- **第二步：5个女同学冷启动。** 不用说"帮我推广"，说"帮我校对一个AI产品"。她们填完看到人格报告自然会截图分享。
- **第三步：种子数据清理。** 库里 9 个假人必须清掉（`seed.py` 有 `--refresh` 但只刷新种子假人），真人注册后才算数。

---

## 当前项目状态

### 代码结构

```
campus-match/
├── app.py              # Flask 主应用 (~900行)
├── config.py           # 学校域名 + 所有环境变量
├── models.py           # User/UserTag/Match/Blocklist
├── questionnaire.py    # 39题定义 + 特征向量化 + 破冰生成
├── matcher.py          # 余弦相似度 + 匈牙利算法
├── personality.py      # ⚠️ 还不存在！你要创建的
├── email_service.py    # SMTP 邮件
├── batch_job.py        # 每周批量匹配任务
├── crawler.py          # 公开信息爬取策略
├── seed.py             # 种子数据（9个假人）
├── tunnel.py           # serveo 公网隧道
├── templates/          # 6个Jinja2页面
├── static/             # CSS + i18n.js (四语言)
├── docs/               # 11份文档
│   ├── personality-report-spec.md  # ← 你的任务书
│   ├── multi-agent-vip-features.md # VIP功能设计
│   ├── competitor-research.md      # 竞品调研
│   ├── mvp-roadmap.md             # 路线图
│   └── ...
└── .env                # QQ邮箱 SMTP 凭据（不入库）
```

### 已有功能

- ✅ 学校邮箱注册（域名白名单）→ QQ SMTP 真实验证码
- ✅ 39题五维问卷（价值观/生活习惯/情感风格/兴趣/相处预期）→ 126维特征向量
- ✅ 余弦相似度实时匹配 + 匈牙利全局最优（批量模式下周二晚 9 点）
- ✅ 一票否决（出轨/孩子/婚姻/吸烟差异过大直接跳过）
- ✅ "对我很重要"权重翻倍
- ✅ 择偶取向（男/女/不限）+ 跨校开关
- ✅ 黑名单（搜昵称拉黑，双向生效）
- ✅ 四周额度+冷却机制（每人每周最多 1 次匹配）
- ✅ 匹配后互换学校邮箱 + 附加联系方式
- ✅ 相处说明书 + 破冰话题（⚠️ 当前是模板风格，v1.9.1 revert 了军师版本）
- ✅ 没配上也会发邮件通知
- ✅ Q40 自由留言（"留给TA的话"）
- ✅ 四语言（简/繁/英/葡）+ 大湾区天际线 UI
- ✅ 匹配分数不对用户展示（只展示契合点 + 破冰）
- ✅ 内测号免验证（`cmtest01@um.edu.mo` 等）
- ✅ serveo 公网隧道 + .env 环境变量管理
- ✅ 腾讯云部署指南 + 运维手册 + 备份脚本
- ✅ 多 Agent VIP 功能设计文档
- ✅ 竞品深度调研报告
- ✅ 完整的 README + ARCHITECTURE + CHANGELOG

### 已知的待改进项

- 🔧 破冰话题目前是模板风格（"你们对xxx看法几乎一样——可以聊聊：xxx"）。我和 Claude 讨论过要做"军师"风格——像舍友帮朋友出主意那种语气。方向定了但没落地，见 `CHANGELOG.md` v1.9.0→v1.9.1 的 revert 历史
- 🔧 种子数据 9 个假人还在库里，上线前要清掉
- 🔧 serveo 域名不稳定，定期断开。正式上线前需买域名+腾讯云服务器
- 🔧 匹配页预约/跨校按钮的状态判断逻辑分散在 JS 和 API 之间

---

## 你现在要做的：恋爱人格报告

**完整技术规格** 在 `docs/personality-report-spec.md`，以下是概要。

### 核心逻辑

填完 39 题问卷 → 立刻生成恋爱人格分析 → 前端弹报告卡片 → 可截图分享。

**4 维度人格系统**（每维 0-100 分，≥50 取高端、<50 取低端）：

| 维度 | 来源题 | 高分端 | 低分端 |
|------|-------|--------|--------|
| 情感表达 | Q18/Q22/Q21 | E 外放热烈 | I 内敛含蓄 |
| 生活节奏 | Q9/Q12/Q16/Q29 | S 结构秩序 | F 随性自由 |
| 关系边界 | Q7/Q19/Q20 | C 亲密融合 | O 独立自主 |
| 风险态度 | Q4/Q5/Q6 | P 稳健保守 | A 开放冒险 |

组合成 4 字母代码（如"ESCP"）+ 中文名称（如"守护者型"）。

### 文件改动

```
新增 personality.py          ← 核心：维度打分 + 人格分类 + 报告生成
修改 questionnaire.py        ← 特征向量化后调用 personality，写 mbti_json 字段
修改 app.py                  ← POST /api/questionnaire 返回里加 personality 字段
修改 templates/questionnaire.html  ← 提交后弹报告卡片（不立刻跳匹配页）
修改 static/style.css         ← 报告卡片样式
修改 static/i18n.js           ← 报告相关翻译 key
```

### 关键注意事项

1. **`mbti_json` 字段已存在于 `models.py:50`**，不需要新建表
2. 报告中不要出现百分比排名（"前X%"）——库里目前只有假数据，等 50+ 真人再补
3. 分享用复制文案，不做图片生成（MVP 阶段太重的功能后置）
4. 文档里的 4 字母码组合是示意——真实用代码根据 4 个字母自动查找对应的中文名和 tagline 即可
5. 可以灵活调整维度映射的题号，只要逻辑自洽

### 开发顺序

1. `personality.py` → 后端能产出报告 JSON
2. 接 `questionnaire.py` → 特征向量生成后调用 personality
3. 改 `app.py` → API 返回带 personality
4. 改前端问卷页 → 弹报告卡片
5. 加分享按钮 + 样式

---

## Git 纪律

- 每次 push 前更新 CHANGELOG.md（这是项目约定，见 `.cursor/rules/changelog-on-push.mdc`）
- 开工前 `git pull`，收工后 `git commit -m "... 改了什么" && git push`
- 不清楚的地方直接在仓库里读文档，docs/ 下有 11 份

---

## 当前最新 commit

```
72c0318 docs: love personality report technical spec for Cursor implementation
```

开工前先 `git pull origin master`。
