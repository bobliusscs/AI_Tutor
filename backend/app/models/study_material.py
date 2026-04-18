"""
数据模型 - 学习资料
存储AI生成或用户上传的学习资料
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.core.database import Base


class MaterialType(str, enum.Enum):
    """资料类型"""
    AI_GENERATED = "ai_generated"  # AI生成
    USER_UPLOADED = "user_uploaded"  # 用户上传
    WEB_LINK = "web_link"  # 网页链接
    VIDEO = "video"  # 视频
    DOCUMENT = "document"  # 文档


class MaterialSource(str, enum.Enum):
    """资料来源"""
    SYSTEM = "system"  # 系统生成
    USER = "user"  # 用户上传
    IMPORTED = "imported"  # 外部导入


class StudyMaterial(Base):
    """学习资料表"""
    __tablename__ = "study_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    study_goal_id = Column(Integer, ForeignKey("study_goals.id"), nullable=False)
    
    # 基本信息
    title = Column(String(300), nullable=False)  # 资料标题
    description = Column(Text)  # 资料描述
    
    # 类型与来源
    material_type = Column(String(30), default=MaterialType.AI_GENERATED.value)
    source = Column(String(20), default=MaterialSource.SYSTEM.value)
    
    # 内容
    content = Column(Text)  # 文本内容
    content_url = Column(String(500))  # 外部链接或文件路径
    
    # 关联知识点
    related_nodes = Column(JSON)  # 关联的知识点ID列表 ["node_id1", "node_id2"]
    
    # 元数据
    file_format = Column(String(50))  # 文件格式：pdf, doc, mp4等
    file_size = Column(Integer)  # 文件大小（字节）
    document_type = Column(String(50))  # 文档类型：scanned_pdf/text_pdf/word/powerpoint/image
    
    # 使用统计
    view_count = Column(Integer, default=0)  # 查看次数
    download_count = Column(Integer, default=0)  # 下载次数
    
    # AI生成信息
    ai_generation_params = Column(JSON)  # AI生成参数
    
    # 关联
    study_goal = relationship("StudyGoal", back_populates="materials")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<StudyMaterial {self.title}>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "material_type": self.material_type,
            "source": self.source,
            "content": self.content,
            "content_url": self.content_url,
            "related_nodes": self.related_nodes,
            "file_format": self.file_format,
            "document_type": self.document_type,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
