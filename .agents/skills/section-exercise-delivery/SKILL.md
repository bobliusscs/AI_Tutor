---
name: section-exercise-delivery
description: 获取自适应难度习题并展示到前端
version: 2.1.0
author: MindGuide Team
---

# 习题交付 Skill

## 触发规则

**练习/做题意图必须调用`get_section_exercises`，禁止用纯文字出题。**

触发关键词：做练习、做题、做习题、测试一下、巩固练习、练一练、推荐习题、练习巩固

**参数填写（每次调用都必须提供）：**
- `goal_id`：从"学习目标概览"中查找，格式为`[id=数字]`，提取其中的数字。如用户说"做拓维信息的练习"，找到匹配的目标行`[id=10] 拓维信息`，则goal_id=10
- `student_id`：从"当前用户信息"中的id字段获取
- `chapter_number`/`section_number`：用户指定则传，否则不传

## 可用工具

### `get_section_exercises`

获取指定章节或当前进度的习题（自适应难度）。

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| `goal_id` | integer | 是 | 学习目标ID，从学习目标概览的[id=X]中提取 |
| `student_id` | integer | 是 | 学生ID，从当前用户信息中获取 |
| `chapter_number` | integer | 否 | 章序号，不传则自动定位 |
| `section_number` | integer | 否 | 节序号，需同时指定chapter_number |
