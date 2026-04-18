"""
引擎管理器 - 统一管理所有引擎实例
"""
from functools import lru_cache
from sqlalchemy.orm import Session
import os
import threading

from app.core.config import settings
from app.services.ai_model_provider import AIModelProvider
from app.engines.knowledge_graph_engine import KnowledgeGraphEngine
from app.engines.learning_plan_engine import LearningPlanEngine
from app.engines.lesson_engine import LessonEngine
from app.engines.assessment_engine import AssessmentEngine
from app.engines.memory_engine import MemoryEngine
from app.engines.analysis_engine import AnalysisEngine


# 线程安全的缓存清除锁
_cache_lock = threading.Lock()


def _read_env_file():
    """
    从 .env 文件读取配置（用于动态获取最新配置）
    """
    # 获取 .env 文件路径（从 engine_manager.py 位置向上查找）
    # engine_manager.py 在 app/services/ 下
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env_path = os.path.join(backend_dir, ".env")
    
    config = {
        "CURRENT_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "qwen3.5:9B",
        "CUSTOM_API_KEY": "",
        "CUSTOM_API_BASE_URL": "https://api.openai.com/v1",
        "CUSTOM_MODEL": "gpt-4o-mini",
        "CUSTOM_SUPPORTS_THINKING": False,
        # 知识图谱生成配置
        "IMAGE_BATCH_SIZE": 5,
        "TEXT_CHUNK_SIZE": 2000,
        "TEXT_CHUNK_OVERLAP": 200,
    }
    
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key in config:
                                # 处理布尔值和整数值
                                if key == "CUSTOM_SUPPORTS_THINKING":
                                    config[key] = value.lower() == "true"
                                elif key in ["IMAGE_BATCH_SIZE", "TEXT_CHUNK_SIZE", "TEXT_CHUNK_OVERLAP"]:
                                    try:
                                        config[key] = int(value)
                                    except ValueError:
                                        pass
                                else:
                                    config[key] = value
        except Exception as e:
            print(f"读取 .env 文件出错: {e}")
    
    return config


def _create_ai_provider() -> AIModelProvider:
    """
    创建AI模型提供者的实例（每次调用都创建新实例）
    """
    # 动态读取 .env 文件获取最新配置
    env_config = _read_env_file()
    
    config = {
        "CURRENT_PROVIDER": env_config["CURRENT_PROVIDER"],
        "OLLAMA_BASE_URL": env_config["OLLAMA_BASE_URL"],
        "OLLAMA_MODEL": env_config["OLLAMA_MODEL"],
        "CUSTOM_API_KEY": env_config["CUSTOM_API_KEY"],
        "CUSTOM_API_BASE_URL": env_config["CUSTOM_API_BASE_URL"],
        "CUSTOM_MODEL": env_config["CUSTOM_MODEL"],
        "CUSTOM_SUPPORTS_THINKING": env_config["CUSTOM_SUPPORTS_THINKING"],
    }
    
    return AIModelProvider(
        provider_name=env_config["CURRENT_PROVIDER"],
        config=config
    )


# 缓存 AI provider 实例（用于聊天等需要保持状态的场景）
@lru_cache(maxsize=1)
def get_ai_provider() -> AIModelProvider:
    """
    获取AI模型提供者的单例实例
    """
    return _create_ai_provider()


def reset_ai_provider_cache():
    """
    清除 AI provider 缓存（当设置更新时调用）
    """
    global _ai_provider_instance
    with _cache_lock:
        get_ai_provider.cache_clear()
        print("[AI Provider] 缓存已清除，下次调用将读取最新配置")


class EngineManager:
    """引擎管理器"""
    
    def __init__(self, db: Session, ai_provider: AIModelProvider):
        self.db = db
        self.ai_provider = ai_provider
        
        # 初始化所有引擎
        self.knowledge_graph_engine = KnowledgeGraphEngine(db, ai_provider)
        self.learning_plan_engine = LearningPlanEngine(db, ai_provider)
        self.lesson_engine = LessonEngine(db)
        self.assessment_engine = AssessmentEngine(db, ai_provider)
        self.memory_engine = MemoryEngine(db)
        self.analysis_engine = AnalysisEngine(db)
    
    @classmethod
    def create(cls, db: Session, config: dict) -> "EngineManager":
        """
        创建引擎管理器实例
        
        Args:
            db: 数据库会话
            config: AI 模型配置
            
        Returns:
            EngineManager 实例
        """
        ai_provider = AIModelProvider(
            provider_name=config.get("AI_MODEL_PROVIDER", "openai"),
            config=config
        )
        return cls(db, ai_provider)
