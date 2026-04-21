"""
数据库配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# 创建数据库引擎
if settings.DATABASE_TYPE == "sqlite":
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}  # SQLite 需要
    )
else:  # MySQL
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
