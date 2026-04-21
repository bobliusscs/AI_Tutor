"""
学生管理 API 路由
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import bcrypt
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.config import settings
from app.models.student import Student
from app.schemas import StudentCreate, StudentLogin, Response


router = APIRouter()


def hash_password(password: str) -> str:
    """密码哈希 - 使用 bcrypt"""
    # bcrypt 限制密码长度最多 72 字节
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 - 使用 bcrypt"""
    # bcrypt 限制密码长度最多 72 字节
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # 将 datetime 转换为时间戳（UTC 时间戳）
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=Response)
async def register_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db)
):
    """学生注册"""
    # 检查用户名是否已存在
    existing = db.query(Student).filter(Student.username == student_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建学生
    student = Student(
        username=student_data.username,
        email=student_data.email,
        nickname=student_data.nickname,
        hashed_password=hash_password(student_data.password),
        background=student_data.background
    )
    
    db.add(student)
    db.commit()
    db.refresh(student)
    
    # 生成JWT token
    access_token = create_access_token(
        data={"sub": student.username, "student_id": student.id}
    )
    
    return Response(
        success=True,
        message="注册成功",
        data={
            "student_id": student.id,
            "username": student.username,
            "token": access_token
        }
    )


@router.post("/login", response_model=Response)
async def login_student(
    login_data: StudentLogin,
    db: Session = Depends(get_db)
):
    """学生登录"""
    student = db.query(Student).filter(Student.username == login_data.username).first()
    
    if not student or not verify_password(login_data.password, student.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成JWT token
    access_token = create_access_token(
        data={"sub": student.username, "student_id": student.id}
    )
    
    return Response(
        success=True,
        message="登录成功",
        data={
            "student_id": student.id,
            "username": student.username,
            "nickname": student.nickname,
            "token": access_token
        }
    )


@router.get("/{student_id}/profile", response_model=Response)
async def get_student_profile(
    student_id: int,
    db: Session = Depends(get_db)
):
    """获取学生档案"""
    student = db.query(Student).filter(Student.id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": student.id,
            "username": student.username,
            "nickname": student.nickname,
            "grade": student.grade,
            "total_learning_time": student.total_learning_time,
            "study_streak": student.study_streak
        }
    )
