"""
Skill管理器 - 加载和管理Skill工具

核心功能:
- 扫描 .agents/skills/ 目录加载Skill定义
- 解析 SKILL.md 文件提取工具信息
- 注册工具函数并生成OpenAI格式定义
"""
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillManager:
    """Skill工具管理器"""
    
    SKILLS_DIR = ".agents/skills"
    
    def __init__(self, db=None, student_id=None):
        """
        Args:
            db: 数据库会话
            student_id: 学生ID
        """
        self.db = db
        self.student_id = student_id
        self.skills = {}  # skill_name -> skill_info
        self.tools = {}   # tool_name -> tool_info
        self.tool_functions = {}  # tool_name -> function
        
    def discover_and_load(self):
        """自动发现并加载所有Skill"""
        try:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent.parent
            skills_path = project_root / self.SKILLS_DIR
            
            if not skills_path.exists():
                logger.warning(f"Skills目录不存在: {skills_path}")
                return
            
            logger.info(f"开始扫描Skills目录: {skills_path}")
            
            for skill_dir in skills_path.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    self._load_skill(skill_dir)
            
            logger.info(f"已加载 {len(self.skills)} 个Skill, {len(self.tools)} 个工具")
            
        except Exception as e:
            logger.error(f"加载Skills失败: {e}", exc_info=True)
    
    def _load_skill(self, skill_dir: Path):
        """加载单个Skill"""
        try:
            skill_name = skill_dir.name
            skill_md_path = skill_dir / "SKILL.md"
            
            # 读取SKILL.md
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析YAML frontmatter
            metadata = self._parse_frontmatter(content)
            
            # 提取工具定义
            tools = self._extract_tools_from_md(content)
            
            # 提取触发规则
            trigger_rules = self._extract_trigger_rules(content)
            
            # 保存Skill信息
            self.skills[skill_name] = {
                'name': skill_name,
                'path': str(skill_dir),
                'metadata': metadata,
                'tools': tools,
                'trigger_rules': trigger_rules,
                'loaded_at': datetime.now().isoformat()
            }
            
            # 注册工具（将触发规则合并进description，遵循OpenAI Function Calling标准）
            for tool in tools:
                tool_name = tool['name']
                
                # 构建完整描述：基础描述 + 触发规则
                full_description = tool['description']
                if trigger_rules:
                    full_description = f"{full_description}\n\n触发条件：{trigger_rules}"
                
                self.tools[tool_name] = {
                    'skill': skill_name,
                    'description': full_description,
                    'parameters': tool['parameters'],
                    'returns': tool.get('returns', '')
                }
                
                logger.info(f"注册工具: {tool_name} (来自Skill: {skill_name})")
            
        except Exception as e:
            logger.error(f"加载Skill {skill_dir.name} 失败: {e}", exc_info=True)
    
    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """解析YAML frontmatter"""
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}
        
        frontmatter = match.group(1)
        result = {}
        
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        
        return result
    
    def _extract_tools_from_md(self, content: str) -> List[Dict[str, Any]]:
        """从Markdown中提取工具定义"""
        tools = []
        
        # 查找"可用工具"章节
        tools_section = re.search(r'## 可用工具\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        if not tools_section:
            return tools
        
        # 查找工具标题 (### `tool_name` 或 ### 1. `tool_name`)
        tool_matches = re.finditer(r'### (?:\d+\.\s*)?`(\w+)`\s*\n(.*?)(?=### (?:\d+\.\s*)?`|\Z)', 
                                   tools_section.group(1), re.DOTALL)
        
        for match in tool_matches:
            tool_name = match.group(1)
            tool_content = match.group(2)
            
            # 提取描述
            description = self._extract_tool_description(tool_content)
            
            # 提取参数(从表格)
            parameters = self._extract_parameters_from_table(tool_content)
            
            # 提取返回值
            returns = self._extract_returns(tool_content)
            
            tools.append({
                'name': tool_name,
                'description': description,
                'parameters': parameters,
                'returns': returns
            })
        
        return tools
    
    def _extract_tool_description(self, content: str) -> str:
        """提取工具描述"""
        # 第一行非空文本作为描述
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('|') and not line.startswith('**'):
                return line[:200]
        return ""
    
    def _extract_parameters_from_table(self, content: str) -> Dict[str, Any]:
        """从Markdown表格提取参数定义,转换为JSON Schema"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # 查找参数表格：支持有"**参数：**"前缀或直接表格两种格式
        # 1) 有前缀：**参数：**\n| ... |
        table_match = re.search(r'\*\*参数[:：]\*\*\s*\n(.*?)(?=\n\*\*|\Z)', content, re.DOTALL)
        if not table_match:
            # 2) 无前缀：直接匹配含"参数名"表头的表格行
            table_match = re.search(r'(\|[^\n]*参数[^\n]*\|\n\|[\s\-|]+\|\n(?:\|[^\n]+\|\n?)+)', content)
        
        if not table_match:
            return schema
        
        table_content = table_match.group(1)
        
        # 查找表格行 - 支持带反引号和不带反引号的参数名
        # 格式: | `param_name` | type | 是/否 | description |
        # 或:  | param_name | type | 是/否 | description |
        rows = re.finditer(r'\|\s*`?(\w+)`?\s*\|\s*(\w+)\s*\|\s*([是否])\s*\|\s*(.*?)\s*\|', 
                          table_content)
        
        for row in rows:
            param_name = row.group(1)
            param_type = row.group(2)
            is_required = row.group(3)
            param_desc = row.group(4).strip()
            
            # 转换类型
            json_type = self._convert_type(param_type)
            
            schema["properties"][param_name] = {
                "type": json_type,
                "description": param_desc
            }
            
            if is_required == "是":
                schema["required"].append(param_name)
        
        return schema
    
    def _convert_type(self, type_str: str) -> str:
        """转换Markdown类型为JSON Schema类型"""
        type_mapping = {
            'integer': 'integer',
            'int': 'integer',
            'string': 'string',
            'str': 'string',
            'number': 'number',
            'float': 'number',
            'boolean': 'boolean',
            'bool': 'boolean',
            'array': 'array',
            'object': 'object'
        }
        return type_mapping.get(type_str.lower(), 'string')
    
    def _extract_returns(self, content: str) -> str:
        """提取返回值说明"""
        returns_match = re.search(r'\*\*返回值:\*\*\s*(.*?)(?=\n---|\Z)', content, re.DOTALL)
        if returns_match:
            return returns_match.group(1).strip()[:500]
        return ""
    
    def _extract_trigger_rules(self, content: str) -> str:
        """从SKILL.md的'触发规则'章节提取规则文本，用于注入系统提示词"""
        match = re.search(r'## 触发规则\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def register_tool_function(self, tool_name: str, func: Callable):
        """注册工具函数实现"""
        if tool_name not in self.tools:
            logger.warning(f"尝试注册未知工具: {tool_name}")
            return
        
        self.tool_functions[tool_name] = func
        logger.info(f"注册工具函数: {tool_name}")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取OpenAI Function Calling格式的工具列表"""
        tools_list = []
        
        for tool_name, tool_info in self.tools.items():
            tools_list.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            })
        
        return tools_list
    
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self.tools
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果的字符串表示
        """
        if tool_name not in self.tool_functions:
            return f"Error: Tool '{tool_name}' not implemented"
        
        try:
            func = self.tool_functions[tool_name]
            
            # 自动注入db和student_id
            import inspect
            sig = inspect.signature(func)
            params = sig.parameters
            
            call_args = arguments.copy()
            if 'db' in params and 'db' not in call_args:
                call_args['db'] = self.db
            if 'student_id' in params and 'student_id' not in call_args:
                call_args['student_id'] = self.student_id
            
            # 执行函数
            if inspect.iscoroutinefunction(func):
                result = await func(**call_args)
            else:
                result = func(**call_args)
            
            # 转换为字符串
            if isinstance(result, str):
                return result
            else:
                return json.dumps(result, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {e}", exc_info=True)
            return f"Error executing tool '{tool_name}': {str(e)}"
    
    def get_tools_description(self) -> str:
        """获取工具描述的Markdown文本(用于注入系统提示词)"""
        if not self.tools:
            return "当前无可用工具。"
        
        desc_parts = ["## 可用工具\n"]
        
        # 按Skill分组
        skill_groups = {}
        for tool_name, tool_info in self.tools.items():
            skill_name = tool_info['skill']
            if skill_name not in skill_groups:
                skill_groups[skill_name] = []
            skill_groups[skill_name].append((tool_name, tool_info))
        
        for skill_name, tools in skill_groups.items():
            desc_parts.append(f"\n### {skill_name}\n")
            for tool_name, tool_info in tools:
                desc_parts.append(f"- **{tool_name}**: {tool_info['description']}")
        
        return "\n".join(desc_parts)
