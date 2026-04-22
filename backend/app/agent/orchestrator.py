"""
工具编排器 - 统一管理Skill和MCP工具

核心功能:
- 统一管理Skill工具和MCP工具
- 生成OpenAI Function Calling格式的工具定义
- 协调工具执行流程
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .skill_manager import SkillManager
from .mcp_manager import MCPClientManager

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """工具编排器"""
    
    def __init__(self, db=None, student_id=None):
        """
        Args:
            db: 数据库会话
            student_id: 学生ID
        """
        self.db = db
        self.student_id = student_id
        
        # 初始化管理器
        self.skill_manager = SkillManager(db, student_id)
        self.mcp_manager = MCPClientManager()
        
        # MCP配置文件路径
        self.mcp_config_path = None
    
    def discover_and_load_skills(self):
        """发现并加载所有Skill"""
        self.skill_manager.discover_and_load()
        self._register_builtin_tool_functions()
    
    def _register_builtin_tool_functions(self):
        """注册内置工具函数实现"""
        # 注册课件交付工具
        try:
            from app.agent.tools import get_current_lesson_ppt
            self.skill_manager.register_tool_function("get_current_lesson_ppt", get_current_lesson_ppt)
            logger.info("已注册工具函数: get_current_lesson_ppt")
        except Exception as e:
            logger.warning(f"注册工具函数 get_current_lesson_ppt 失败: {e}")
        
        # 注册习题交付工具
        try:
            from app.agent.tools import get_section_exercises
            self.skill_manager.register_tool_function("get_section_exercises", get_section_exercises)
            logger.info("已注册工具函数: get_section_exercises")
        except Exception as e:
            logger.warning(f"注册工具函数 get_section_exercises 失败: {e}")
        
        # 注册学习会话管理工具
        try:
            from app.agent.tools import save_study_summary, get_recent_sessions_summary
            self.skill_manager.register_tool_function("save_study_summary", save_study_summary)
            self.skill_manager.register_tool_function("get_recent_sessions_summary", get_recent_sessions_summary)
            logger.info("已注册工具函数: save_study_summary, get_recent_sessions_summary")
        except Exception as e:
            logger.warning(f"注册学习会话管理工具失败: {e}")
        
        logger.info(f"已注册 {len(self.skill_manager.tool_functions)} 个工具函数")
    
    def load_mcp_servers(self, config_path: str = None):
        """
        加载MCP Server配置
        
        Args:
            config_path: MCP配置文件路径
        """
        if config_path:
            self.mcp_config_path = config_path
        elif self.mcp_config_path:
            config_path = self.mcp_config_path
        else:
            # 默认路径
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "mcp_servers.json"
            self.mcp_config_path = str(config_path)
        
        # 加载配置
        servers_config = self.mcp_manager.load_from_config(config_path)
        
        # 返回配置供异步初始化使用
        return servers_config
    
    async def initialize_mcp_servers(self, servers_config: List[Dict]):
        """
        初始化MCP Server连接
        
        Args:
            servers_config: Server配置列表
        """
        for server_config in servers_config:
            if server_config.get("enabled", False):
                await self.mcp_manager.add_server(
                    server_config["name"],
                    server_config
                )
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有可用工具(OpenAI格式)
        
        Returns:
            工具列表,格式: [{"type": "function", "function": {...}}, ...]
        """
        tools = []
        
        # Skill工具
        tools.extend(self.skill_manager.get_tools())
        
        # MCP工具
        tools.extend(self.mcp_manager.get_tools())
        
        logger.debug(f"获取所有工具: {len(tools)} 个 (Skill: {len(self.skill_manager.tools)}, MCP: {len(self.mcp_manager.tools)})")
        
        return tools
    
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return (self.skill_manager.has_tool(tool_name) or 
                self.mcp_manager.has_tool(tool_name))
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        执行工具,自动路由到Skill或MCP
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        # 优先检查Skill工具
        if self.skill_manager.has_tool(tool_name):
            return await self.skill_manager.execute(tool_name, arguments)
        
        # 检查MCP工具
        elif self.mcp_manager.has_tool(tool_name):
            return await self.mcp_manager.execute(tool_name, arguments)
        
        # 未知工具
        else:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def get_tools_description(self) -> str:
        """
        获取工具描述的Markdown文本(用于注入系统提示词)
        
        Returns:
            工具描述文本
        """
        parts = []
        
        # Skill工具描述
        skill_desc = self.skill_manager.get_tools_description()
        if skill_desc:
            parts.append(skill_desc)
        
        # MCP工具描述
        if self.mcp_manager.tools:
            parts.append("\n## MCP工具\n")
            for tool_name, (server_name, tool_info) in self.mcp_manager.tools.items():
                parts.append(f"- **{tool_name}** (来自 {server_name}): {tool_info.description}")
        
        if not parts:
            return "当前无可用工具。"
        
        return "\n".join(parts)
    
    async def cleanup(self):
        """清理资源"""
        await self.mcp_manager.close_all()
        logger.info("ToolOrchestrator已清理所有资源")
