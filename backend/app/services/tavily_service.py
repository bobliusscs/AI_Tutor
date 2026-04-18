"""
Tavily 联网搜索服务
"""
import os
from typing import Optional, Dict, Any, List
import httpx


class TavilySearchService:
    """Tavily 搜索服务封装"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Tavily 服务
        
        Args:
            api_key: Tavily API Key，如果为 None 则从配置获取
        """
        # 优先使用传入的 key，否则从配置读取
        if api_key:
            self.api_key = api_key
        else:
            # 从 app/core/config.py 的 settings 读取，确保读取最新配置
            try:
                from app.core.config import settings
                self.api_key = getattr(settings, 'TAVILY_API_KEY', '') or os.getenv("TAVILY_API_KEY", "")
            except Exception:
                self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.base_url = "https://api.tavily.com"
        self.search_endpoint = f"{self.base_url}/search"
        
    def is_configured(self) -> bool:
        """检查是否已配置 API Key"""
        return bool(self.api_key and len(self.api_key) > 0)
    
    async def search(
        self, 
        query: str, 
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False
    ) -> Dict[str, Any]:
        """
        执行搜索查询
        
        Args:
            query: 搜索查询字符串
            search_depth: 搜索深度 ("basic" 或 "advanced")
            max_results: 最大返回结果数 (1-20)
            include_answer: 是否包含 AI 生成的答案摘要
            include_raw_content: 是否包含原始网页内容摘要
            include_images: 是否包含相关图片
            
        Returns:
            搜索结果字典，包含:
            - results: 搜索结果列表
            - answer: AI 生成的答案摘要（如果启用）
            - query: 原始查询
        """
        if not self.is_configured():
            raise ValueError("Tavily API Key 未配置")
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.search_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ValueError("Tavily API Key 无效或已过期")
                raise ValueError(f"Tavily API 请求失败: {e.response.status_code}")
            except Exception as e:
                raise ValueError(f"Tavily 搜索出错: {str(e)}")
    
    def format_search_results(self, results: Dict[str, Any]) -> str:
        """
        将搜索结果格式化为适合放入提示词的文本
        
        Args:
            results: search() 返回的结果
            
        Returns:
            格式化后的文本
        """
        if not results.get("results"):
            return "未找到相关结果。"
        
        formatted_parts = []
        
        # 添加查询信息
        formatted_parts.append(f"## 搜索查询: {results.get('query', '')}")
        formatted_parts.append("")
        
        # 添加 AI 生成的答案（如果有）
        if results.get("answer"):
            formatted_parts.append("### 答案摘要:")
            formatted_parts.append(results["answer"])
            formatted_parts.append("")
        
        # 添加搜索结果
        formatted_parts.append("### 搜索结果:")
        for i, result in enumerate(results.get("results", []), 1):
            title = result.get("title", "无标题")
            url = result.get("url", "")
            content = result.get("content", "")
            
            formatted_parts.append(f"**[{i}] {title}**")
            formatted_parts.append(f"来源: {url}")
            formatted_parts.append(f"内容: {content[:300]}..." if len(content) > 300 else f"内容: {content}")
            formatted_parts.append("")
        
        return "\n".join(formatted_parts)
    
    async def search_and_format(
        self, 
        query: str, 
        search_depth: str = "basic",
        max_results: int = 5
    ) -> str:
        """
        执行搜索并直接返回格式化后的文本
        
        Args:
            query: 搜索查询字符串
            search_depth: 搜索深度
            max_results: 最大返回结果数
            
        Returns:
            格式化后的搜索结果文本
        """
        results = await self.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=True
        )
        return self.format_search_results(results)


# 全局单例
_tavily_service: Optional[TavilySearchService] = None


def get_tavily_service(api_key: Optional[str] = None) -> TavilySearchService:
    """获取或创建 Tavily 服务实例"""
    global _tavily_service
    
    if api_key:
        # 如果提供了新的 API Key，创建新实例
        return TavilySearchService(api_key=api_key)
    
    if _tavily_service is None:
        _tavily_service = TavilySearchService()
    
    return _tavily_service


def reset_tavily_service():
    """重置 Tavily 服务实例"""
    global _tavily_service
    _tavily_service = None
