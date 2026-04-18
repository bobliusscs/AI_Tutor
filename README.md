# MindGuide - 基于智能体的自适应学习系统

MindGuide 是一款基于智能体（Agent）架构的自适应学习系统，采用 B/S 架构设计，以学习目标为核心组织单元，引入大模型驱动的智能体进行个性化学习引导，为学习者提供学习资源生成、学情分析、资源推荐和个性化学习引导等核心功能。

## 背景与问题

传统在线学习平台存在以下不足：
- **学习资源生成成本高**：依赖教师或专家编写，学习资源更新周期长
- **个性化建模不足**：缺乏学生知识建模与个性化资源推荐能力
- **学习引导缺失**：学生缺乏导师个性化引导和答疑支持

MindGuide 针对上述问题，提供了一套完整的自适应学习解决方案。

## 核心功能

### 1. 学习资源生成与管理
- 以学习目标为核心组织单元，围绕目标生成知识图谱、学习计划、课件、习题等资源
- 支持上传教材/课件构建专属学习资料库
- 知识图谱支持可视化展示与手动编辑
- 习题库支持上传、生成、筛选和导出

### 2. 学情分析
- 可视化统计分析：学习进度、练习正确率、学习趋势、学习偏好等
- 结合 **PG-LLM-KT 知识追踪模型** 建模学生知识掌握状态
- 实时更新学习记录与掌握度预测

### 3. 学习资源推荐
- 基于 **PG-KG-REC 学习资源推荐算法**
- 从习题库中选择能最大化学生知识水平增益的 Top-N 个习题
- 智能推荐策略提升学习效率

### 4. 个性化学习引导（Agent）
- **长期记忆与短期记忆机制**：持续记录学习行为与交互反馈
- **工具调用系统**：支持学习资料查询、课件获取、进度查询、习题推荐等
- **自适应教学策略**：在持续交互中动态调整学习路径
- **工具扩展能力**：通过 Skill 系统扩展智能体的教学和辅导能力

## 设计原则

| 原则 | 描述 |
|------|------|
| 模块化与可扩展性 | 分层与模块化设计，标准化接口，支持模型替换与功能演进 |
| 数据与模型协同驱动 | 结合 PG-LLM-KT 与 PG-KG-REC 模型，实现数据驱动与模型驱动的协同 |
| 以学习者为中心的个性化 | 围绕学习目标与行为建模，动态调整学习路径与推荐策略 |

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    客户端层                          │
│         (React + Ant Design + ECharts)              │
├─────────────────────────────────────────────────────┤
│                    服务层                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ 学习资源生成  │ │   学情分析    │ │  资源推荐    │ │
│  │ 与管理模块    │ │    模块       │ │   模块       │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │           个性化学习引导模块（Agent）              │ │
│  │   长期记忆 │ 短期记忆 │ 工具系统 │ Skill扩展      │ │
│  └──────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│                    数据层                            │
│   (学习目标 │ 知识图谱 │ 学习资源 │ 学习行为 │ 模型)  │
└─────────────────────────────────────────────────────┘
```

## 技术架构

```
MindGuide/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── agent/             # Agent 核心模块
│   │   │   ├── memory/        # 记忆系统
│   │   │   │   ├── long_term.py
│   │   │   │   └── short_term.py
│   │   │   ├── tools/         # 工具系统
│   │   │   │   ├── builtin.py
│   │   │   │   ├── executor.py
│   │   │   │   └── registry.py
│   │   │   ├── context.py
│   │   │   ├── core.py        # Agent主循环
│   │   │   └── evolution.py   # 自演化
│   │   ├── agents/            # Agent适配层
│   │   ├── api/
│   │   │   └── routes/       # API路由
│   │   │       ├── chat.py       # 聊天接口
│   │   │       ├── knowledge_graph.py
│   │   │       ├── learning_plan.py
│   │   │       ├── practice.py   # 练习巩固
│   │   │       ├── question.py   # 习题库
│   │   │       └── ...
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── engines/           # 核心引擎
│   │   │   ├── knowledge_graph_engine.py  # 知识图谱
│   │   │   ├── learning_plan_engine.py    # 学习规划
│   │   │   ├── lesson_engine.py           # 课时教学
│   │   │   ├── assessment_engine.py        # 诊断测评
│   │   │   ├── memory_engine.py           # 记忆系统
│   │   │   ├── document_processor.py      # 文档处理
│   │   │   └── analysis_engine.py         # 学情分析
│   │   ├── models/            # 数据模型
│   │   ├── prompts/           # 提示词模板
│   │   ├── services/          # 业务服务
│   │   │   ├── ai_model_provider.py      # AI模型调用
│   │   │   ├── cancel_manager.py          # 取消管理
│   │   │   └── ...
│   │   └── skills/            # 技能系统
│   │       ├── definitions/   # Skill定义
│   │       ├── manager.py
│   │       ├── skill_chain.py
│   │       └── tools.py
│   ├── uploads/              # 上传文件目录
│   ├── requirements.txt
│   ├── .env.example
│   └── mindguide.db          # SQLite数据库
├── frontend/                 # React前端
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   │   ├── Chat.jsx         # 聊天页面
│   │   │   ├── GoalList.jsx    # 学习目标列表
│   │   │   ├── LandingPage.jsx  # 落地页
│   │   │   ├── Login.jsx       # 登录
│   │   │   ├── Register.jsx     # 注册
│   │   │   ├── Settings.jsx     # 设置
│   │   │   ├── SkillManagement.jsx
│   │   │   └── goal/           # 学习目标子页面
│   │   │       ├── Analysis.jsx     # 学情分析
│   │   │       ├── KnowledgeGraph.jsx
│   │   │       ├── Questions.jsx
│   │   │       └── ...
│   │   ├── components/      # 公共组件
│   │   │   ├── CanvasPanel.jsx        # 画布面板
│   │   │   ├── ChatInputBar.jsx       # 聊天输入
│   │   │   ├── ChatPPTVisualizer.jsx  # PPT可视化
│   │   │   ├── ExercisePractice.jsx   # 习题练习
│   │   │   ├── GuideTestModal.jsx     # 引导测试
│   │   │   ├── LearningStyle.jsx      # 学习风格
│   │   │   └── MermaidRenderer.jsx    # Mermaid渲染
│   │   ├── layouts/
│   │   └── utils/
│   ├── dist/                # 构建输出
│   ├── package.json
│   └── vite.config.js
├── start.ps1               # Windows启动脚本
└── README.md
```

## 快速开始

### 一键启动（Windows）

```powershell
.\start.ps1
```

### 手动启动

**后端：**

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 编辑配置AI模型
uvicorn app.main:app --reload
```

后端运行在 http://localhost:8000

**前端：**

```bash
cd frontend
npm install
npm run dev
```

前端运行在 http://localhost:5173

## 环境配置

复制 `backend/.env.example` 为 `backend/.env`：

```bash
# AI模型配置
AI_MODEL_PROVIDER=ollama  # 或 openai
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:9B

# OpenAI配置
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo
```

## 环境要求

- Python 3.10+
- Node.js 16+
- Ollama 或 OpenAI API

## 技术栈

### 后端
- FastAPI - 高性能异步Web框架
- SQLAlchemy - ORM框架
- Pydantic - 数据验证
- LangChain - AI应用开发

### 前端
- React 18 + Vite
- Ant Design 5.x - UI组件库
- ECharts - 数据可视化
- Mermaid - 图表渲染
- Framer Motion - 动画效果

### 数据库
- SQLite（默认）
- 支持扩展为 PostgreSQL/MySQL

## 许可证

MIT License
