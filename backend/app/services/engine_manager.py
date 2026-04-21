"""
引擎管理器 - 统一管理所有引擎实例
支持按功能模块分配不同的 AI 模型
"""
from functools import lru_cache
from sqlalchemy.orm import Session
import threading

from app.services.ai_model_provider import AIModelProvider
from app.engines.knowledge_graph_engine import KnowledgeGraphEngine
from app.engines.learning_plan_engine import LearningPlanEngine
from app.engines.lesson_engine import LessonEngine
from app.engines.assessment_engine import AssessmentEngine
from app.engines.memory_engine import MemoryEngine
from app.engines.analysis_engine import AnalysisEngine


# 线程安全的缓存清除锁
_cache_lock = threading.Lock()

# 模块级 Provider 缓存
_module_provider_cache: dict = {}


def _create_provider_from_config(provider_name: str, config: dict) -> AIModelProvider:
    """
    从配置创建 AIModelProvider 实例
    """
    return AIModelProvider(provider_name=provider_name, config=config)


def _create_ai_provider() -> AIModelProvider:
    """
    创建AI模型提供者的实例（使用默认/agent模块配置）
    """
    from app.core.model_config import get_module_provider_config

    provider_config = get_module_provider_config("agent")
    if provider_config:
        return _create_provider_from_config(
            provider_config["provider_name"],
            provider_config["config"]
        )

    # 降级：使用默认 Ollama 配置
    return _create_provider_from_config("ollama", {
        "CURRENT_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "qwen3.5:9B",
    })


def get_module_provider(module_name: str) -> AIModelProvider:
    """
    获取指定功能模块的 AI Provider

    Args:
        module_name: 模块名称，如 "knowledge_graph", "learning_plan", "exercise", "agent" 等

    Returns:
        AIModelProvider 实例
    """
    from app.core.model_config import get_module_provider_config

    # 检查缓存
    if module_name in _module_provider_cache:
        return _module_provider_cache[module_name]

    provider_config = get_module_provider_config(module_name)
    if provider_config:
        provider = _create_provider_from_config(
            provider_config["provider_name"],
            provider_config["config"]
        )
    else:
        # 降级：使用默认配置
        provider = _create_ai_provider()

    # 缓存
    _module_provider_cache[module_name] = provider
    return provider


# 缓存 AI provider 实例（用于默认/agent场景）
@lru_cache(maxsize=1)
def get_ai_provider() -> AIModelProvider:
    """
    获取AI模型提供者的单例实例（默认使用 agent 模块的配置）
    """
    return _create_ai_provider()


def reset_ai_provider_cache():
    """
    清除所有 Provider 缓存（当设置更新时调用）
    """
    with _cache_lock:
        get_ai_provider.cache_clear()
        _module_provider_cache.clear()
        print("[AI Provider] 所有缓存已清除，下次调用将读取最新配置")


class EngineManager:
    """引擎管理器 - 每个引擎使用其对应模块的 AI Provider"""

    def __init__(self, db: Session):
        self.db = db

        # 每个引擎使用各自模块的 AI Provider
        self.knowledge_graph_engine = KnowledgeGraphEngine(db, get_module_provider("knowledge_graph"))
        self.learning_plan_engine = LearningPlanEngine(db, get_module_provider("learning_plan"))
        self.lesson_engine = LessonEngine(db)
        self.assessment_engine = AssessmentEngine(db, get_module_provider("exercise"))
        self.memory_engine = MemoryEngine(db)
        self.analysis_engine = AnalysisEngine(db)

    @classmethod
    def create(cls, db: Session, config: dict = None) -> "EngineManager":
        """
        创建引擎管理器实例

        Args:
            db: 数据库会话
            config: 兼容旧接口，实际不使用（从 model_config.json 读取）

        Returns:
            EngineManager 实例
        """
        return cls(db)
