"""
Skill管理 API 路由 - 提供skill的安装、卸载和列表功能
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.skill_service import SkillService
from app.schemas import Response


router = APIRouter()


class SkillInstallRequest(BaseModel):
    """Skill安装请求"""
    skill_id: str


class SkillUninstallRequest(BaseModel):
    """Skill卸载请求"""
    skill_name: str


class SkillInfo(BaseModel):
    """Skill信息"""
    id: str
    name: str
    description: str
    builtin: bool = False
    installed_at: Optional[str] = None
    version: str = "1.0"
    category: str = "custom"


class SkillPreset(BaseModel):
    """Skill预设信息"""
    id: str
    name: str
    description: str
    category: str = "custom"
    version: str = "1.0"
    builtin: bool = False


@router.get("/list", response_model=Response)
async def list_installed_skills():
    """
    获取已安装的skills列表

    返回所有已安装的skill信息，包括内置skill和用户安装的skill。
    """
    try:
        skills = SkillService.list_installed_skills()
        return Response(
            success=True,
            message=f"已安装 {len(skills)} 个Skills",
            data={
                "skills": skills,
                "total": len(skills),
            },
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"获取已安装Skills失败: {str(e)}",
            data={"skills": [], "total": 0},
        )


@router.get("/presets", response_model=Response)
async def get_skill_presets():
    """
    获取预设skill列表

    返回所有可安装的skill预设，包括内置skill和扩展skill。
    """
    try:
        presets = SkillService.get_presets()
        # 同时标注哪些已安装
        installed_ids = {s["id"] for s in SkillService.list_installed_skills()}

        for preset in presets:
            preset["installed"] = preset["id"] in installed_ids

        return Response(
            success=True,
            message="获取预设成功",
            data={
                "presets": presets,
                "total": len(presets),
            },
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"获取预设失败: {str(e)}",
            data={"presets": [], "total": 0},
        )


@router.get("/available", response_model=Response)
async def get_available_skills():
    """
    获取可安装但尚未安装的skills

    返回可安装但尚未安装的skill列表。
    """
    try:
        available = SkillService.get_available_skills()
        return Response(
            success=True,
            message=f"有 {len(available)} 个Skill可安装",
            data={
                "skills": available,
                "total": len(available),
            },
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"获取可用Skills失败: {str(e)}",
            data={"skills": [], "total": 0},
        )


@router.get("/{skill_name}", response_model=Response)
async def get_skill_detail(skill_name: str):
    """
    获取指定skill的详细信息

    - **skill_name**: skill的名称/ID
    """
    try:
        detail = SkillService.get_skill_detail(skill_name)

        if not detail:
            return Response(
                success=False,
                message=f"未找到Skill: {skill_name}",
                data=None,
            )

        return Response(
            success=True,
            message="获取Skill详情成功",
            data=detail,
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"获取Skill详情失败: {str(e)}",
            data=None,
        )


@router.post("/install", response_model=Response)
async def install_skill(request: SkillInstallRequest):
    """
    安装指定skill

    - **skill_id**: 要安装的skill ID（必须是预设中的skill）
    """
    if not request.skill_id:
        return Response(
            success=False,
            message="请提供要安装的skill_id",
            data=None,
        )

    try:
        # 检查是否已安装
        if SkillService.check_skill_installed(request.skill_id):
            return Response(
                success=False,
                message=f"Skill {request.skill_id} 已安装",
                data={"already_installed": True},
            )

        result = SkillService.install_skill(request.skill_id)

        if result["success"]:
            return Response(
                success=True,
                message=result["message"],
                data=result.get("skill"),
            )
        else:
            return Response(
                success=False,
                message=result["message"],
                data=None,
            )

    except Exception as e:
        return Response(
            success=False,
            message=f"安装Skill失败: {str(e)}",
            data=None,
        )


@router.post("/uninstall", response_model=Response)
async def uninstall_skill(request: SkillUninstallRequest):
    """
    卸载指定skill

    - **skill_name**: 要卸载的skill名称
    - 注意：内置skill无法卸载
    """
    if not request.skill_name:
        return Response(
            success=False,
            message="请提供要卸载的skill_name",
            data=None,
        )

    try:
        result = SkillService.uninstall_skill(request.skill_name)

        if result["success"]:
            return Response(
                success=True,
                message=result["message"],
                data={"uninstalled": True},
            )
        else:
            return Response(
                success=False,
                message=result["message"],
                data={"uninstalled": False},
            )

    except Exception as e:
        return Response(
            success=False,
            message=f"卸载Skill失败: {str(e)}",
            data=None,
        )


@router.get("/builtin/list", response_model=Response)
async def list_builtin_skills():
    """
    获取内置skill列表

    返回所有内置的skill，这些skill不可卸载。
    """
    try:
        builtin_skills = SkillService.BUILTIN_SKILLS
        return Response(
            success=True,
            message="获取内置Skills成功",
            data={
                "skills": builtin_skills,
                "total": len(builtin_skills),
            },
        )
    except Exception as e:
        return Response(
            success=False,
            message=f"获取内置Skills失败: {str(e)}",
            data={"skills": [], "total": 0},
        )
