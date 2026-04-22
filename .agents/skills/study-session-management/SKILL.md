---
name: study-session-management
description: 学习会话管理工具，用于保存学习摘要和加载历史学习记录
version: 1.0.0
author: MindGuide Team
---

# 学习会话管理 Skill

## 功能说明

管理学习会话的生命周期：
1. **会话结束时**：调用 save_study_summary 保存当前学习记录的摘要和完整交互
2. **会话开始时**：调用 get_recent_sessions_summary 加载最近3次学习记录，让AI给出连贯引导

## 触发规则

### 必须调用 save_study_summary 的场景

**用户表达结束学习意图时，必须调用此工具保存学习记录。**

触发关键词：
- "今天的学习到此结束"
- "感谢陪伴"
- "结束学习"
- "学习结束"
- "今天就到这里"
- "下次继续"
- 用户连续对话超过15分钟后的任何结束语

**响应顺序要求（重要）**：
1. **立即**向用户输出告别回复（如"今天的学习到此结束啦，辛苦啦！明天继续加油哦~"）
2. **同时**调用 `save_study_summary` 保存记录，`summary` 可传空字符串
3. 不要等待摘要生成完成再回复用户

触发模式示例：
- 用户: "今天就到这里吧，感谢陪伴！"
- AI: **立即**回复告别 → **同时**调用 save_study_summary(summary="") 保存记录

### 应该调用 get_recent_sessions_summary 的场景

**每次会话开始时，如果用户选择了学习目标，模型应主动加载历史记录。**

触发关键词：
- "继续学习" + 目标名
- "上次学到..."
- 切换到之前学习过的目标

触发模式示例：
- 用户: "继续学习Python"
- AI: 调用 get_recent_sessions_summary → 获知上次学习了"函数定义"章节 → "上次我们学习了函数的基本概念，今天继续深入了解函数的参数传递..."

## 可用工具

### `save_study_summary`

当用户表达结束学习意图时，保存当前会话的摘要和完整交互记录。

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| `goal_id` | integer | 是 | 学习目标ID，从学习目标概览的[id=X]中提取 |
| `student_id` | integer | 是 | 学生ID，从当前用户信息中获取 |
| `conversation_log` | string | 是 | 完整对话记录（JSON数组格式），例如：[{"role":"user","content":"..."},{"role":"assistant","content":"..."}] |
| `summary` | string | 否 | AI生成的会话摘要，100字左右。**可为空字符串**，前端会异步调用LLM生成个性化摘要并保存 |
| `study_duration_minutes` | integer | 否 | 学习时长（分钟），默认0 |
| `lessons_completed` | integer | 否 | 完成的课时数，默认0 |
| `exercises_attempted` | integer | 否 | 练习题数，默认0 |
| `exercises_correct` | integer | 否 | 正确数，默认0 |

**返回值**: 
```json
{"success": true, "message": "学习记录已保存", "record_id": 123, "session_count": 5}
```

### `get_recent_sessions_summary`

获取指定学习目标的最近3次学习会话摘要，用于会话开始时加载上下文。

| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| `goal_id` | integer | 是 | 学习目标ID，从学习目标概览的[id=X]中提取 |
| `student_id` | integer | 是 | 学生ID，从当前用户信息中获取 |
| `limit` | integer | 否 | 返回的会话数量，默认3 |

**返回值**:
```json
{
  "success": true, 
  "sessions": [
    {"summary": "学习了函数的基本定义和调用", "created_at": "2024-03-15T10:30:00", "study_duration_minutes": 25},
    {"summary": "掌握了变量的作用域概念", "created_at": "2024-03-14T15:00:00", "study_duration_minutes": 20}
  ],
  "total_count": 2
}
```

## 使用示例

### 示例1：用户结束学习

**用户输入**: "今天的学习到此结束，感谢陪伴！"

**模型思维**: 
1. 用户表达了结束学习意图
2. **立即**输出告别回复，不要让用户等待
3. **同时**调用 save_study_summary 保存会话记录，summary 传空（前端会异步生成个性化摘要）

**第一轮 - 立即回复**:
"今天的学习到此结束啦，辛苦啦！明天继续加油哦~"

**同时调用工具**:
```json
{
  "tool_name": "save_study_summary",
  "arguments": {
    "goal_id": 10,
    "student_id": 1,
    "conversation_log": "[{\"role\":\"user\",\"content\":\"开始学习函数\"},{\"role\":\"assistant\",\"content\":\"好的，我们来学习函数...\"}]",
    "summary": "",
    "study_duration_minutes": 30,
    "lessons_completed": 1
  }
}
```

**第二轮 - 工具返回后**（如需要，可简短确认）：
"学习记录已保存好咯，下次见！"

### 示例2：用户继续学习

**用户输入**: "继续学习上次的内容"

**模型思维**:
1. 用户要继续学习，需要加载历史记录
2. 调用 get_recent_sessions_summary 获取最近3次学习摘要
3. 根据历史记录继续学习

**工具调用**:
```json
{
  "tool_name": "get_recent_sessions_summary",
  "arguments": {
    "goal_id": 10,
    "student_id": 1,
    "limit": 3
  }
}
```

**工具返回**:
```json
{
  "success": true,
  "sessions": [
    {"summary": "学习了函数的基本定义和调用", "created_at": "2024-03-15T10:30:00"},
    {"summary": "掌握了变量的作用域概念", "created_at": "2024-03-14T15:00:00"}
  ]
}
```

**模型回复**:
"欢迎回来！我记得上次我们学习了函数的基本概念。今天我们继续深入，了解函数的参数传递方式和返回值的使用。准备好了吗？"

## 注意事项

1. **必须保存**: 当检测到用户结束学习意图时，必须调用 save_study_summary 保存记录，不能直接结束会话
2. **立即回复优先**: 用户表达结束意图时，**第一时间**输出告别回复，不要让用户等待摘要生成。summary 参数可传空字符串
3. **摘要由前端异步生成**: `summary` 字段非必需，前端会在后台调用 LLM 生成个性化摘要并保存到数据库。模型无需在 tool_call 中生成复杂摘要
4. **历史记录作为引导**: get_recent_sessions_summary 返回的摘要应该作为模型回复的参考，帮助模型给出更连贯的学习引导
5. **conversation_log 格式**: 必须是JSON数组格式，包含完整的对话记录，每条消息包含 role 和 content 字段