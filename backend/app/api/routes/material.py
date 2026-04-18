"""
学习资料 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import shutil
import uuid

from app.core.database import get_db
from app.api.deps import get_current_student_id
from app.schemas import Response
from app.models.study_goal import StudyGoal
from app.models.study_material import StudyMaterial, MaterialType, MaterialSource

# 文件上传配置 - 与main.py保持一致
# 修正：路径必须与main.py中StaticFiles挂载的upload_dir一致
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UPLOAD_DIR = os.path.join(backend_dir, "app", "uploads", "materials")
os.makedirs(UPLOAD_DIR, exist_ok=True)


router = APIRouter()


@router.get("/{goal_id}", response_model=Response)
async def list_materials(
    goal_id: int,
    material_type: Optional[str] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取学习目标的学习资料列表
    
    ## 参数
    - material_type: 筛选类型 (ai_generated/user_uploaded/web_link/video/document)
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    query = db.query(StudyMaterial).filter(StudyMaterial.study_goal_id == goal_id)
    
    if material_type:
        query = query.filter(StudyMaterial.material_type == material_type)
    
    materials = query.order_by(StudyMaterial.created_at.desc()).all()
    
    return Response(
        success=True,
        message="获取成功",
        data=[m.to_dict() for m in materials]
    )


@router.post("/{goal_id}", response_model=Response)
async def create_material(
    goal_id: int,
    title: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    material_type: str = MaterialType.AI_GENERATED.value,
    related_nodes: Optional[List[str]] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    创建学习资料（AI生成或手动创建）
    
    ## 参数
    - title: 资料标题
    - content: 资料内容
    - description: 资料描述
    - material_type: 资料类型
    - related_nodes: 关联的知识点ID列表
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    material = StudyMaterial(
        study_goal_id=goal_id,
        title=title,
        description=description,
        content=content,
        material_type=material_type,
        source=MaterialSource.USER.value if material_type == MaterialType.USER_UPLOADED.value else MaterialSource.SYSTEM.value,
        related_nodes=related_nodes or []
    )
    
    db.add(material)
    db.commit()
    db.refresh(material)
    
    return Response(
        success=True,
        message="资料创建成功",
        data=material.to_dict()
    )


@router.get("/{goal_id}/{material_id}", response_model=Response)
async def get_material(
    goal_id: int,
    material_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """获取资料详情"""
    # 验证用户权限
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.study_goal_id == goal_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="资料不存在")
    
    # 更新查看次数
    material.view_count += 1
    db.commit()
    
    return Response(
        success=True,
        message="获取成功",
        data=material.to_dict()
    )


@router.delete("/{goal_id}/{material_id}", response_model=Response)
async def delete_material(
    goal_id: int,
    material_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """删除学习资料"""
    # 验证用户权限
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    material = db.query(StudyMaterial).filter(
        StudyMaterial.id == material_id,
        StudyMaterial.study_goal_id == goal_id
    ).first()
    
    if not material:
        raise HTTPException(status_code=404, detail="资料不存在")
    
    db.delete(material)
    db.commit()
    
    return Response(
        success=True,
        message="删除成功",
        data={"id": material_id}
    )


@router.post("/{goal_id}/generate", response_model=Response)
async def generate_material(
    goal_id: int,
    node_id: str,
    material_format: str = "article",  # article/summary/exercises
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    AI生成学习资料
    
    ## 参数
    - node_id: 针对哪个知识点生成资料
    - material_format: 资料格式 (article-文章/summary-总结/exercises-练习题)
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # TODO: 调用AI服务生成资料
    # 这里返回模拟数据
    
    material = StudyMaterial(
        study_goal_id=goal_id,
        title=f"知识点 {node_id} 的学习资料",
        description=f"AI生成的{material_format}格式资料",
        content="这里是AI生成的内容...",
        material_type=MaterialType.AI_GENERATED.value,
        source=MaterialSource.SYSTEM.value,
        related_nodes=[node_id],
        ai_generation_params={
            "node_id": node_id,
            "format": material_format,
            "generated_at": datetime.utcnow().isoformat()
        }
    )
    
    db.add(material)
    db.commit()
    db.refresh(material)
    
    return Response(
        success=True,
        message="资料生成成功",
        data=material.to_dict()
    )


@router.post("/{goal_id}/upload", response_model=Response)
async def upload_material_file(
    goal_id: int,
    request: Request,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    上传学习资料文件
    
    支持格式：PDF, Word (.docx), 图片, 文本
    """
    # 验证用户权限
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在或无权访问")
    
    # 解析FormData
    form_data = await request.form()
    
    # 调试：打印所有字段
    print(f"[Upload Debug] FormData keys: {list(form_data.keys())}")
    print(f"[Upload Debug] FormData types: {[(k, type(form_data[k]).__name__, hasattr(form_data[k], 'filename')) for k in form_data.keys()]}")
    
    # 获取文件 - 直接获取第一个文件
    file = None
    for key in form_data.keys():
        field_value = form_data[key]
        if hasattr(field_value, 'filename') and hasattr(field_value, 'content_type'):
            file = field_value
            print(f"[Upload Debug] Found file: {field_value.filename}, type: {field_value.content_type}")
            break
    
    if not file:
        # 调试信息
        keys_list = list(form_data.keys())
        print(f"[Upload Debug] No file found. Keys: {keys_list}")
        raise HTTPException(status_code=400, detail=f"请选择要上传的文件 (keys: {keys_list})")
    
    # 获取其他字段
    title = form_data.get("title", file.filename or "未命名文件")
    material_type = form_data.get("material_type", MaterialType.USER_UPLOADED.value)
    description = form_data.get("description")
    
    # 验证文件类型
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "text/plain",
    ]
    allowed_extensions = [".pdf", ".docx", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".txt"]
    
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    
    if file.content_type not in allowed_types and file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 PDF、Word、图片、文本文件")
    
    # 限制文件大小（50MB）
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset position
    
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过50MB限制")
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 构建访问URL
    content_url = f"/uploads/materials/{unique_filename}"
    
    # 获取文件格式（去掉点号）
    file_format = file_ext.lstrip('.').lower() if file_ext else ""
    
    # 文档类型：默认使用文件扩展名
    # 注意：文档类型检测（扫描版/文字版）应在需要处理时进行，而不是上传时
    # 这样可以避免上传时就开始转换图片，提升上传速度
    document_type = file_format  # 默认使用文件格式作为文档类型
    
    # 创建资料记录（保持用户选择的类型）
    material = StudyMaterial(
        study_goal_id=goal_id,
        title=title or file.filename,
        description=description or f"上传文件: {file.filename}",
        content=content_url,
        material_type=material_type,
        source=MaterialSource.USER.value,
        file_size=file_size,
        content_url=content_url,
        file_format=file_format,
        document_type=document_type
    )
    
    db.add(material)
    db.commit()
    db.refresh(material)
    
    return Response(
        success=True,
        message="文件上传成功",
        data=material.to_dict()
    )
