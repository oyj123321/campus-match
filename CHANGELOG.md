# Changelog

All notable changes to CampusMatch.

---

## [1.1.0] — 2026-07-28

### 问题（上次）
- 匹配写死「男只找女 / 女只找男」，无法支持同性或双性取向
- 上线前缺少生产开关、验证码限流、隐私说明与健康检查，不敢直接给同学用

### 改动
- **Added / 择偶取向**：问卷基本信息增加「希望匹配的性别」（男 / 女 / 男女都可以）；匹配需双方取向互相接受
- **Fixed / 匹配引擎**：`orientation_compatible` 双向过滤；批量模式在含同性/不限时改用贪心配对
- **Added / MVP 1.1 上线项**：`FLASK_DEBUG`、Session 安全、注册限流、`/api/health`、首页隐私说明
- **Fixed / 注册**：SMTP 失败时仍返回验证码到页面，不阻断验证流程
- **Docs**：`docs/mvp-roadmap.md`；`.env.example` 补充生产配置项
- **Seed**：默认异性取向；Emma 设为 `both` 便于演示

---

## [1.0.1] — 2026-07-28

### 问题（上次）
- 问卷量表滑块默认停在 3，进度却显示未答/提交又偷偷带上默认值，交互混乱
- `answers` JSON 键是字符串、匹配逻辑用 int 取，导致一票否决和匹配理由实际失效
- 「重新匹配」遇到已有记录直接跳过，页面像匹配失败；旧逻辑还可能重复发邮件
- 种子用户兴趣选项写错（咖啡馆/民谣等），特征向量对不上题库

### 改动
- **Fixed / 问卷页**：改为 1–5 点选；未点不算已答；提交前校验并高亮缺题
- **Fixed / 数据层**：`answers`、`important_qids` 读写统一为 int 键
- **Fixed / 匹配**：更新已有 Match 并返回结果；邮件只通知新匹配
- **Fixed / 种子与 API**：选项纠错 + `seed.py --refresh`；不足 20 题拒绝提交；过滤非法 multi
- **Improved**：进度 sticky、已答/未答状态、★ 重要标记、移动端 Likert；共同点含兴趣交集
- **Docs**：约定每次推送前必须更新本更改日志（见 `.cursor/rules/changelog-on-push.mdc`）

---

## [1.0.0] — 2026-07-27

### MVP 首个完整可用版本

#### Added
- **学校邮箱注册 + QQ SMTP 真实邮件验证**
  - 域名白名单自动识别学校
  - QQ 邮箱 SMTP 发送 6 位验证码
  - 10 分钟过期机制
  - 开发模式 fallback：邮件失败时控制台打印 token

- **32题深度问卷系统**
  - 四维度：核心价值观(8) / 生活习惯(8) / 情感风格(8) / 兴趣爱好(8)
  - Scale 滑块 (1-5) + Multi 多选
  - "对我很重要" 标记（权重 ×2）
  - 一票否决（出轨/孩子/婚姻/抽烟）

- **81维特征向量 + 余弦相似度匹配**
  - 问卷答案 → 归一化特征向量
  - 余弦相似度 Top-N 实时匹配
  - 匈牙利算法全局最优匹配（批量模式备用）
  - 一票否决过滤

- **匹配结果邮件通知**
  - 双方收到对方微信号 + 匹配度百分比
  - 共同点 + 差异分析
  - 样式化 HTML 邮件

- **种子数据生成器**
  - 澳大 8人（4男4女）+ 澳科 1人
  - 差异化人设：心理学/工科/法律/商科/传理/教育/金融/计算机/设计
  - 81维特征向量预计算

- **公网部署**
  - serveo SSH 反向隧道，零成本
  - pythonw 后台运行，不依赖终端
  - .env 环境变量管理

- **爬虫策略模块**
  - 多源搜索策略生成
  - 学校兴趣标签自动提取
  - 日报系统同款 pipeline

#### Supported Schools
- 澳门大学 (um.edu.mo)
- 澳门科技大学 (must.edu.mo)
- 澳门理工大学 (mpu.edu.mo)
- 澳门旅游大学 (iftm.edu.mo)
- 澳门城市大学 (cityu.edu.mo)
- 上海交通大学 (sjtu.edu.cn) — 参考实现
- 复旦大学 (fudan.edu.cn)
- 同济大学 (tongji.edu.cn)
- 华东师范大学 (ecnu.edu.cn)

#### Tech Stack
- Python 3 / Flask / SQLAlchemy / SQLite
- Jinja2 / Vanilla JS / CSS
- QQ SMTP / serveo SSH tunnel

---

## [0.1.0] — 2026-07-27 (early)

### 初始原型

- Flask 骨架 + SQLite
- 标签关键词匹配（简单交集）
- 上海高校邮箱白名单
- 开发模式邮件打印

---

### 版本命名规则

```
v<MAJOR>.<MINOR>.<PATCH>

MAJOR: 不兼容的架构变更
MINOR: 新功能、新学校、新算法
PATCH: Bug 修复、样式调整
```
