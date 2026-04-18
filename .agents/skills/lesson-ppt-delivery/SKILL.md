---
name: lesson-ppt-delivery
description: 获取课件内容并展示到前端
version: 3.1.0
author: MindGuide Team
---

# 课件交付 Skill

## 触发规则

**学习/课件意图必须调用`get_current_lesson_ppt`，禁止用纯文字替代课件。**

触发关键词：开始学习、继续学习、看课件、展示PPT、下一节、下一课、继续上课、学第X章、继续学

**参数填写（每次调用都必须提供）：**
- `goal_id`：从"学习目标概览"中查找，格式为`[id=数字]`，提取其中的数字。如用户说"继续学习拓维信息"，找到匹配的目标行`[id=10] 拓维信息`，则goal_id=10
- `student_id`：从"当前用户信息"中的id字段获取
- `chapter_number`/`section_number`：用户指定则传，否则不传

## 可用工具

### `get_current_lesson_ppt`

获取指定章节或当前进度的课件内容。

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| `goal_id` | integer | 是 | 学习目标ID，从学习目标概览的[id=X]中提取 |
| `student_id` | integer | 是 | 学生ID，从当前用户信息中获取 |
| `chapter_number` | integer | 否 | 章序号，不传则自动定位 |
| `section_number` | integer | 否 | 节序号，需同时指定chapter_number |
