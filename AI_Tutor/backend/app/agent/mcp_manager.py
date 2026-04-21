"""
MCP客户端管理器 - 连接和管理MCP Server

核心功能:
- 连接MCP Server (支持SSE和Stdio两种传输方式)
- 获取MCP Server提供的工具列表
- 执行MCP工具调用
"""
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 延迟导入MCP库,避免未安装时报错
try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP库未安装,MCP功能不可用。运行: pip install mcp")


class MCPClientManager:
    """MCP客户端管理器"""
    
    def __init__(self):
        self.servers = {}  # server_name -> session
        self.tools = {}    # tool_name -> (server_name, tool_info)
        self.connections = {}  # server_name -> connection context (用于清理)
    
    async def add_server(self, name: str, config: dict):
        """
        添加MCP Server连接
        
        Args:
            name: Server名称
            config: Server配置 {
                "transport": "sse" | "stdio",
                "url": "...",  # SSE模式
                "command": "...",  # Stdio模式
                "args": []  # Stdio模式参数
            }
        """
        if not MCP_AVAILABLE:
            logger.error(f"MCP库未安装,无法连接Server: {name}")
            return
        
        try:
            transport = config.get("transport", "sse")
            
            if transport == "sse":
                await self._connect_sse(name, config["url"])
            elif transport == "stdio":
                await self._connect_stdio(name, config)
            else:
                logger.error(f"不支持的传输方式: {transport}")
                
        except Exception as e:
            logger.error(f"连接MCP Server {name} 失败: {e}", exc_info=True)
    
    async def _connect_sse(self, name: str, url: str):
        """通过SSE连接MCP Server"""
        try:
            logger.info(f"正在通过SSE连接MCP Server: {name} ({url})")
            
            # 创建SSE连接
            sse_connection = sse_client(url=url)
            streams = await sse_connection.__aenter__()
            
            # 创建会话
            session = ClientSession(*streams)
            await session.__aenter__()
            
            # 初始化
            await session.initialize()
            
            # 获取工具列表
            tools_result = await session.list_tools()
            
            # 注册工具
            for tool in tools_result.tools:
                self.tools[tool.name] = (name, tool)
                logger.info(f"注册MCP工具: {tool.name} (来自Server: {name})")
            
            # 保存连接
            self.servers[name] = session
            self.connections[name] = {
                'sse': sse_connection,
                'session': session
            }
            
            logger.info(f"MCP Server {name} 连接成功,获取 {len(tools_result.tools)} 个工具")
            
        except Exception as e:
            logger.error(f"SSE连接失败 {name}: {e}", exc_info=True)
            raise
    
    async def _connect_stdio(self, name: str, config: dict):
        """通过Stdio连接MCP Server"""
        try:
            logger.info(f"正在通过Stdio连接MCP Server: {name} ({config['command']})")
            
            command = config["command"]
            args = config.get("args", [])
            
            # 创建Stdio连接
            stdio_connection = stdio_client(command=command, args=args)
            streams = await stdio_connection.__aenter__()
            
            # 创建会话
            session = ClientSession(*streams)
            await session.__aenter__()
            
            # 初始化
            await session.initialize()
            
            # 获取工具列表
            tools_result = await session.list_tools()
            
            # 注册工具
            for tool in tools_result.tools:
                self.tools[tool.name] = (name, tool)
                logger.info(f"注册MCP工具: {tool.name} (来自Server: {name})")
            
            # 保存连接
            self.servers[name] = session
            self.connections[name] = {
                'stdio': stdio_connection,
                'session': session
            }
            
            logger.info(f"MCP Server {name} 连接成功,获取 {len(tools_result.tools)} 个工具")
            
        except Exception as e:
            logger.error(f"Stdio连接失败 {name}: {e}", exc_info=True)
            raise
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取MCP工具的OpenAI格式定义"""
        tools_list = []
        
        for tool_name, (server_name, tool_info) in self.tools.items():
            # 转换MCP工具格式为OpenAI格式
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info.description,
                    "parameters": tool_info.inputSchema
                }
            }
            tools_list.append(openai_tool)
        
        return tools_list
    
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self.tools
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        执行MCP工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果的字符串表示
        """
        if tool_name not in self.tools:
            return f"Error: MCP Tool '{tool_name}' not found"
        
        try:
            server_name, tool_info = self.tools[tool_name]
            session = self.servers[server_name]
            
            logger.info(f"执行MCP工具: {tool_name} (Server: {server_name})")
            
            # 调用工具
            result = await session.call_tool(tool_name, arguments)
            
            # 格式化结果
            return self._format_result(result)
            
        except Exception as e:
            logger.error(f"执行MCP工具 {tool_name} 失败: {e}", exc_info=True)
            return f"Error executing MCP tool '{tool_name}': {str(e)}"
    
    def _format_result(self, result) -> str:
        """格式化MCP工具执行结果"""
        try:
            # MCP返回可能是多种格式,统一转为字符串
            if hasattr(result, 'content'):
                # 如果有content属性,尝试序列化
                return json.dumps(result.content, ensure_ascii=False, default=str)
            elif isinstance(result, list):
                return json.dumps(result, ensure_ascii=False, default=str)
            elif isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False, default=str)
            else:
                return str(result)
        except Exception as e:
            logger.error(f"格式化MCP结果失败: {e}")
            return str(result)
    
    async def close_all(self):
        """关闭所有MCP连接"""
        for name, conn in self.connections.items():
            try:
                if 'session' in conn:
                    await conn['session'].__aexit__(None, None, None)
                if 'sse' in conn:
                    await conn['sse'].__aexit__(None, None, None)
                if 'stdio' in conn:
                    await conn['stdio'].__aexit__(None, None, None)
                logger.info(f"MCP Server {name} 已断开连接")
            except Exception as e:
                logger.error(f"关闭MCP Server {name} 失败: {e}")
        
        self.servers.clear()
        self.tools.clear()
        self.connections.clear()
    
    def load_from_config(self, config_path: str):
        """
        从配置文件加载MCP Server列表
        
        Args:
            config_path: 配置文件路径 (JSON格式)
        """
        try:
            import os
            if not os.path.exists(config_path):
                logger.warning(f"MCP配置文件不存在: {config_path}")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            servers = config.get("servers", [])
            logger.info(f"从配置文件加载 {len(servers)} 个MCP Server")
            
            return servers
            
        except Exception as e:
            logger.error(f"加载MCP配置文件失败: {e}", exc_info=True)
            return []
