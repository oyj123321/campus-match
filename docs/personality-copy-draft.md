# 问卷推演 MBTI · 文案与产品定稿（阶段 A）

> 状态：已按拍板实现（见 `mbti_report.py` + 匹配中心展示）  
> 已弃用：自创四潮 / 十二校园型 / 塔罗包装

## 拍板

1. 标题：**问卷推演 MBTI**  
2. **不显示**四维进度条  
3. 更合拍：**只写字母**（如 `INFJ、ENFP`）  
4. 语气：**正经**

## 免责（页内固定）

本结果由 CampusMatch 恋爱问卷近似映射，并非正式 MBTI 测验，仅供娱乐与破冰参考，不代表匹配算法结论。

## 实现入口

- 映射与十六型文案：`mbti_report.py`  
- 提交问卷后写入 `users.mbti_json`；`GET /api/me/mbti`  
- 匹配中心顶部展示块  

规划总览见 [`personality-fun-report.md`](./personality-fun-report.md)。
