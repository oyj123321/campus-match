# 趣味性格报告技术思路（已收敛为 MBTI）

> 状态：阶段 A **已实现（规则映射 MBTI）**  
> 相关：[`personality-copy-draft.md`](./personality-copy-draft.md)、[`multi-agent-vip-features.md`](./multi-agent-vip-features.md)

---

## 结论（产品）

内测反馈希望填完有「像星座一样」的解读。自创体系认可度低，**阶段 A 直接采用大众熟悉的 MBTI 十六型**：

- 标题：**问卷推演 MBTI**  
- 无四维条；更合拍只写字母；语气正经  
- **不改**匹配主算法（仍余弦等）  
- 页脚声明：非正式 MBTI 测验

---

## 与多 Agent VIP

| | 问卷推演 MBTI（已做） | 多 Agent 陪审团（规划） |
|--|----------------------|------------------------|
| 对象 | 单人 | 双人 |
| 时机 | 交卷后 / 匹配中心 | 配对后 / VIP |
| 成本 | 零 API | LLM |

阶段 B（可选）：用一次 LLM 润色十六型长文。阶段 C：把类型摘要喂给双人说明书。

---

## 实现要点

- `mbti_report.build_mbti_report(answers)`：量表/多选 → E/I·S/N·T/F·J/P → 类型文案 + 神准句  
- 落库 `users.mbti_json`；接口 `GET /api/me/mbti`  
- UI：`templates/matches.html` 顶部卡片  

---

## 一句话

先给公认的 MBTI 字母与正经恋爱速写；好玩、好分享；匹配仍走向量。
