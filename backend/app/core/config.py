"""
核心配置模块
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"  # 允许额外字段
    )
    
    # 应用设置
    APP_NAME: str = "MindGuide"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_TYPE: str = "sqlite"  # sqlite 或 mysql
    DATABASE_URL: str = "sqlite:///./mindguide.db"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # AI 模型配置
    AI_MODEL_PROVIDER: str = "ollama"  # openai, qwen, 或 ollama
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "qwen3.5:9B"
    
    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3.5:9B"
    
    # 自定义 API 配置
    CURRENT_PROVIDER: str = "ollama"  # ollama 或 custom
    CUSTOM_API_KEY: str = ""
    CUSTOM_API_BASE_URL: str = "https://api.openai.com/v1"
    CUSTOM_MODEL: str = "gpt-4o-mini"
    CUSTOM_SUPPORTS_THINKING: bool = False
    
    # Tavily 联网搜索配置
    TAVILY_API_KEY: str = ""
    
    # Qwen本地模型配置
    QWEN_MODEL_PATH: str = "./models/qwen-7b"
    QWEN_DEVICE: str = "cuda"
    
    # JWT 设置
    SECRET_KEY: str = "your_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # CORS 设置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"]
    
    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 知识图谱生成配置（基于学习资料）
    # 图片分批配置（扫描版PDF转换为图片后的处理）
    IMAGE_BATCH_SIZE: int = 5  # 每次发送给多模态模型的图片数量
    
    # 文字分批配置（其他文档提取文字后的处理）
    TEXT_CHUNK_SIZE: int = 2000  # 每批文字的字符数
    TEXT_CHUNK_OVERLAP: int = 200  # 批次之间的重叠字符数
    
    # 知识图谱生成参数
    MIN_KNOWLEDGE_POINTS: int = 5  # 最少知识点数量
    MAX_KNOWLEDGE_POINTS: int = 40  # 最多知识点数量
    GRAPH_VALIDATION_ENABLED: bool = True  # 是否启用图谱验证

    # Agent 配置
    WORKSPACE_ROOT: str = "."  # 工作空间根目录（用于加载 Skills）


# 全局配置实例
settings = Settings()
