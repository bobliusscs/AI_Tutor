"""
依赖注入 - 获取数据库会话和引擎管理器
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.services.engine_manager import EngineManager
from app.models.student import Student


# JWT Bearer 认证
security = HTTPBearer(auto_error=False)


def get_engine_manager(db: Session = Depends(get_db)) -> EngineManager:
    """
    获取引擎管理器（动态读取最新配置）
    每个引擎内部会根据 model_config.json 获取各自的 AI Provider
    """
    return EngineManager(db)


def get_current_student(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Student:
    """
    从 JWT token 中提取并验证当前登录用户
    
    安全机制：
    - 所有需要认证的 API 都必须使用此依赖
    - 用户 ID 从 token 中提取，而不是信任前端参数
    - 自动校验 token 有效期
    
    Raises:
        HTTPException: 401 认证失败
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证，请先登录",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        student_id: int = payload.get("student_id")
        username: str = payload.get("sub")
        
        if student_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 格式无效，缺少用户信息",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 验证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 从数据库验证学生存在
    student = db.query(Student).filter(Student.id == student_id).first()
    
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被删除",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return student


def get_current_student_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> int:
    """
    简化版：只返回当前用户的 student_id
    
    用于不需要完整 Student 对象的场景
    """
    student = get_current_student(credentials, db)
    return student.id
