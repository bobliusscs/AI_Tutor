"""
Skill服务 - 提供skill的安装、卸载和列表功能
"""
import os
import shutil
import re
from typing import List, Dict, Optional, Any
from datetime import datetime


class SkillService:
    """Skill文件操作服务"""

    # Skills目录相对于项目根目录
    SKILLS_DIR = ".agents/skills"

    # 内置Skill定义（不可卸载）- 仅课件交付与习题交付为核心交付Skill
    BUILTIN_SKILLS = [
        "lesson-ppt-delivery",
        "section-exercise-delivery",
    ]

    # 预设Skill库（可安装的Skill）
    SKILL_PRESETS: List[Dict[str, Any]] = [
        # 内置核心Skill（不可卸载）
        {
            "id": "lesson-ppt-delivery",
            "name": "课件交付",
            "description": "获取课件内容并展示到前端，支持按章节和课时定位课件",
            "category": "core",
            "version": "3.1.0",
            "builtin": True,
        },
        {
            "id": "section-exercise-delivery",
            "name": "习题交付",
            "description": "获取自适应难度习题并展示到前端，支持按章节定位习题",
            "category": "core",
            "version": "2.1.0",
            "builtin": True,
        },
        # 可安装可卸载的扩展Skill
        {
            "id": "aitutor-learning",
            "name": "学习交互",
            "description": "保存长期记忆并结合进度数据提供个性化学习引导",
            "category": "learning",
            "version": "1.0",
            "builtin": False,
        },
        {
            "id": "aitutor-plan",
            "name": "学习计划",
            "description": "管理和展示学习计划的章-节-课时结构，包含课时内容获取功能",
            "category": "learning",
            "version": "1.0",
            "builtin": False,
        },
        {
            "id": "aitutor-question",
            "name": "题库问答",
            "description": "从题库获取题目，支持按知识点和难度筛选，包含出题和评估功能",
            "category": "learning",
            "version": "1.0",
            "builtin": False,
        },
        {
            "id": "aitutor-study-goal",
            "name": "学习目标",
            "description": "管理学习目标，支持创建、查询和更新学习目标",
            "category": "learning",
            "version": "1.0",
            "builtin": False,
        },
        # 学科专项Skill
        {
            "id": "aitutor-math",
            "name": "数学专项",
            "description": "专注于数学学习辅助，包含公式推导、几何证明、数理逻辑训练",
            "category": "subject",
            "version": "1.0",
            "builtin": False,
        },
        {
            "id": "aitutor-english",
            "name": "英语专项",
            "description": "专注于英语学习辅助，包含词汇记忆、语法讲解、阅读理解",
            "category": "subject",
            "version": "1.0",
            "builtin": False,
        },
        {
            "id": "aitutor-physics",
            "name": "物理专项",
            "description": "专注于物理学习辅助，包含力学、电磁学、光学等专题讲解",
            "category": "subject",
            "version": "1.0",
            "builtin": False,
        },
    ]

    @classmethod
    def get_project_root(cls) -> str:
        """获取项目根目录"""
        # 假设从 backend/app/services/ 回溯到项目根
        current = os.path.dirname(os.path.abspath(__file__))
        # backend/app/services -> backend/app -> backend -> project_root
        return os.path.dirname(os.path.dirname(os.path.dirname(current)))

    @classmethod
    def get_skills_dir(cls) -> str:
        """获取skills目录的绝对路径"""
        return os.path.join(cls.get_project_root(), cls.SKILLS_DIR)

    @classmethod
    def _parse_skill_md_header(cls, file_path: str) -> Optional[Dict[str, str]]:
        """解析SKILL.md的YAML frontmatter"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 匹配 YAML frontmatter
            match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                result = {}
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        result[key.strip()] = value.strip()
                return result
            return None
        except Exception:
            return None

    @classmethod
    def _get_skill_description(cls, file_path: str) -> str:
        """从SKILL.md中提取描述"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 移除frontmatter后获取第一段非空文本
            content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

            # 找到第一个标题后的内容作为描述
            lines = content.strip().split("\n")
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    # 跳过标题，返回后续内容
                    desc_lines = []
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if not next_line or next_line.startswith("#"):
                            break
                        if next_line:
                            desc_lines.append(next_line)
                            if len(desc_lines) >= 3:  # 最多3行
                                break
                    return " ".join(desc_lines)[:200] if desc_lines else ""

            return ""
        except Exception:
            return ""

    @classmethod
    def list_installed_skills(cls) -> List[Dict[str, Any]]:
        """获取已安装的skills列表"""
        skills_dir = cls.get_skills_dir()
        installed = []

        if not os.path.exists(skills_dir):
            return installed

        try:
            for item in os.listdir(skills_dir):
                item_path = os.path.join(skills_dir, item)
                skill_md = os.path.join(item_path, "SKILL.md")

                # 检查是否是有效的skill目录
                if not os.path.isdir(item_path) or not os.path.exists(skill_md):
                    continue

                # 解析frontmatter
                metadata = cls._parse_skill_md_header(skill_md)
                description = cls._get_skill_description(skill_md)

                # 查找预设信息
                preset = next(
                    (p for p in cls.SKILL_PRESETS if p["id"] == item), None
                )

                skill_info = {
                    "id": item,
                    "name": preset["name"] if preset else item,
                    "description": metadata.get("description", description)
                    if metadata
                    else description,
                    "builtin": item in cls.BUILTIN_SKILLS,
                    "installed_at": datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).isoformat()
                    if os.path.exists(item_path)
                    else None,
                    "version": preset["version"] if preset else "1.0",
                    "category": preset["category"] if preset else "custom",
                }
                installed.append(skill_info)

        except Exception as e:
            print(f"Error listing installed skills: {e}")

        return installed

    @classmethod
    def get_presets(cls) -> List[Dict[str, Any]]:
        """获取预设skill列表"""
        return cls.SKILL_PRESETS

    @classmethod
    def get_available_skills(cls) -> List[Dict[str, Any]]:
        """获取可安装但尚未安装的skills"""
        installed_ids = {s["id"] for s in cls.list_installed_skills()}
        available = []

        for preset in cls.SKILL_PRESETS:
            if preset["id"] not in installed_ids:
                available.append(preset)

        return available

    @classmethod
    def get_skill_detail(cls, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取指定skill的详细信息"""
        skills_dir = cls.get_skills_dir()
        skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")

        if not os.path.exists(skill_path):
            return None

        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析frontmatter
            metadata = cls._parse_skill_md_header(skill_path)

            # 查找预设信息
            preset = next(
                (p for p in cls.SKILL_PRESETS if p["id"] == skill_name), None
            )

            return {
                "id": skill_name,
                "name": preset["name"] if preset else skill_name,
                "description": metadata.get("description", "")
                    if metadata
                    else "",
                "content": content,
                "builtin": skill_name in cls.BUILTIN_SKILLS,
                "version": preset["version"] if preset else "1.0",
                "category": preset["category"] if preset else "custom",
                "size": os.path.getsize(skill_path),
                "modified_at": datetime.fromtimestamp(
                    os.path.getmtime(skill_path)
                ).isoformat(),
            }
        except Exception as e:
            print(f"Error getting skill detail: {e}")
            return None

    @classmethod
    def install_skill(cls, skill_id: str) -> Dict[str, Any]:
        """安装指定skill"""
        # 查找预设信息
        preset = next((p for p in cls.SKILL_PRESETS if p["id"] == skill_id), None)

        if not preset:
            return {"success": False, "message": f"未找到预设Skill: {skill_id}"}

        # 检查是否已安装
        skills_dir = cls.get_skills_dir()
        skill_path = os.path.join(skills_dir, skill_id)

        if os.path.exists(skill_path):
            return {"success": False, "message": f"Skill {skill_id} 已安装"}

        # 创建目录
        os.makedirs(skill_path, exist_ok=True)

        # 生成SKILL.md内容
        skill_content = cls._generate_skill_md(preset)

        try:
            with open(os.path.join(skill_path, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(skill_content)

            return {
                "success": True,
                "message": f"Skill {preset['name']} 安装成功",
                "skill": {
                    "id": skill_id,
                    "name": preset["name"],
                    "installed_at": datetime.now().isoformat(),
                },
            }
        except Exception as e:
            # 清理创建的空目录
            if os.path.exists(skill_path):
                shutil.rmtree(skill_path)
            return {"success": False, "message": f"安装失败: {str(e)}"}

    @classmethod
    def _generate_skill_md(cls, preset: Dict[str, Any]) -> str:
        """根据预设生成SKILL.md内容"""
        skill_id = preset["id"]
        skill_name = preset["name"]

        # 根据不同skill类型生成不同的内容模板
        templates = {
            "aitutor-math": """---
description: AI Tutor 数学专项学习技能 - 提供数学公式推导、几何证明、数理逻辑训练等专业辅助
---

# AI Tutor 数学专项学习技能

用于提供专业的数学学习辅助，涵盖公式推导、几何证明、数理逻辑训练等专题。

## 技能用途

当需要：
- 推导数学公式或证明定理
- 解决几何证明题
- 训练数理逻辑思维
- 讲解数学概念和解题技巧

## 使用建议

此技能可与 core 技能配合使用，提供更专业的数学辅助学习体验。

---

## 版权声明

此技能由 AI Tutor 系统自动生成。
""",
            "aitutor-english": """---
description: AI Tutor 英语专项学习技能 - 提供词汇记忆、语法讲解、阅读理解等专业辅助
---

# AI Tutor 英语专项学习技能

用于提供专业的英语学习辅助，涵盖词汇记忆、语法讲解、阅读理解等专题。

## 技能用途

当需要：
- 学习英语词汇和短语
- 理解英语语法规则
- 练习阅读理解
- 提升写作表达能力

## 使用建议

此技能可与 core 技能配合使用，提供更专业的英语辅助学习体验。

---

## 版权声明

此技能由 AI Tutor 系统自动生成。
""",
            "aitutor-physics": """---
description: AI Tutor 物理专项学习技能 - 提供力学、电磁学、光学等专题讲解
---

# AI Tutor 物理专项学习技能

用于提供专业的物理学习辅助，涵盖力学、电磁学、光学等专题。

## 技能用途

当需要：
- 理解物理概念和定律
- 解决物理计算题
- 分析物理实验
- 掌握物理公式应用

## 使用建议

此技能可与 core 技能配合使用，提供更专业的物理辅助学习体验。

---

## 版权声明

此技能由 AI Tutor 系统自动生成。
""",
        }

        # 获取模板或使用默认模板
        template = templates.get(
            skill_id,
            f"""---
description: {preset['description']}
---

# {skill_name}

{preset['description']}

## 技能用途

当需要相关学习辅助时使用此技能。

---

## 版权声明

此技能由 AI Tutor 系统自动生成。
""",
        )

        return template

    @classmethod
    def uninstall_skill(cls, skill_name: str) -> Dict[str, Any]:
        """卸载指定skill"""
        # 检查是否是内置skill
        if skill_name in cls.BUILTIN_SKILLS:
            return {
                "success": False,
                "message": f"无法卸载内置Skill: {skill_name}",
            }

        # 检查是否已安装
        skills_dir = cls.get_skills_dir()
        skill_path = os.path.join(skills_dir, skill_name)

        if not os.path.exists(skill_path):
            return {"success": False, "message": f"Skill {skill_name} 未安装"}

        try:
            # 删除skill目录
            shutil.rmtree(skill_path)

            return {
                "success": True,
                "message": f"Skill {skill_name} 已卸载",
            }
        except Exception as e:
            return {"success": False, "message": f"卸载失败: {str(e)}"}

    @classmethod
    def check_skill_installed(cls, skill_id: str) -> bool:
        """检查指定skill是否已安装"""
        skills_dir = cls.get_skills_dir()
        skill_path = os.path.join(skills_dir, skill_id)
        return os.path.exists(skill_path) and os.path.exists(
            os.path.join(skill_path, "SKILL.md")
        )
