"""
知识图谱 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

from app.core.database import get_db
from app.api.deps import get_engine_manager, get_current_student_id
from app.services.engine_manager import EngineManager
from app.schemas import GenerateGraphRequest, GraphVisualizeResponse, Response
from app.models.node_mastery import NodeMastery
from app.models.study_goal import StudyGoal
from app.models.student import Student
from app.services.cancel_manager import request_cancel, GenerationCancelledError


router = APIRouter()


# ============ 取消知识图谱生成 =============

@router.post("/cancel-generation", response_model=Response)
async def cancel_graph_generation():
    """
    取消当前正在进行的知识图谱生成
    
    发送取消信号，生成过程会在下一个检查点停止
    """
    try:
        request_cancel()
        return Response(
            success=True,
            message="取消请求已发送"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消失败: {str(e)}")


# ============ 根据学习目标生成图谱（分层生成）============

@router.post("/goal/{goal_id}/generate", response_model=Response)
async def generate_graph_from_goal(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    分层分块生成知识图谱（无参考教材时的增强策略）
    
    策略流程：
    1. 第一步：调用模型将主题拆分为 6-12 个类别
    2. 第二步：分别为每个类别生成子知识图谱（根据学习深度调整数量）
    3. 第三步：调用模型融合所有子图谱，去重、补漏、优化关系
    """
    # 获取学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 检查是否已有知识图谱
    if goal.knowledge_graphs:
        return Response(
            success=True,
            message="该学习目标已有知识图谱",
            data={
                "graph_id": goal.knowledge_graphs[0].id,
                "title": goal.knowledge_graphs[0].title,
                "total_nodes": goal.knowledge_graphs[0].total_nodes,
                "estimated_hours": goal.knowledge_graphs[0].estimated_hours
            }
        )
    
    # 获取学生背景信息
    student = db.query(Student).filter(Student.id == current_student_id).first()
    student_background = student.background if student else {}
    
    # 获取学习深度
    study_depth = goal.study_depth or "intermediate"
    
    # 构建学习目标信息
    study_goal_info = {
        "title": goal.title,
        "subject": goal.subject,
        "description": goal.description,
        "student_level": student_background.get("level", "intermediate"),
        "study_goal_id": goal_id
    }
    
    try:
        graph = await engine_manager.knowledge_graph_engine.generate_graph_from_goal(
            study_goal=study_goal_info,
            student_background=student_background,
            study_depth=study_depth
        )
        
        # 更新学习目标的知识点数量
        goal.total_knowledge_points = graph.total_nodes
        db.commit()
        
        return Response(
            success=True,
            message="知识图谱（分层生成）生成成功",
            data={
                "graph_id": graph.id,
                "title": graph.title,
                "total_nodes": graph.total_nodes,
                "total_edges": graph.total_edges,
                "estimated_hours": graph.estimated_hours,
                "categories": list(set([node.get("category", "核心概念") for node in graph.nodes]))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成知识图谱失败: {str(e)}")


@router.post("/goal/{goal_id}/generate-from-materials", response_model=Response)
async def generate_graph_from_materials(
    goal_id: int,
    material_ids: Optional[List[int]] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    根据用户上传的学习资料生成知识图谱
    
    如果用户上传了学习资料（PDF、Word、PPT等），会从这些资料中提取知识点和依赖关系。
    
    ## 参数
    - material_ids: 可选，指定要使用的学习资料ID列表。如果为空，则使用学习目标关联的所有用户上传资料。
    
    ## 处理策略
    - **扫描版PDF**: 转换为图片，使用多模态模型（支持视觉的Ollama模型）提取知识点
    - **其他PDF/Word/PPT**: 提取文字，分批使用文本模型提取知识点
    - 图片和文字分批处理后合并去重
    """
    # 获取学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 检查是否有学习资料
    from app.models.study_material import StudyMaterial
    materials_query = db.query(StudyMaterial).filter(
        StudyMaterial.study_goal_id == goal_id,
        StudyMaterial.source.in_(["user", "imported"])
    )
    
    if material_ids:
        materials_query = materials_query.filter(StudyMaterial.id.in_(material_ids))
    
    materials = materials_query.all()
    
    if not materials:
        # 没有学习资料，回退到普通模式
        print("未找到学习资料，回退到普通知识图谱生成模式")
        return await generate_graph_from_goal(goal_id, current_student_id, db, engine_manager)
    
    # 检查是否已有知识图谱（可以强制重新生成，或者返回已有图谱）
    # 这里选择：如果已有图谱，询问用户是否重新生成
    if goal.knowledge_graphs and not material_ids:
        return Response(
            success=True,
            message="该学习目标已有知识图谱，如需基于新资料重新生成，请指定material_ids",
            data={
                "graph_id": goal.knowledge_graphs[0].id,
                "title": goal.knowledge_graphs[0].title,
                "total_nodes": goal.knowledge_graphs[0].total_nodes,
                "estimated_hours": goal.knowledge_graphs[0].estimated_hours,
                "has_materials": True,
                "material_count": len(materials)
            }
        )
    
    # 获取学生背景信息
    student = db.query(Student).filter(Student.id == current_student_id).first()
    student_background = student.background if student else {}
    
    # 获取学习深度
    study_depth = goal.study_depth or "intermediate"
    
    # 构建学习目标信息
    study_goal_info = {
        "title": goal.title,
        "subject": goal.subject,
        "description": goal.description,
        "student_level": student_background.get("level", "intermediate"),
        "study_goal_id": goal_id
    }
    
    try:
        print(f"开始基于 {len(materials)} 个学习资料生成知识图谱...")
        
        graph = await engine_manager.knowledge_graph_engine.generate_graph_from_materials(
            study_goal=study_goal_info,
            student_background=student_background,
            material_ids=material_ids,
            study_depth=study_depth
        )
        
        # 更新学习目标的知识点数量
        goal.total_knowledge_points = graph.total_nodes
        db.commit()
        
        # 获取资料类型统计
        material_types = {}
        for m in materials:
            doc_type = m.file_format or "unknown"
            material_types[doc_type] = material_types.get(doc_type, 0) + 1
        
        return Response(
            success=True,
            message="基于学习资料的知识图谱生成成功",
            data={
                "graph_id": graph.id,
                "title": graph.title,
                "total_nodes": graph.total_nodes,
                "total_edges": graph.total_edges,
                "estimated_hours": graph.estimated_hours,
                "materials_used": len(materials),
                "material_types": material_types,
                "categories": list(set([node.get("category", "核心概念") for node in graph.nodes]))
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"基于学习资料生成知识图谱失败: {str(e)}")


@router.post("/goal/{goal_id}/generate-from-materials/stream")
async def generate_graph_from_materials_stream(
    goal_id: int,
    material_ids: Optional[List[int]] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    基于学习资料生成知识图谱（SSE流式版本）
    
    通过Server-Sent Events实时推送处理进度：
    - 加载文档进度
    - 处理文档进度（分批）
    - 生成知识图谱进度
    - 最终完成结果
    """
    # 重置取消状态，确保新请求不受上次取消的影响
    from app.services.cancel_manager import reset_cancel
    reset_cancel()
    
    async def generate_stream():
        try:
            # 获取学习目标
            goal = db.query(StudyGoal).filter(
                StudyGoal.id == goal_id,
                StudyGoal.student_id == current_student_id
            ).first()
            
            if not goal:
                yield f"data: {json.dumps({'error': '学习目标不存在'}, ensure_ascii=False)}\n\n"
                return
            
            # 检查学习资料
            from app.models.study_material import StudyMaterial
            materials_query = db.query(StudyMaterial).filter(
                StudyMaterial.study_goal_id == goal_id
            )
            
            if material_ids:
                materials_query = materials_query.filter(StudyMaterial.id.in_(material_ids))
            
            materials = materials_query.all()
            
            if not materials:
                # 没有学习资料，回退到普通模式
                yield f"data: {json.dumps({
                    'status': 'fallback',
                    'message': '未找到学习资料，回退到普通模式'
                }, ensure_ascii=False)}\n\n"
                return
            
            # 获取学生背景信息
            student = db.query(Student).filter(Student.id == current_student_id).first()
            student_background = student.background if student else {}
            
            # 获取学习深度
            study_depth = goal.study_depth or "intermediate"
            
            # 构建学习目标信息
            study_goal_info = {
                "title": goal.title,
                "subject": goal.subject,
                "description": goal.description,
                "student_level": student_background.get("level", "intermediate"),
                "study_goal_id": goal_id
            }
            
            # 创建引擎管理器
            engine_manager = get_engine_manager(db)
            
            # 创建 asyncio.Queue 用于进度回调
            progress_queue = asyncio.Queue()
            
            async def progress_callback(data: dict):
                """进度回调函数 - 将进度数据放入队列"""
                await progress_queue.put(data)
            
            # 启动生成任务
            generate_task = asyncio.create_task(
                engine_manager.knowledge_graph_engine.generate_graph_from_materials(
                    study_goal=study_goal_info,
                    student_background=student_background,
                    material_ids=material_ids,
                    progress_callback=progress_callback,
                    study_depth=study_depth
                )
            )
            
            # 从队列消费进度消息并 yield
            while not generate_task.done():
                try:
                    data = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    continue
            
            # 处理队列中剩余的消息
            while not progress_queue.empty():
                data = await progress_queue.get()
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            # 获取生成结果
            try:
                graph = generate_task.result()
                
                # 更新学习目标的知识点数量
                goal.total_knowledge_points = graph.total_nodes
                db.commit()
                
                # 获取资料类型统计
                material_types = {}
                for m in materials:
                    doc_type = m.file_format or "unknown"
                    material_types[doc_type] = material_types.get(doc_type, 0) + 1
                
                # 发送完成结果
                yield f"data: {json.dumps({
                    'status': 'completed',
                    'progress': 100,
                    'message': '知识图谱生成完成！',
                    'result': {
                        'graph_id': graph.id,
                        'title': graph.title,
                        'total_nodes': graph.total_nodes,
                        'total_edges': graph.total_edges,
                        'estimated_hours': graph.estimated_hours,
                        'materials_used': len(materials),
                        'material_types': material_types,
                        'categories': list(set([node.get("category", "核心概念") for node in json.loads(graph.nodes)])) if isinstance(graph.nodes, str) else []
                    },
                    'totalNodes': graph.total_nodes,
                    'totalEdges': graph.total_edges
                }, ensure_ascii=False)}\n\n"
                
            except GenerationCancelledError as e:
                print(f"生成被用户取消: {e}")
                yield f"data: {json.dumps({
                    'status': 'cancelled',
                    'error': '用户取消了生成'
                }, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({
                    'status': 'error',
                    'error': str(e)
                }, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/goal/{goal_id}/generate/stream")
async def generate_graph_from_goal_stream(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    分层分块生成知识图谱（SSE流式版本）
    
    策略流程：
    1. 第一步：调用模型将主题拆分为 6-12 个类别
    2. 第二步：分别为每个类别生成子知识图谱（根据学习深度调整数量）
    3. 第三步：调用模型融合所有子图谱，去重、补漏、优化关系
    
    通过Server-Sent Events实时推送处理进度：
    - decomposing_categories: 正在分析知识结构
    - generating_sub_graphs: 正在为各类别生成知识点
    - integrating_graph: 正在整合图谱
    - saving_graph: 正在保存
    - completed: 完成
    """
    # 重置取消状态，确保新请求不受上次取消的影响
    from app.services.cancel_manager import reset_cancel
    reset_cancel()
    
    async def generate_stream():
        try:
            # 获取学习目标
            goal = db.query(StudyGoal).filter(
                StudyGoal.id == goal_id,
                StudyGoal.student_id == current_student_id
            ).first()
            
            if not goal:
                yield f"data: {json.dumps({'error': '学习目标不存在'}, ensure_ascii=False)}\n\n"
                return
            
            # 获取学生背景信息
            student = db.query(Student).filter(Student.id == current_student_id).first()
            student_background = student.background if student else {}
            
            # 获取学习深度
            study_depth = goal.study_depth or "intermediate"
            
            # 构建学习目标信息
            study_goal_info = {
                "title": goal.title,
                "subject": goal.subject,
                "description": goal.description,
                "student_level": student_background.get("level", "intermediate"),
                "study_goal_id": goal_id
            }
            
            # 创建引擎管理器
            engine_manager = get_engine_manager(db)
            
            # 创建 asyncio.Queue 用于进度回调
            progress_queue = asyncio.Queue()
            
            async def progress_callback(data: dict):
                """进度回调函数 - 将进度数据放入队列"""
                await progress_queue.put(data)
            
            # 启动生成任务
            generate_task = asyncio.create_task(
                engine_manager.knowledge_graph_engine.generate_graph_from_goal(
                    study_goal=study_goal_info,
                    student_background=student_background,
                    progress_callback=progress_callback,
                    study_depth=study_depth
                )
            )
            
            # 从队列消费进度消息并 yield
            while not generate_task.done():
                try:
                    data = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    continue
            
            # 处理队列中剩余的消息
            while not progress_queue.empty():
                data = await progress_queue.get()
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            # 获取生成结果
            try:
                graph = generate_task.result()
                
                # 更新学习目标的知识点数量
                goal.total_knowledge_points = graph.total_nodes
                db.commit()
                
                # 发送完成结果
                yield f"data: {json.dumps({
                    'status': 'completed',
                    'progress': 100,
                    'message': f'知识图谱生成完成！共 {graph.total_nodes} 个知识点',
                    'result': {
                        'graph_id': graph.id,
                        'title': graph.title,
                        'total_nodes': graph.total_nodes,
                        'total_edges': graph.total_edges,
                        'estimated_hours': graph.estimated_hours,
                        'categories': list(set([node.get("category", "核心概念") for node in json.loads(graph.nodes)])) if isinstance(graph.nodes, str) else []
                    },
                    'totalNodes': graph.total_nodes,
                    'totalEdges': graph.total_edges
                }, ensure_ascii=False)}\n\n"
                
            except GenerationCancelledError as e:
                print(f"生成被用户取消: {e}")
                yield f"data: {json.dumps({
                    'status': 'cancelled',
                    'error': '用户取消了生成'
                }, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({
                    'status': 'error',
                    'error': str(e)
                }, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/generate", response_model=Response)
async def generate_knowledge_graph(
    request: GenerateGraphRequest,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    生成知识图谱
    
    ## 功能说明
    - 将模糊的学习目标拆解为结构化知识图谱
    - 根据学生背景动态调整图谱粒度
    - 返回可视化数据格式（ECharts）
    
    ## 示例
    ```json
    {
      "topic": "人工智能",
      "student_background": {
        "has_programming_experience": true,
        "math_level": "high_school"
      }
    }
    ```
    """
    try:
        graph = await engine_manager.knowledge_graph_engine.generate_graph(
            topic=request.topic,
            student_background=request.student_background,
            title=request.title,
            description=request.description
        )
        
        return Response(
            success=True,
            message="知识图谱生成成功",
            data={
                "graph_id": graph.id,
                "title": graph.title,
                "total_nodes": graph.total_nodes,
                "estimated_hours": graph.estimated_hours
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{graph_id}", response_model=Response)
async def get_knowledge_graph(
    graph_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """获取知识图谱详情"""
    graph = engine_manager.knowledge_graph_engine.get_graph(graph_id)
    
    if not graph:
        raise HTTPException(status_code=404, detail="知识图谱不存在")
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "id": graph.id,
            "title": graph.title,
            "description": graph.description,
            "total_nodes": graph.total_nodes,
            "total_edges": graph.total_edges,
            "estimated_hours": graph.estimated_hours
        }
    )


@router.get("/goal/{goal_id}/visualize", response_model=Response)
async def visualize_goal_knowledge_graph(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db),
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取学习目标的知识图谱可视化数据（带掌握度）
    
    返回可直接用于 ECharts 渲染的 nodes 和 edges 数据
    节点颜色根据5级掌握度变化：
    - 萌芽 (0%): 灰色
    - 入门 (1-20%): 蓝色
    - 发展 (21-40%): 浅蓝
    - 理解 (41-60%): 黄色
    - 熟练 (61-80%): 橙色
    - 精通 (81-100%): 绿色
    """
    # 获取学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取知识图谱
    if not goal.knowledge_graphs:
        raise HTTPException(status_code=404, detail="知识图谱不存在")
    
    graph = goal.knowledge_graphs[0]
    
    # 获取掌握度数据
    masteries = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id
    ).all()
    
    mastery_map = {m.node_id: m.mastery_level for m in masteries}
    
    # 解析 JSON 数据
    import json
    # 确保 nodes 和 edges 是列表格式
    if isinstance(graph.nodes, str):
        graph_nodes = json.loads(graph.nodes)
    else:
        graph_nodes = graph.nodes
    
    if isinstance(graph.edges, str):
        graph_edges = json.loads(graph.edges)
    else:
        graph_edges = graph.edges
    
    # 构建可视化数据
    nodes = []
    for node in graph_nodes:
        node_id = node.get('id')
        mastery = mastery_map.get(node_id, 0)
        
        # 根据掌握度计算颜色和状态
        color, status, status_key = get_mastery_info(mastery)
        
        nodes.append({
            "id": node_id,
            "name": node.get('label', node.get('name', node_id)),
            "category": node.get('category', '核心概念'),
            "difficulty": node.get('difficulty', 'intermediate'),
            "description": node.get('description', ''),
            "prerequisites": node.get('prerequisites', []),
            "mastery": mastery,
            "masteryName": status,
            "masteryKey": status_key,
            "symbolSize": get_symbol_size(node, mastery),
            "itemStyle": {"color": color},
            "value": mastery
        })
    
    edges = [
        {
            "source": edge.get('source'),
            "target": edge.get('target'),
            "relation": edge.get('relation', '')
        }
        for edge in graph_edges
    ]
    
    # 统计各等级数量
    mastery_stats = calculate_mastery_stats(nodes)
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "goal_id": goal_id,
            "title": graph.title,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "categories": list(set([n.get('category', '核心概念') for n in nodes])),
            "mastery_stats": mastery_stats
        }
    )


@router.get("/{graph_id}/visualize", response_model=Response)
async def visualize_knowledge_graph(
    graph_id: int,
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    获取知识图谱可视化数据（ECharts 格式）
    
    返回可直接用于 ECharts 渲染的 nodes 和 edges 数据
    """
    viz_data = engine_manager.knowledge_graph_engine.get_graph_for_visualization(graph_id)
    
    if not viz_data:
        raise HTTPException(status_code=404, detail="知识图谱不存在")
    
    return Response(
        success=True,
        message="获取成功",
        data=viz_data
    )


@router.put("/{graph_id}/mastery", response_model=Response)
async def update_mastery_map(
    graph_id: int,
    node_mastery: Dict[str, float],
    engine_manager: EngineManager = Depends(get_engine_manager)
):
    """
    更新知识图谱掌握度热力图
    
    ## 参数
    - node_mastery: {node_id: mastery_level} 掌握度字典
    """
    updated_data = engine_manager.knowledge_graph_engine.update_graph_mastery(
        graph_id=graph_id,
        node_mastery=node_mastery
    )
    
    return Response(
        success=True,
        message="更新成功",
        data=updated_data
    )


def get_mastery_info(mastery: float) -> tuple:
    """
    根据掌握度返回颜色、状态名称和状态键
    
    Returns:
        (color, status_name, status_key)
    """
    if mastery >= 81:
        return "#52c41a", "精通", "mastered"
    elif mastery >= 61:
        return "#fa8c16", "熟练", "proficient"
    elif mastery >= 41:
        return "#fadb14", "理解", "understanding"
    elif mastery >= 21:
        return "#40a9ff", "发展", "developing"
    elif mastery >= 1:
        return "#1890ff", "入门", "learning"
    else:
        return "#d9d9d9", "萌芽", "sprouting"


def get_symbol_size(node: dict, mastery: float) -> int:
    """
    根据节点难度和掌握度计算节点大小
    """
    difficulty = node.get('difficulty', 'intermediate')
    base_size = {
        "foundation": 28,
        "intermediate": 35,
        "advanced": 42,
        "expert": 50
    }.get(difficulty, 35)
    
    # 掌握度越高，节点稍微变大
    size = base_size + (mastery / 100) * 10
    return int(size)


def calculate_mastery_stats(nodes: list) -> dict:
    """
    计算掌握度统计
    """
    stats = {
        "total": len(nodes),
        "sprouting": 0,
        "learning": 0,
        "developing": 0,
        "understanding": 0,
        "proficient": 0,
        "mastered": 0
    }
    
    for node in nodes:
        mastery = node.get("mastery", 0)
        key = get_mastery_info(mastery)[2]
        stats[key] += 1
    
    return stats


@router.post("/goal/{goal_id}/assess", response_model=Response)
async def submit_assessment(
    goal_id: int,
    assessments: List[dict],  # [{"node_id": "xxx", "score": 80, "node_name": "xxx"}]
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    提交测评结果，更新知识点掌握度
    
    ## 参数
    - assessments: 测评结果列表
      - node_id: 知识点ID
      - score: 得分 0-100
      - node_name: 知识点名称
    
    ## 掌握度等级说明
    - 精通 (81-100): 完全掌握，可以灵活应用
    - 熟练 (61-80): 较好掌握，能够独立完成
    - 理解 (41-60): 基本理解，需要巩固练习
    - 发展 (21-40): 初步了解，需要深入学习
    - 入门 (1-20): 刚刚接触，需要从基础开始
    - 萌芽 (0): 尚未开始学习
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    updated_count = 0
    for assessment in assessments:
        node_id = assessment.get('node_id')
        score = assessment.get('score', 0)
        node_name = assessment.get('node_name', '')
        
        # 查找或创建掌握度记录
        mastery = db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == current_student_id,
            NodeMastery.node_id == node_id
        ).first()
        
        if not mastery:
            mastery = NodeMastery(
                student_id=current_student_id,
                study_goal_id=goal_id,
                node_id=node_id,
                node_name=node_name,
                mastery_level=score,
                total_attempts=1,
                correct_attempts=1 if score >= 60 else 0,
                last_assessment_score=score,
                last_assessment_at=datetime.utcnow()
            )
            db.add(mastery)
        else:
            # 更新掌握度（加权平均，最近的成绩权重更高）
            old_mastery = mastery.mastery_level
            # 使用指数加权平均，最近的成绩权重更大
            weight = 0.4  # 新成绩权重
            mastery.mastery_level = old_mastery * (1 - weight) + score * weight
            mastery.total_attempts += 1
            if score >= 60:
                mastery.correct_attempts += 1
            mastery.last_assessment_score = score
            mastery.last_assessment_at = datetime.utcnow()
        
        updated_count += 1
    
    # 更新学习目标的已掌握知识点数（精通级别）
    mastered_count = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id,
        NodeMastery.mastery_level >= 81
    ).count()
    
    goal.mastered_points = mastered_count
    db.commit()
    
    return Response(
        success=True,
        message=f"已更新 {updated_count} 个知识点的掌握度",
        data={
            "updated_count": updated_count,
            "mastered_points": mastered_count,
            "mastery_levels": {
                "精通": db.query(NodeMastery).filter(
                    NodeMastery.study_goal_id == goal_id,
                    NodeMastery.student_id == current_student_id,
                    NodeMastery.mastery_level >= 81
                ).count(),
                "熟练": db.query(NodeMastery).filter(
                    NodeMastery.study_goal_id == goal_id,
                    NodeMastery.student_id == current_student_id,
                    NodeMastery.mastery_level >= 61,
                    NodeMastery.mastery_level < 81
                ).count(),
                "理解": db.query(NodeMastery).filter(
                    NodeMastery.study_goal_id == goal_id,
                    NodeMastery.student_id == current_student_id,
                    NodeMastery.mastery_level >= 41,
                    NodeMastery.mastery_level < 61
                ).count(),
                "发展": db.query(NodeMastery).filter(
                    NodeMastery.study_goal_id == goal_id,
                    NodeMastery.student_id == current_student_id,
                    NodeMastery.mastery_level >= 21,
                    NodeMastery.mastery_level < 41
                ).count(),
                "入门": db.query(NodeMastery).filter(
                    NodeMastery.study_goal_id == goal_id,
                    NodeMastery.student_id == current_student_id,
                    NodeMastery.mastery_level >= 1,
                    NodeMastery.mastery_level < 21
                ).count(),
                "萌芽": db.query(NodeMastery).filter(
                    NodeMastery.study_goal_id == goal_id,
                    NodeMastery.student_id == current_student_id,
                    NodeMastery.mastery_level < 1
                ).count()
            }
        }
    )


@router.get("/goal/{goal_id}/nodes/{node_id}/mastery", response_model=Response)
async def get_node_mastery(
    goal_id: int,
    node_id: str,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """获取特定知识点的掌握度详情"""
    mastery = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == current_student_id,
        NodeMastery.node_id == node_id
    ).first()
    
    if not mastery:
        # 判断是否完全不存在或是萌芽状态
        all_masteries = db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == current_student_id
        ).all()
        
        return Response(
            success=True,
            message="该知识点尚未开始学习",
            data={
                "node_id": node_id,
                "mastery_level": 0,
                "masteryName": "萌芽",
                "masteryKey": "sprouting",
                "status": "not_started",
                "attempts": 0
            }
        )
    
    # 根据掌握度确定状态
    level = mastery.mastery_level
    if level >= 81:
        status_name, status_key = "精通", "mastered"
    elif level >= 61:
        status_name, status_key = "熟练", "proficient"
    elif level >= 41:
        status_name, status_key = "理解", "understanding"
    elif level >= 21:
        status_name, status_key = "发展", "developing"
    elif level >= 1:
        status_name, status_key = "入门", "learning"
    else:
        status_name, status_key = "萌芽", "sprouting"
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "node_id": node_id,
            "node_name": mastery.node_name,
            "mastery_level": round(mastery.mastery_level, 1),
            "masteryName": status_name,
            "masteryKey": status_key,
            "status": status_key,
            "attempts": mastery.total_attempts,
            "correct_attempts": mastery.correct_attempts,
            "last_score": mastery.last_assessment_score,
            "last_attempted": mastery.last_assessment_at.isoformat() if mastery.last_assessment_at else None
        }
    )
