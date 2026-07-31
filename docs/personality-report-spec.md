# 恋爱人格报告 — 技术规格

> 给 Cursor 实现的完整方案。填完问卷 → 立刻生成人格分析 → 可截图分享。

---

## 一、触发时机

```
POST /api/questionnaire 提交成功
    ↓
立刻调用人格报告生成器
    ↓
写入 User.mbti_json 字段（字段已存在，见 models.py:50）
    ↓
前端在提交成功后展示报告卡片（不是跳匹配页，而是先弹报告）
```

## 二、人格分类体系

### 4 个维度 × 每个维度 2 极 = 16 种恋爱人格

| 维度 | 来源题目 | 低分端 | 高分端 |
|------|---------|--------|--------|
| **情感表达 (E/I)** | Q18（表达爱意方式）、Q22（浪漫vs务实）、Q21 情绪支持 | 内敛含蓄 (I) | 外放热烈 (E) |
| **生活节奏 (S/F)** | Q9（作息）、Q12（整洁）、Q16（旅行风格）、Q29（户外vs室内） | 结构秩序 (S) | 随性自由 (F) |
| **关系边界 (C/O)** | Q19（独处需求）、Q20（社交边界）、Q7（伴侣vs朋友） | 亲密融合 (C) | 独立自主 (O) |
| **风险态度 (P/A)** | Q4（消费观）、Q5（婚姻）、Q6（孩子）、Q34（消费观念） | 稳健保守 (P) | 开放冒险 (A) |

### 16 种人格代号

```
        情感表达(E)                情感表达(I)
生活 S   ESCP (守护者型)            ISCP (静谧港湾型)
节奏 +   ESCA (开明领航型)           ISCA (内秀构建型)
秩序 F   EFCP (阳光筑巢型)           IFCP (温柔守望型)
         EFCA (浪漫牧者型)           IFCA (诗意栖居型)

         EOCP (灯塔型)              IOCP (沉思者型)
生活 S   EOCA (自由先驱型)           IOCA (孤岛哲人型)
节奏 +   EOCP 变体 (热心管家型)       IOCP 变体 (自我王国型)
随性 F   EFCP 变体 (亲密冒险家)       IFCP 变体 (花园隐士型)
         EFCA 变体 (春风旅人型)       IFCA 变体 (星尘游吟型)
```

> 注：上面是示意。真实代号用 4 字母码 + 一个易记的中文名。不需要全列 16 种，让代码自动组合生成。

## 三、评分算法

```python
def generate_love_personality(user):
    answers = user.answers  # {int_qid: value}
    
    # 1. 四维度打分（每个维度 0-100）
    dimensions = compute_dimension_scores(answers)
    
    # 2. 确定每维的极性（高于/低于 50）
    dims = {
        "expression": ("E" if dimensions["expression"] >= 50 else "I", dimensions["expression"]),
        "rhythm":     ("S" if dimensions["rhythm"] >= 50 else "F", dimensions["rhythm"]),
        "boundary":   ("C" if dimensions["boundary"] >= 50 else "O", dimensions["boundary"]),
        "risk":       ("P" if dimensions["risk"] >= 50 else "A", dimensions["risk"]),
    }
    
    # 3. 人格代号（4 字母）
    code = dims["expression"][0] + dims["rhythm"][0] + dims["boundary"][0] + dims["risk"][0]
    
    # 4. 生成报告
    return {
        "code": code,           # 如 "ESCP"
        "name": get_personality_name(code),  # 如 "守护者型"
        "dimensions": dims,
        "traits": generate_traits(dims),     # 3 条核心特质
        "strength": generate_strength(dims), # 关系中最大优势
        "match_tip": generate_match_tip(code, answers),  # 适合什么样的伴侣
        "subtitle": generate_subtitle(code),  # 一句话 tagline
    }
```

### 各维度分值计算（纯基于答案，不需要其他用户数据）

```python
def compute_dimension_scores(answers):
    # expression 情感表达 (0-100)
    expr = scale_score(answers, [
        (18, "多选", {"帮对方做事": -20, "准备礼物惊喜": -10, "直接说爱": +20, "拥抱牵手": +10}),
        (22, "scale", lambda v: (v-1)*25),           # 浪漫(高分)=外放
        (21, "scale", lambda v: (v-1)*25),           # 陪伴=外放
    ])
    
    # rhythm 生活节奏 (0-100) — 高分=秩序，低分=随性
    rhythm = scale_score_avg(answers, [9,12,16,29], invert=[12,29])
    # Q9 作息(早睡=秩序) Q12 整洁(整洁=秩序) Q16 旅行(规划=秩序) Q29 户外(户外=秩序)
    
    # boundary 关系边界 (0-100) — 高分=亲密融合，低分=独立
    boundary = scale_score_avg(answers, [7,19,20], invert=[19])
    # Q7 伴侣vs朋友(优先伴侣=亲密) Q19 独处(需要大量=独立=低分) Q20 社交边界(介意=独立=低分)
    
    # risk 风险态度 (0-100) — 高分=保守，低分=冒险
    risk = scale_score_avg(answers, [4,5,6], invert=[])
    # Q4 消费(储蓄=保守) Q5 婚姻(必须=保守) Q6 孩子(一定要=保守)
    # 注意: Q5/Q6 是 dealbreaker, 但如果全选中间值(=3)说明开放态度
    
    return {"expression": clamp(expr), "rhythm": clamp(rhythm), 
            "boundary": clamp(boundary), "risk": clamp(risk)}
```

