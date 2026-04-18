"""
MindGuide AI 家教系统 - 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api.router import api_router


def _migrate_agent_memories(db_engine) -> None:
    """为 agent_memories 表添加缺失的新列（幂等，SQLite 兼容）"""
    from sqlalchemy import text
    new_columns = [
        "ALTER TABLE agent_memories ADD COLUMN embedding TEXT",
        "ALTER TABLE agent_memories ADD COLUMN version INTEGER DEFAULT 1",
    ]
    with db_engine.connect() as conn:
        for sql in new_columns:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                # 列已存在时忽略错误（SQLite 会抛出 OperationalError: duplicate column name）
                pass


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    
    # 导入所有模型以确保建表时能发现它们
    import app.models  # noqa: F401
    
    # 自动建表（包含所有已注册的 SQLAlchemy 模型）
    Base.metadata.create_all(bind=engine)
    
    # 幂等迁移：为已有表添加新列（SQLite 兼容方式）
    _migrate_agent_memories(engine)
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI 智能家庭教师系统",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载 API 路由
    app.include_router(api_router, prefix="/api")
    
    # 创建上传目录 - 与 material.py 保持一致
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    # 创建materials子目录
    materials_dir = os.path.join(upload_dir, "materials")
    os.makedirs(materials_dir, exist_ok=True)
    
    # 挂载静态文件（上传的文件）
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
    
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