## 四、报告展示（前端）

提交问卷成功后，不跳匹配页。在当前页弹出一个报告卡片：

```
┌─────────────────────────────────────┐
│         你的恋爱人格                 │
│                                     │
│         🦉 守护者型                  │
│           ESCP                     │
│                                     │
│  "你想要一个可以依靠的肩膀，         │
│   而不是一场冒险的旅程"              │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 情感表达  ████████░░  72% 外放│   │
│  │ 生活节奏  ██████░░░░  58% 秩序│   │
│  │ 关系边界  ████░░░░░░  35% 融合│   │
│  │ 风险态度  ████████░░  68% 保守│   │
│  └─────────────────────────────┘   │
│                                     │
│  💡 你的核心特质                    │
│  · 你会用行动而非言语表达在乎       │
│  · 对关系有清晰的边界感             │
│  · 看重长期承诺胜过一时激情         │
│                                     │
│  💚 你在关系中的优势                │
│  善于深度倾听，让对方感到被理解     │
│                                     │
│  🔮 你可能适合                      │
│  感性浪漫型 — 能把你从逻辑里        │
│  拉出来，同时尊重你的边界           │
│                                     │
│  [📋 进入匹配页]  [📤 分享报告]     │
└─────────────────────────────────────┘
```

## 五、文件改动清单

| 文件 | 改动 |
|------|------|
| **新增 `personality.py`** | 核心生成器：维度打分 + 人格分类 + 报告生成 |
| **修改 `questionnaire.py`** | 在 `build_feature_vector()` 之后调用 personality 生成，存 `mbti_json` |
| **修改 `app.py`** | `POST /api/questionnaire` 返回中增加 `personality` 字段 |
| **修改 `templates/questionnaire.html`** | 提交成功后弹出报告卡片（成功后不立刻跳匹配页，点"进入匹配页"再跳） |
| **修改 `static/style.css`** | 人格报告卡片样式 |
| **修改 `static/i18n.js`** | 人格报告相关翻译 key |
| **新增 `templates/_personality_card.html`** | （可选）报告卡片模板片段，可复用 |

## 六、分享机制

报告底部 [📤 分享报告] 按钮：

```javascript
// 不是生成图片（太重），而是复制一段带链接的文案
function shareReport(personality) {
    const text = `我在 CampusMatch 做了恋爱人格测试
我是 ${personality.name} (${personality.code})
"${personality.subtitle}"
→ 来测测你的是什么 https://xxx.serveousercontent.com`;
    
    if (navigator.share) {
        navigator.share({ text });
    } else {
        copyToClipboard(text);
        alert('文案已复制，去朋友圈/小红书粘贴吧！');
    }
}
```

不追求"精美海报图片"——那是上线后优化的事。MVP 用复制文案就够了。女生填完看到"守护者型"三个字，自然会截图发出去。

## 七、开发顺序建议

1. 先写 `personality.py` + 在 `questionnaire.py` 里接上 → 后端能产出报告 JSON
2. 改 `app.py` → API 返回里带 personality
3. 改前端问卷页 → 提交后展示卡片
4. 加分享按钮 + 样式
5. 测试：填一份问卷看报告长什么样

---

## 附录：4 个维度的详细计分规则

### 情感表达 E/I
```
Q18 (多选, 表达爱意方式):
  "直接说爱与赞美"     → +25
  "拥抱牵手等接触"     → +12
  "准备礼物惊喜"       → -10
  "帮对方做事"         → -20
  基础分 50，加减后 clamp 到 0-100

Q22 (scale 1-5, 浪漫vs务实):
  (value-1) * 25 加到基础分
  选1(极度浪漫)=0, 选5(极度务实)=100, 选3=50

Q21 (scale 1-5, 情绪低落时希望伴侣):
  (value-1) * 25
  选1(主动陪伴)=0, 选5(给空间)=100

三项取平均值 → expression_score
≥50 → E (外放热烈)
<50 → I (内敛含蓄)
```

### 生活节奏 S/F
```
Q9  (scale): (value-1)*25  早睡=高分(秩序)
Q12 (scale): (6-value)*25  整洁=高分(秩序) [反向]
Q16 (scale): (value-1)*25  规划=高分(秩序)
Q29 (scale): (6-value)*25  户外=高分(秩序) [反向]

四项取平均 → rhythm_score
≥50 → S (结构秩序)
<50 → F (随性自由)
```

### 关系边界 C/O
```
Q7  (scale): (6-value)*25  优先伴侣=高分(亲密) [反向]
Q19 (scale): (value-1)*25  需要大量独处=高分(独立) [注意: 高独处=低亲密]
Q20 (scale): (6-value)*25  介意社交=低分(独立) [反向]

三项取平均 → boundary_score
≥50 → C (亲密融合)
<50 → O (独立自主)
```

### 风险态度 P/A
```
Q4  (scale): (value-1)*25  储蓄=高分(保守)
Q5  (scale): (value-1)*25  必须结婚=高分(保守)
Q6  (scale): (value-1)*25  一定要孩子=高分(保守)

三项取平均 → risk_score
≥50 → P (稳健保守)
<50 → A (开放冒险)
```

> 注意 Q5/Q6 是 dealbreaker 题。如果用户选了极端值（1 或 5），这个维度的倾向会很强——这是有意的。人格报告可以如实反映极端倾向，但匹配时不应展示此维度对比。
