"""
知识图谱引擎 - 智能拆解学习目标，生成可视化知识图谱
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import asyncio
import json
import os

from app.models.knowledge_graph import KnowledgeGraph, KnowledgeNode
from app.models.study_material import StudyMaterial
from app.services.ai_model_provider import AIModelProvider
from app.engines.document_processor import DocumentProcessor
from app.core.config import settings
from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError, reset_cancel


class KnowledgeGraphEngine:
    """知识图谱引擎"""
    
    def __init__(self, db: Session, ai_provider: AIModelProvider):
        self.db = db
        self.ai_provider = ai_provider
    
    async def generate_graph_from_goal(
        self, 
        study_goal: dict,
        student_background: Optional[dict] = None,
        progress_callback=None,
        study_depth: str = "intermediate"
    ) -> KnowledgeGraph:
        """
        根据学习目标生成知识图谱（无参考教材时）
        
        策略流程：
        1. 第一步：调用模型将主题拆分为 6-12 个类别
        2. 第二步：分别为每个类别生成子知识图谱
           - basic(了解): 每类 5 个知识点左右
           - intermediate(熟悉): 每类 10 个知识点左右
           - advanced(深入): 每类 15 个知识点以上
        3. 第三步：调用模型融合所有子图谱，去重、补漏、优化关系
        
        Args:
            study_goal: 学习目标信息，包含 title, subject, description
            student_background: 学生背景信息
            progress_callback: 进度回调函数
            study_depth: 学习深度 (basic/intermediate/advanced)
            
        Returns:
            KnowledgeGraph: 生成的知识图谱对象
        """
        # 根据学习深度确定每类知识点数量范围
        depth_config = {
            "basic": {"min": 4, "max": 6, "target": 5},       # 了解: 每类5个左右
            "intermediate": {"min": 8, "max": 12, "target": 10},  # 熟悉: 每类10个左右
            "advanced": {"min": 13, "max": 18, "target": 15}  # 深入: 每类15个以上
        }
        nodes_config = depth_config.get(study_depth, depth_config["intermediate"])
        
        # 构建 AI 上下文
        context = {
            "subject": study_goal.get("subject", ""),
            "description": study_goal.get("description", ""),
            "student_level": study_goal.get("student_level", "intermediate"),
            "study_depth": study_depth,
            **(student_background or {})
        }
        
        topic = study_goal.get("title", "")
        study_goal_id = study_goal.get("study_goal_id")
        
        # 重置取消状态
        reset_cancel()
        
        # ===== 第一步：拆分主题为类别 =====
        if progress_callback:
            await progress_callback({
                "status": "decomposing_categories",
                "progress": 5,
                "message": f"正在分析「{topic}」的知识结构..."
            })
        
        categories_result = await self.ai_provider.decompose_into_categories(
            topic=topic,
            context=context
        )
        
        categories = categories_result.get("categories", [])
        if len(categories) < 6:
            print(f"警告：类别数量不足({len(categories)}个)，期望6-12个")
            # 如果类别太少，回退到普通模式
            if len(categories) < 3:
                print("类别数量过少，回退到普通生成模式")
                return await self.generate_graph_from_goal(study_goal, student_background)
        
        print(f"[分层生成] 第一步完成：将「{topic}」拆分为 {len(categories)} 个类别")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.get('name', '')}: {cat.get('scope', '')[:30]}...")
        
        # ===== 第二步：为每个类别生成子知识图谱 =====
        if progress_callback:
            await progress_callback({
                "status": "generating_sub_graphs",
                "progress": 15,
                "message": f"开始为 {len(categories)} 个类别生成知识点...",
                "total_categories": len(categories),
                "current_category": 0
            })
        
        # 判断是否使用云端API（云端支持并行，本地Ollama串行更稳定）
        is_cloud_api = not self.ai_provider.is_ollama()
        
        if is_cloud_api:
            # ===== 云端API：并行生成所有类别的子图谱 =====
            print(f"[分层生成] 使用云端API，并行生成 {len(categories)} 个类别的子图谱")
            
            max_concurrent = 5  # 云端API：最大5并发
            semaphore = asyncio.Semaphore(max_concurrent)
            lock = asyncio.Lock()
            is_cancelled = False
            completed_count = 0
            
            async def generate_single_category(category: dict, index: int) -> dict:
                """为单个类别生成子知识图谱"""
                nonlocal is_cancelled, completed_count
                
                async with semaphore:
                    if is_cancelled:
                        return {"category_index": index, "nodes": [], "edges": [], "skipped": True}
                    
                    cat_name = category.get('name', f'类别{index+1}')
                    print(f"[分层生成] 并行 [{index+1}/{len(categories)}]：为「{cat_name}」生成子图谱")
                    
                    try:
                        # 检查是否已取消
                        await wait_if_cancelled()
                        
                        sub_graph = await self.ai_provider.generate_sub_graph(
                            category=category,
                            topic=topic,
                            context=context,
                            study_depth=study_depth
                        )
                        
                        # 检查是否已取消
                        await wait_if_cancelled()
                        
                        sub_nodes = sub_graph.get("nodes", [])
                        sub_edges = sub_graph.get("edges", [])
                        print(f"  生成 {len(sub_nodes)} 个知识点，{len(sub_edges)} 条边")
                        
                        async with lock:
                            completed_count += 1
                            if progress_callback:
                                await progress_callback({
                                    "status": "generating_sub_graphs",
                                    "progress": int(15 + (completed_count / len(categories)) * 50),
                                    "message": f"正在生成「{cat_name}」的知识图谱...",
                                    "total_categories": len(categories),
                                    "current_category": completed_count
                                })
                        
                        return {"category_index": index, "nodes": sub_nodes, "edges": sub_edges, "skipped": False}
                        
                    except GenerationCancelledError:
                        is_cancelled = True
                        print(f"[分层生成] 检测到取消，停止生成")
                        return {"category_index": index, "nodes": [], "edges": [], "skipped": True}
                    except Exception as e:
                        print(f"[分层生成] 类别「{cat_name}」生成失败: {e}")
                        return {"category_index": index, "nodes": [], "edges": [], "skipped": True}
            
            # 并行执行所有类别的生成任务
            tasks = [generate_single_category(cat, i) for i, cat in enumerate(categories)]
            results = await asyncio.gather(*tasks)
            
            # 收集所有结果
            all_nodes = []
            all_edges = []
            for result in sorted(results, key=lambda x: x.get("category_index", 0)):
                all_nodes.extend(result.get("nodes", []))
                all_edges.extend(result.get("edges", []))
            
        else:
            # ===== 本地Ollama：串行生成（更稳定） =====
            print(f"[分层生成] 使用本地Ollama模型，串行生成 {len(categories)} 个类别的子图谱")
            
            all_nodes = []
            all_edges = []
            
            for i, category in enumerate(categories):
                # 检查是否已取消
                await wait_if_cancelled()
                
                cat_name = category.get('name', f'类别{i+1}')
                
                if progress_callback:
                    await progress_callback({
                        "status": "generating_sub_graphs",
                        "progress": int(15 + (i / len(categories)) * 50),
                        "message": f"正在生成「{cat_name}」的知识图谱...",
                        "total_categories": len(categories),
                        "current_category": i + 1
                    })
                
                print(f"[分层生成] 串行 [{i+1}/{len(categories)}]：为「{cat_name}」生成子图谱")
                
                # 为单个类别生成子知识图谱（根据学习深度调整知识点数量）
                sub_graph = await self.ai_provider.generate_sub_graph(
                    category=category,
                    topic=topic,
                    context=context,
                    study_depth=study_depth
                )
                
                # 调用后立即检查取消
                await wait_if_cancelled()
                
                sub_nodes = sub_graph.get("nodes", [])
                sub_edges = sub_graph.get("edges", [])
                
                print(f"  生成 {len(sub_nodes)} 个知识点，{len(sub_edges)} 条边")
                
                all_nodes.extend(sub_nodes)
                all_edges.extend(sub_edges)
        
        print(f"[分层生成] 第二步完成：共生成 {len(all_nodes)} 个知识点，{len(all_edges)} 条边")
        
        # ===== 第三步：AI智能融合所有子图谱 =====
        if progress_callback:
            await progress_callback({
                "status": "integrating_graph",
                "progress": 70,
                "message": "正在整合所有知识图谱..."
            })
        
        # 先进行初步合并去重
        merged_graph = self._merge_sub_graphs(
            {"nodes": all_nodes, "edges": all_edges},
            topic
        )
        
        # 调用 AI 进行深度融合
        if len(merged_graph.get("nodes", [])) >= 5:
            merged_graph = await self._integrate_sub_graphs_with_ai(
                merged_graph,
                categories,
                study_goal,
                progress_callback
            )
        
        nodes = merged_graph.get("nodes", [])
        edges = merged_graph.get("edges", [])
        
        # 校验节点数量
        if len(nodes) < 5:
            raise ValueError(
                f"融合后知识图谱节点数量不足：期望至少5个节点，实际{len(nodes)}个"
            )
        
        # 过滤不相关节点
        filtered_nodes = self._filter_irrelevant_nodes(nodes, topic)
        if len(filtered_nodes) < len(nodes):
            print(f"[分层生成] 过滤了 {len(nodes) - len(filtered_nodes)} 个不相关节点")
            nodes = filtered_nodes
            # 同步过滤边
            node_ids = {n.get("id") for n in nodes}
            edges = [e for e in edges if e.get("source") in node_ids and e.get("target") in node_ids]
        
        # 再次校验
        if len(nodes) < 5:
            raise ValueError(f"过滤后节点数量不足：{len(nodes)}个")
        
        # 计算元数据
        estimated_hours = sum(node.get("estimated_hours", 1.0) for node in nodes)
        
        # 根据学生背景调整
        adjusted_nodes = self._adjust_for_student(nodes, context)
        
        # ===== 保存知识图谱 =====
        if progress_callback:
            await progress_callback({
                "status": "saving_graph",
                "progress": 95,
                "message": "正在保存知识图谱..."
            })
        
        knowledge_graph = KnowledgeGraph(
            study_goal_id=study_goal_id,
            title=f"{topic}知识图谱（分层生成）",
            description=study_goal.get("description", f"针对「{topic}」学习的完整知识路径"),
            nodes=json.dumps(adjusted_nodes, ensure_ascii=False),
            edges=json.dumps(edges, ensure_ascii=False),
            total_nodes=len(adjusted_nodes),
            total_edges=len(edges),
            estimated_hours=estimated_hours
        )
        
        self.db.add(knowledge_graph)
        self.db.commit()
        self.db.refresh(knowledge_graph)
        
        # 保存知识点详情
        self._save_knowledge_nodes(knowledge_graph.id, adjusted_nodes)
        
        if progress_callback:
            await progress_callback({
                "status": "completed",
                "progress": 100,
                "message": f"知识图谱生成完成！共 {len(adjusted_nodes)} 个知识点"
            })
        
        print(f"[分层生成] 完成！最终图谱包含 {len(adjusted_nodes)} 个知识点，{len(edges)} 条边")
        
        return knowledge_graph

    def _merge_sub_graphs(
        self,
        graph_data: dict,
        topic: str
    ) -> dict:
        """
        合并多个子知识图谱，初步去重
        
        Args:
            graph_data: 包含所有子图谱的节点和边
            topic: 学习主题
            
        Returns:
            合并后的图谱数据
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if not nodes:
            return {"nodes": [], "edges": []}
        
        # 按ID去重
        unique_nodes = {}
        for node in nodes:
            node_id = node.get("id", "")
            if node_id and node_id not in unique_nodes:
                unique_nodes[node_id] = node
        
        # 过滤边：只保留两端节点都存在的边
        valid_node_ids = set(unique_nodes.keys())
        valid_edges = []
        seen_edges = set()
        
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            
            if source in valid_node_ids and target in valid_node_ids:
                edge_key = f"{source}->{target}"
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    valid_edges.append(edge)
        
        return {
            "nodes": list(unique_nodes.values()),
            "edges": valid_edges
        }

    async def _integrate_sub_graphs_with_ai(
        self,
        graph_data: dict,
        categories: list,
        study_goal: dict,
        progress_callback=None
    ) -> dict:
        """
        使用 AI 深度融合所有子知识图谱
        
        融合策略：
        1. 分析所有节点和边
        2. 找出冗余的知识点并删除
        3. 发现遗漏的知识点并添加
        4. 发现遗漏的依赖关系并添加
        
        Args:
            graph_data: 合并后的图谱数据
            categories: 类别列表
            study_goal: 学习目标信息
            progress_callback: 进度回调
            
        Returns:
            融合后的高质量知识图谱
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        topic = study_goal.get("title", "")
        
        if len(nodes) < 5:
            return graph_data
        
        if progress_callback:
            await progress_callback({
                "status": "integrating_graph",
                "progress": 75,
                "message": "AI正在分析知识图谱..."
            })
        
        # 构建类别信息摘要
        category_summary = "\n".join([
            f"- {cat.get('id')}: {cat.get('name')}（{cat.get('scope', '')}）"
            for cat in categories
        ])
        
        # 构建节点摘要
        node_summaries = [
            {
                "id": n.get("id", ""),
                "name": n.get("name", ""),
                "category": n.get("category", ""),
                "difficulty": n.get("difficulty", ""),
                "importance": n.get("importance", "important")
            }
            for n in nodes[:200]  # 限制节点数量避免超出token限制
        ]
        
        # 构建边摘要
        edge_summaries = [
            {
                "source": e.get("source", ""),
                "target": e.get("target", ""),
                "relation": e.get("relation", "")
            }
            for e in edges[:300]  # 限制边数量
        ]
        
        system_prompt = """你是知识架构师，擅长分析和整合知识图谱。

## 你的任务
分析输入的知识图谱，找出以下问题并输出修改指令：

1. **冗余节点**：找出语义重复或高度相似的知识点，保留一个
2. **遗漏知识点**：找出应该在图中但缺失的重要知识点
3. **遗漏依赖**：找出重要知识点之间缺失的依赖关系

## 重要约束
- **节点上限**：420个，超过必须删除
- **只输出修改指令**：不要输出完整的节点和边列表

## 输出格式
```json
{
  "nodes_to_remove": ["要删除的节点ID列表"],
  "nodes_to_add": [
    {
      "id": "新节点ID（英文驼峰）",
      "name": "新节点名称（中文）",
      "description": "节点描述",
      "difficulty": "难度级别",
      "estimated_hours": 预计时长,
      "prerequisites": ["前置节点ID"],
      "category": "所属类别",
      "importance": "重要程度"
    }
  ],
  "edges_to_add": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型"
    }
  ],
  "analysis_summary": "分析总结（50字以上）"
}
```

## 边关系类型（8种）
前置依赖、组成关系、进阶关系、对立关系、对比关系、应用关系、等价关系、关联关系

## 删除优先级
1. 孤立节点（无任何边连接）
2. optional 重要性的节点
3. 重复/相似节点"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}

## 类别结构
{category_summary}

## 图谱统计
- 当前节点数：{len(nodes)}
- 当前边数：{len(edges)}
- 节点上限：420

## 所有节点概要
```json
{node_summaries}
```

## 所有边概要
```json
{edge_summaries}
```

## 你的任务
1. 分析孤立节点和重复节点，标记要删除的
2. 分析遗漏的重要知识点，输出要添加的
3. 分析缺失的依赖关系，输出要添加的边
4. 如果节点超过420个，必须标记删除

**重要**：nodes_to_add 和 edges_to_add 中的 ID 必须是新的或现有的，不要凭空创造ID！"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.ai_provider.chat(messages, temperature=0.7)
            
            # 解析响应
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response)
            
            nodes_to_remove = set(result.get("nodes_to_remove", []))
            nodes_to_add = result.get("nodes_to_add", [])
            edges_to_add = result.get("edges_to_add", [])
            analysis_summary = result.get("analysis_summary", "")
            
            print(f"[AI融合] {analysis_summary}")
            print(f"[AI融合] 删除 {len(nodes_to_remove)} 个冗余节点")
            print(f"[AI融合] 添加 {len(nodes_to_add)} 个遗漏节点")
            print(f"[AI融合] 添加 {len(edges_to_add)} 条遗漏边")
            
            # 执行修改
            modified_nodes = [n for n in nodes if n.get("id") not in nodes_to_remove]
            modified_nodes.extend(nodes_to_add)
            
            # 获取当前节点ID集合
            current_node_ids = {n.get("id") for n in modified_nodes}
            
            # 添加边（确保两端节点都存在）
            existing_edge_keys = {(e.get("source"), e.get("target")) for e in edges}
            new_edges = list(edges)
            
            for edge in edges_to_add:
                source = edge.get("source")
                target = edge.get("target")
                if source in current_node_ids and target in current_node_ids:
                    edge_key = (source, target)
                    if edge_key not in existing_edge_keys:
                        new_edges.append(edge)
                        existing_edge_keys.add(edge_key)
            
            # 自动精简（如果超过420个节点）
            if len(modified_nodes) > 420:
                print(f"[AI融合] 节点数量({len(modified_nodes)})超过上限，自动精简...")
                modified_nodes = self._auto_prune_nodes(modified_nodes, new_edges, topic)
            
            if progress_callback:
                await progress_callback({
                    "status": "integrating_graph",
                    "progress": 85,
                    "message": "图谱整合完成"
                })
            
            return {
                "nodes": modified_nodes,
                "edges": new_edges
            }
            
        except Exception as e:
            print(f"[AI融合] 融合失败: {e}，使用合并后的数据")
            import traceback
            traceback.print_exc()
            return graph_data

    async def generate_graph_from_materials(
        self,
        study_goal: dict,
        student_background: Optional[dict] = None,
        material_ids: Optional[List[int]] = None,
        progress_callback=None,
        study_depth: str = "intermediate"
    ) -> KnowledgeGraph:
        """
        根据用户上传的学习资料生成知识图谱
        
        Args:
            study_goal: 学习目标信息，包含 title, subject, description
            student_background: 学生背景信息
            material_ids: 学习资料ID列表（如果为空，则获取学习目标关联的所有用户上传资料）
            progress_callback: 进度回调函数，签名为 async def progress_callback(data: dict)
            study_depth: 学习深度 (basic/intermediate/advanced)
            
        Returns:
            KnowledgeGraph: 生成的知识图谱对象
        """
        # 获取学习资料
        materials = self._get_materials_for_graph(study_goal, material_ids)
        
        if not materials:
            # 如果没有学习资料，回退到普通模式
            print("未找到学习资料，回退到普通知识图谱生成模式")
            return await self.generate_graph_from_goal(study_goal, student_background, study_depth=study_depth)
        
        print(f"找到 {len(materials)} 个学习资料，开始处理...")
        
        # 重置取消状态（新生成开始）
        reset_cancel()
        
        # 1. 开始加载文档时 (5%)
        if progress_callback:
            await progress_callback({
                "status": "loading_documents",
                "progress": 5,
                "message": "正在加载文档...",
                "total": len(materials),
                "current": 0
            })
        
        # 构建上下文
        context = {
            "topic": study_goal.get("title", ""),
            "subject": study_goal.get("subject", ""),
            "description": study_goal.get("description", ""),
            "student_level": study_goal.get("student_level", "intermediate"),
            **(student_background or {})
        }
        
        # 初始化文档处理器（与main.py保持一致的路径）
        upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "app", "uploads", "materials"
        )
        doc_processor = DocumentProcessor(upload_dir)
        
        # 第一阶段：预计算所有文档的分块数
        total_chunks = 0
        material_chunks_info = []  # 存储每个资料的分块信息
        
        for i, material in enumerate(materials):
            print(f"分析资料: {material.title}")
            
            # 2. 每加载一个文档时 (5% -> 15%)
            if progress_callback:
                await progress_callback({
                    "status": "loading_documents",
                    "progress": int(5 + (i + 1) / len(materials) * 10),
                    "message": f"正在加载文档: {material.title}",
                    "total": len(materials),
                    "current": i + 1
                })
            
            try:
                # 检查是否已取消
                await wait_if_cancelled()
                
                file_path = material.content_url or material.content
                if not file_path:
                    print(f"[分块计算] 资料 '{material.title}' 没有文件路径")
                    material_chunks_info.append({"material": material, "chunks": 0, "type": "unknown"})
                    continue
                
                print(f"[分块计算] 处理资料: {material.title}, 路径: {file_path}")
                
                # 优先使用数据库中保存的文档类型（如果可用且最新）
                saved_doc_type = getattr(material, 'document_type', None)
                print(f"[分块计算] 数据库保存的文档类型: {saved_doc_type}")
                
                # 重新检测文档类型以确保准确性（使用优化后的检测逻辑）
                doc_result = doc_processor.process_file(file_path)
                doc_type = doc_result.get("type", "")
                print(f"[分块计算] 重新检测文档类型: {doc_type}")
                
                # 如果保存的类型与检测类型不一致，记录警告
                if saved_doc_type and saved_doc_type != doc_type:
                    print(f"[分块计算] ⚠️ 警告: 保存类型({saved_doc_type})与检测类型({doc_type})不一致，以检测结果为准")
                
                if doc_type == "scanned_pdf":
                    images = doc_result.get("images", [])
                    print(f"[分块计算] 扫描版PDF，图片数量: {len(images)}")
                    
                    if len(images) == 0:
                        # 图片数量为0，报告错误
                        print(f"[分块计算] 错误: 扫描版PDF没有生成任何图片！")
                        material_chunks_info.append({"material": material, "chunks": 0, "type": doc_type, "error": "未生成图片"})
                        continue
                    
                    chunks = (len(images) + settings.IMAGE_BATCH_SIZE - 1) // settings.IMAGE_BATCH_SIZE
                    total_chunks += chunks
                    print(f"[分块计算] 分块数: {chunks} (图片数:{len(images)}, 批次大小:{settings.IMAGE_BATCH_SIZE})")
                    material_chunks_info.append({"material": material, "chunks": chunks, "type": doc_type, "images": images})
                    
                elif doc_type in ["text_pdf", "word", "powerpoint", "text"]:
                    text = doc_result.get("text", "")
                    print(f"[分块计算] 文字内容长度: {len(text)}")
                    
                    if text:
                        text_chunks = doc_processor.split_text(
                            text,
                            chunk_size=settings.TEXT_CHUNK_SIZE,
                            overlap=settings.TEXT_CHUNK_OVERLAP
                        )
                        chunks = len(text_chunks)
                        total_chunks += chunks
                        print(f"[分块计算] 文字分块数: {chunks}")
                        material_chunks_info.append({"material": material, "chunks": chunks, "type": doc_type, "text_chunks": text_chunks})
                    else:
                        print(f"[分块计算] 警告: 文字内容为空")
                        material_chunks_info.append({"material": material, "chunks": 0, "type": doc_type})
                        
                elif doc_type == "image":
                    images = doc_result.get("images", [])
                    chunks = len(images) if images else 1
                    total_chunks += chunks
                    print(f"[分块计算] 图片分块数: {chunks}")
                    material_chunks_info.append({"material": material, "chunks": chunks, "type": doc_type, "images": images})
                    
                else:
                    print(f"[分块计算] 未知文档类型: {doc_type}")
                    material_chunks_info.append({"material": material, "chunks": 1, "type": doc_type})
                    
            except Exception as e:
                import traceback
                print(f"[分块计算] 分析资料 '{material.title}' 时出错: {e}")
                traceback.print_exc()
                material_chunks_info.append({"material": material, "chunks": 0, "type": "error", "error": str(e)})
                continue
        
        print(f"[分块计算] 总分块数: {total_chunks}")
        
        # 3. 文档全部加载完成时 (15%)
        if progress_callback:
            await progress_callback({
                "status": "loading_documents",
                "progress": 15,
                "message": f"已完成文档加载，共{len(materials)}个文件",
                "total": len(materials),
                "current": len(materials)
            })
        
        # 4. 文档处理（提取文字、分块）开始/完成时，计算总分块数后 (15% -> 25%)
        if progress_callback:
            await progress_callback({
                "status": "processing_documents",
                "progress": 25,
                "message": f"正在处理文档（被分为{total_chunks}个部分）",
                "total_chunks": total_chunks
                # 注意：初始化阶段不发送chunk字段，避免前端误判
            })
        
        # 第二阶段：处理所有资料并生成图谱
        all_nodes = []
        all_edges = []
        temp_images = []  # 临时图片文件，需要清理
        current_chunk_num = 0  # 当前处理的全局分块序号
        
        for mat_info in material_chunks_info:
            # 检查是否已取消
            await wait_if_cancelled()
            
            material = mat_info["material"]
            doc_type = mat_info.get("type", "unknown")
            
            if doc_type == "error" or mat_info.get("chunks", 0) == 0:
                continue
            
            print(f"处理资料: {material.title}")
            
            try:
                if doc_type == "scanned_pdf":
                    # 扫描版PDF：转换为图片，使用多模态模型提取
                    images = mat_info.get("images", [])
                    if images:
                        temp_images.extend(images)
                        graph_data = await self.ai_provider.extract_knowledge_from_images(
                            images=images,
                            context=context,
                            image_processor=doc_processor,
                            batch_size=settings.IMAGE_BATCH_SIZE,
                            progress_callback=progress_callback,
                            chunk_offset=current_chunk_num,
                            total_chunks=total_chunks
                        )
                        if "nodes" in graph_data:
                            all_nodes.extend(graph_data["nodes"])
                        if "edges" in graph_data:
                            all_edges.extend(graph_data["edges"])
                        # 更新当前分块序号
                        current_chunk_num += mat_info.get("chunks", 1)
                
                elif doc_type in ["text_pdf", "word", "powerpoint", "text"]:
                    # 文字版文档：提取文字，分批处理
                    text_chunks = mat_info.get("text_chunks", [])
                    if text_chunks:
                        graph_data = await self.ai_provider.extract_knowledge_from_text(
                            text_chunks=text_chunks,
                            context=context,
                            progress_callback=progress_callback,
                            chunk_offset=current_chunk_num,
                            total_chunks=total_chunks
                        )
                        if "nodes" in graph_data:
                            all_nodes.extend(graph_data["nodes"])
                        if "edges" in graph_data:
                            all_edges.extend(graph_data["edges"])
                        # 更新当前分块序号
                        current_chunk_num += len(text_chunks)
                
                elif doc_type == "image":
                    # 图片：直接使用多模态模型
                    images = mat_info.get("images", [])
                    if images:
                        graph_data = await self.ai_provider.extract_knowledge_from_images(
                            images=images,
                            context=context,
                            image_processor=doc_processor,
                            batch_size=settings.IMAGE_BATCH_SIZE,
                            progress_callback=progress_callback,
                            chunk_offset=current_chunk_num,
                            total_chunks=total_chunks
                        )
                        if "nodes" in graph_data:
                            all_nodes.extend(graph_data["nodes"])
                        if "edges" in graph_data:
                            all_edges.extend(graph_data["edges"])
                        # 更新当前分块序号
                        current_chunk_num += 1
                
            except GenerationCancelledError:
                # 生成被取消
                print(f"生成已取消，正在清理...")
                raise GenerationCancelledError("用户取消了生成")
            except Exception as e:
                print(f"处理资料 '{material.title}' 时出错: {e}")
                continue
        
        # 6. 所有分块处理完成时 (85%)
        if progress_callback:
            await progress_callback({
                "status": "generating_graph",
                "progress": 85,
                "message": "已完成所有文档图谱生成",
                "total_chunks": total_chunks,
                "chunk": total_chunks
            })
        
        # 清理临时图片
        if temp_images:
            doc_processor.cleanup_temp_images(temp_images)
        
        # 7. 开始融合图谱时 (85% -> 95%)
        if progress_callback:
            await progress_callback({
                "status": "merging_graph",
                "progress": 85,
                "message": "正在融合所有知识图谱"
            })
        
        # 合并去重
        merged_graph = self._merge_and_validate_graph(
            {"nodes": all_nodes, "edges": all_edges},
            study_goal
        )
        
        # 8. 使用 AI 智能整合所有批次的知识图谱（新增步骤）
        # 这个步骤会分析所有批次的结果，发现遗漏的知识点，删除重复的知识点，补充缺失的依赖关系
        if len(merged_graph.get("nodes", [])) >= 5:
            merged_graph = await self._integrate_graph_with_ai(
                merged_graph,
                study_goal,
                progress_callback
            )
        
        nodes = merged_graph.get("nodes", [])
        edges = merged_graph.get("edges", [])
        
        # 计算元数据
        estimated_hours = sum(node.get("estimated_hours", 1.0) for node in nodes)
        
        # 根据学生背景调整
        adjusted_nodes = self._adjust_for_student(nodes, context)
        
        # 创建知识图谱记录
        knowledge_graph = KnowledgeGraph(
            study_goal_id=study_goal.get("study_goal_id"),
            title=f"{study_goal.get('title', '学习目标')}知识图谱",
            description=study_goal.get("description", f"基于学习资料生成的{study_goal.get('title')}知识图谱"),
            nodes=json.dumps(adjusted_nodes, ensure_ascii=False),
            edges=json.dumps(edges, ensure_ascii=False),
            total_nodes=len(adjusted_nodes),
            total_edges=len(edges),
            estimated_hours=estimated_hours
        )
        
        self.db.add(knowledge_graph)
        self.db.commit()
        self.db.refresh(knowledge_graph)
        
        # 保存知识点详情
        self._save_knowledge_nodes(knowledge_graph.id, adjusted_nodes)
        
        return knowledge_graph
    
    def _get_materials_for_graph(
        self,
        study_goal: dict,
        material_ids: Optional[List[int]] = None
    ) -> List[StudyMaterial]:
        """
        获取用于生成知识图谱的学习资料
        
        Args:
            study_goal: 学习目标信息
            material_ids: 指定的学习资料ID列表
            
        Returns:
            学习资料列表
        """
        study_goal_id = study_goal.get("study_goal_id")
        
        if not study_goal_id:
            return []
        
        query = self.db.query(StudyMaterial).filter(
            StudyMaterial.study_goal_id == study_goal_id
        )
        
        if material_ids:
            # 只获取指定的资料
            query = query.filter(StudyMaterial.id.in_(material_ids))
        
        materials = query.all()
        
        return materials
    
    def _merge_and_validate_graph(
        self,
        graph_data: dict,
        study_goal: dict
    ) -> dict:
        """
        合并并验证知识图谱数据
        
        Args:
            graph_data: 原始图谱数据
            study_goal: 学习目标信息
            
        Returns:
            处理后的图谱数据
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if not nodes:
            return {"nodes": [], "edges": []}
        
        # 去重节点（基于ID）
        unique_nodes = {}
        for node in nodes:
            node_id = node.get("id", "")
            if node_id and node_id not in unique_nodes:
                unique_nodes[node_id] = node
        
        # 处理跨批次边：只保留两端节点都存在的边
        valid_node_ids = set(unique_nodes.keys())
        valid_edges = []
        seen_edges = set()
        
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            
            if source in valid_node_ids and target in valid_node_ids:
                edge_key = f"{source}->{target}"
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    valid_edges.append(edge)
        
        # 标准化节点数据
        for node in unique_nodes.values():
            if not node.get("name") and node.get("label"):
                node["name"] = node["label"]
                if "label" in node:
                    del node["label"]
        
        # 过滤不相关的节点
        study_topic = study_goal.get("title", "")
        filtered_nodes = self._filter_irrelevant_nodes(
            list(unique_nodes.values()),
            study_topic
        )
        
        # 再次过滤边，确保两端节点都存在
        final_node_ids = set(node.get("id", "") for node in filtered_nodes)
        final_edges = [
            edge for edge in valid_edges
            if edge.get("source") in final_node_ids and edge.get("target") in final_node_ids
        ]
        
        return {
            "nodes": filtered_nodes,
            "edges": final_edges
        }
    
    async def _integrate_graph_with_ai(
        self,
        graph_data: dict,
        study_goal: dict,
        progress_callback=None
    ) -> dict:
        """
        使用 AI 智能整合所有批次的知识图谱
        
        这个方法会：
        1. 让AI分析当前图谱的问题
        2. AI只输出修改指令（要删除哪些节点ID、要补充哪些边关系）
        3. 系统根据指令执行实际的增删操作
        
        Args:
            graph_data: 所有批次的合并图谱数据
            study_goal: 学习目标信息
            progress_callback: 进度回调函数
            
        Returns:
            整合后的高质量知识图谱
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if len(nodes) < 5:
            # 节点太少，不需要AI整合
            return graph_data
        
        # 发送进度：开始AI分析
        if progress_callback:
            await progress_callback({
                "status": "integrating_graph",
                "progress": 88,
                "message": "正在使用AI分析知识图谱..."
            })
        
        topic = study_goal.get("title", "")
        subject = study_goal.get("subject", "")
        description = study_goal.get("description", "")
        
        # 构建系统提示词 - 只输出修改指令，不输出完整图谱
        system_prompt = """你是一位资深的知识架构师，擅长分析知识图谱问题并给出优化建议。

## 你的任务
分析当前知识图谱的问题，给出具体的修改指令。**你只需要输出修改指令，系统会根据指令自动执行修改**。

## 重要限制
**节点数量上限：420个**
- 如果当前图谱节点数量超过420个，必须标记需要删除的节点
- 删除优先级：
  1. 没有关联关系的孤立节点优先删除
  2. 标记为"optional"的节点
  3. 重要性较低的节点
- 保留：核心知识点、前置依赖链上的知识点、与多个节点有关联的知识点

## 边（Edges）关系类型（共8种）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分
3. **进阶关系**：A是B的基础
4. **对立关系**：A与B是相反的概念
5. **对比关系**：A与B可类比学习
6. **应用关系**：A是B的应用
7. **等价关系**：A和B本质相同
8. **关联关系**：A与B存在某种联系

## 输出要求
**只输出以下JSON格式的修改指令，不要输出完整的节点和边列表**：

```json
{
  "nodes_to_remove": ["需要删除的节点ID列表"],
  "edges_to_add": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型"
    }
  ],
  "analysis_summary": "分析总结（50字以上），说明发现的问题和修改理由"
}
```

## 分析要点
1. **孤立节点**：找出没有任何边连接的节点
2. **重复节点**：找出语义相同或高度相似的节点
3. **缺失关系**：分析哪些重要知识点之间缺少关联
4. **关系多样性**：检查是否只有前置依赖，要补充其他类型关系
5. **节点数量**：如果超过420个，必须标记删除优先级最低的节点"""

        # 构建用户提示词 - 只传递统计信息和节点概要
        # 为了减少token消耗，只传递节点ID、名称、重要性等概要信息
        node_summaries = [
            {
                "id": n.get("id", ""),
                "name": n.get("name", ""),
                "importance": n.get("importance", "important"),
                "category": n.get("category", ""),
                "difficulty": n.get("difficulty", "")
            }
            for n in nodes
        ]
        
        # 构建边概要
        edge_summaries = [
            {
                "source": e.get("source", ""),
                "target": e.get("target", ""),
                "relation": e.get("relation", "")
            }
            for e in edges
        ]
        
        user_prompt = f"""## 学习主题
- 主题：{topic}
- 学科：{subject}
- 描述：{description}

## 当前图谱统计
- 总节点数：{len(nodes)}
- 总边数：{len(edges)}
- 节点上限：420

## 所有节点概要（共 {len(nodes)} 个）
```json
{node_summaries}
```

## 所有边概要（共 {len(edges)} 条）
```json
{edge_summaries}
```

## 你的任务
1. **分析孤立节点**：找出没有任何边连接的节点，这些应该优先删除
2. **分析重复节点**：找出名称相似或语义重复的节点，标记保留一个
3. **分析缺失关系**：分析知识点之间的逻辑关系，补充缺失的重要依赖
4. **控制节点数量**：如果超过420个，标记需要删除的节点
5. **输出修改指令**：只输出 nodes_to_remove 和 edges_to_add

**重要**：请确保 edges_to_add 中每条边的 source 和 target 都在节点列表中存在！"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.ai_provider.chat(messages, temperature=0.7)
            
            # 解析AI响应
            import json
            import re
            
            # 尝试从响应中提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # 尝试直接解析整个响应
                result = json.loads(response)
            
            # 提取修改指令
            nodes_to_remove = result.get("nodes_to_remove", [])
            edges_to_add = result.get("edges_to_add", [])
            analysis_summary = result.get("analysis_summary", "整合完成")
            
            print(f"[AI分析] {analysis_summary}")
            if nodes_to_remove:
                print(f"[AI分析] 建议删除 {len(nodes_to_remove)} 个节点: {nodes_to_remove[:10]}{'...' if len(nodes_to_remove) > 10 else ''}")
            if edges_to_add:
                print(f"[AI分析] 建议添加 {len(edges_to_add)} 条边")
            
            # 发送进度：执行系统修改
            if progress_callback:
                await progress_callback({
                    "status": "integrating_graph",
                    "progress": 90,
                    "message": "正在执行图谱修改..."
                })
            
            # 系统根据指令执行修改
            modified_graph = self._apply_modifications(
                nodes, edges, nodes_to_remove, edges_to_add, topic
            )
            
            # 发送进度：AI整合完成
            if progress_callback:
                await progress_callback({
                    "status": "integrating_graph",
                    "progress": 92,
                    "message": "AI整合完成，正在验证..."
                })
            
            # 后处理：处理孤立节点
            processed_result = self._handle_isolated_nodes(
                modified_graph["nodes"],
                modified_graph["edges"],
                topic
            )
            
            return {
                "nodes": processed_result["nodes"],
                "edges": processed_result["edges"]
            }
            
        except Exception as e:
            print(f"[AI分析] 分析失败: {e}，使用原始数据")
            import traceback
            traceback.print_exc()
            return graph_data
    
    def _apply_modifications(
        self,
        nodes: List[dict],
        edges: List[dict],
        nodes_to_remove: List[str],
        edges_to_add: List[dict],
        topic: str
    ) -> dict:
        """
        根据AI指令执行图谱修改
        
        Args:
            nodes: 原始节点列表
            edges: 原始边列表
            nodes_to_remove: 要删除的节点ID列表
            edges_to_add: 要添加的边列表
            
        Returns:
            修改后的图谱数据
        """
        # 1. 删除指定的节点
        nodes_to_remove_set = set(nodes_to_remove)
        remaining_nodes = [n for n in nodes if n.get("id") not in nodes_to_remove_set]
        
        print(f"[系统修改] 删除 {len(nodes_to_remove_set)} 个节点，剩余 {len(remaining_nodes)} 个节点")
        
        # 2. 添加新的边
        existing_edges = {(e.get("source"), e.get("target")) for e in edges}
        new_edges = list(edges)
        
        for edge in edges_to_add:
            source = edge.get("source")
            target = edge.get("target")
            
            # 确保两端节点都存在
            node_ids = {n.get("id") for n in remaining_nodes}
            if source in node_ids and target in node_ids:
                edge_key = (source, target)
                if edge_key not in existing_edges:
                    new_edges.append(edge)
                    existing_edges.add(edge_key)
        
        print(f"[系统修改] 添加 {len(new_edges) - len(edges)} 条边，现有 {len(new_edges)} 条边")
        
        # 3. 再次检查节点数量，如果仍超过420个，自动精简
        if len(remaining_nodes) > 420:
            print(f"[系统修改] 节点数量仍超过420个({len(remaining_nodes)})，自动精简...")
            remaining_nodes = self._auto_prune_nodes(remaining_nodes, new_edges, topic)
            print(f"[系统修改] 精简后剩余 {len(remaining_nodes)} 个节点")
        
        return {
            "nodes": remaining_nodes,
            "edges": new_edges
        }
    
    def _auto_prune_nodes(
        self,
        nodes: List[dict],
        edges: List[dict],
        topic: str
    ) -> List[dict]:
        """
        自动精简节点，确保数量不超过420个
        
        精简策略：
        1. 首先删除孤立节点（没有边连接的）
        2. 然后按优先级删除：optional -> importance低 -> degree低
        
        Args:
            nodes: 节点列表
            edges: 边列表
            topic: 学习主题
            
        Returns:
            精简后的节点列表
        """
        # 构建节点ID集合
        node_ids = {n.get("id") for n in nodes}
        
        # 计算每个节点的度数（连接数）
        node_degree = {nid: 0 for nid in node_ids}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in node_degree:
                node_degree[source] += 1
            if target in node_degree:
                node_degree[target] += 1
        
        # 按删除优先级分类节点
        isolated_nodes = []      # 孤立节点（度数为0）
        optional_nodes = []      # optional重要性的节点
        low_importance_nodes = []  # 非essential/important的节点
        
        for node in nodes:
            node_id = node.get("id", "")
            importance = node.get("importance", "important")
            degree = node_degree.get(node_id, 0)
            
            if degree == 0:
                isolated_nodes.append(node)
            elif importance == "optional":
                optional_nodes.append(node)
            else:
                low_importance_nodes.append(node)
        
        # 按度数从低到高排序（同优先级内）
        optional_nodes.sort(key=lambda n: node_degree.get(n.get("id", ""), 0))
        low_importance_nodes.sort(key=lambda n: node_degree.get(n.get("id", ""), 0))
        
        # 需要删除的节点数量
        target_count = 420
        current_count = len(nodes)
        to_remove_count = current_count - target_count
        
        if to_remove_count <= 0:
            return nodes
        
        # 开始删除
        nodes_to_remove = []
        
        # 1. 先删除孤立节点
        for node in isolated_nodes:
            if len(nodes_to_remove) >= to_remove_count:
                break
            nodes_to_remove.append(node.get("id"))
        
        # 2. 再删除optional节点
        for node in optional_nodes:
            if len(nodes_to_remove) >= to_remove_count:
                break
            nodes_to_remove.append(node.get("id"))
        
        # 3. 最后删除低重要性节点（按度数从低到高）
        for node in low_importance_nodes:
            if len(nodes_to_remove) >= to_remove_count:
                break
            nodes_to_remove.append(node.get("id"))
        
        # 返回保留的节点
        nodes_to_remove_set = set(nodes_to_remove)
        remaining_nodes = [n for n in nodes if n.get("id") not in nodes_to_remove_set]
        
        print(f"[自动精简] 删除 {len(nodes_to_remove)} 个节点：孤立节点{len([n for n in isolated_nodes if n.get('id') in nodes_to_remove_set])}个，optional{len([n for n in optional_nodes if n.get('id') in nodes_to_remove_set])}个，其他{len([n for n in low_importance_nodes if n.get('id') in nodes_to_remove_set])}个")
        
        return remaining_nodes
    
    def _filter_irrelevant_nodes(
        self,
        nodes: List[dict],
        study_topic: str
    ) -> List[dict]:
        """
        过滤与学习主题不相关的节点
        
        Args:
            nodes: 节点列表
            study_topic: 学习主题
            
        Returns:
            过滤后的节点列表
        """
        filtered = []
        excluded_keywords = [
            "python", "java", "javascript", "c++", "c语言", "编程语言",
            "html", "css", "前端", "后端", "web开发", "http", "api",
            "pytorch", "tensorflow", "keras", "框架应用",
            "区块链", "游戏开发", "移动开发", "ios", "android",
        ]
        
        for node in nodes:
            node_name = node.get("name", "").lower()
            node_id = node.get("id", "").lower()
            node_desc = node.get("description", "").lower()
            
            is_irrelevant = False
            for keyword in excluded_keywords:
                if keyword in node_name or keyword in node_id or keyword in node_desc:
                    if keyword.lower() not in study_topic.lower():
                        is_irrelevant = True
                        print(f"过滤不相关节点 [{keyword}]: {node.get('name')}")
                        break
            
            if not is_irrelevant:
                filtered.append(node)
        
        return filtered
    
    def _handle_isolated_nodes(
        self,
        nodes: List[dict],
        edges: List[dict],
        topic: str
    ) -> dict:
        """
        处理孤立节点（没有任何连接的知识点）- 确保所有节点都至少有一条边
        
        策略：
        1. 找出所有孤立节点
        2. 按难度和类别分组
        3. 循环处理，直到所有节点都有边
        4. 优先使用前置依赖关系，其次使用关联关系
        
        Args:
            nodes: 节点列表
            edges: 边列表
            topic: 学习主题
            
        Returns:
            处理后的节点和边
        """
        if not nodes:
            return {"nodes": nodes, "edges": edges}
        
        # 构建节点ID集合
        node_ids = {node.get("id") for node in nodes if node.get("id")}
        
        # 构建边的连接信息
        connected_nodes = set()
        existing_edges = set()  # 用于快速查找已有边
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                connected_nodes.add(source)
                connected_nodes.add(target)
                existing_edges.add((source, target))
        
        # 找出孤立节点
        isolated_nodes = [node for node in nodes if node.get("id") not in connected_nodes]
        
        if not isolated_nodes:
            print(f"[孤立节点处理] 无孤立节点，图谱完整")
            return {"nodes": nodes, "edges": edges}
        
        print(f"[孤立节点处理] 发现 {len(isolated_nodes)} 个孤立节点，正在建立关联...")
        
        # 新的边列表
        new_edges = list(edges)
        added_count = 0
        
        # 构建节点映射，方便查找
        node_map = {node.get("id"): node for node in nodes}
        
        # 按难度排序（基础优先连接）
        difficulty_order = {"foundation": 0, "intermediate": 1, "advanced": 2, "expert": 3}
        
        def get_difficulty_order(node):
            return difficulty_order.get(node.get("difficulty", "intermediate"), 1)
        
        # 对孤立节点按难度排序
        isolated_nodes.sort(key=get_difficulty_order)
        
        # 已处理的孤立节点
        processed_isolated_ids = set()
        
        # 策略1：处理有前置依赖的孤立节点
        for node in isolated_nodes:
            if node.get("id") in processed_isolated_ids:
                continue
            
            prerequisites = node.get("prerequisites", [])
            if prerequisites:
                # 找到第一个存在于图谱中的前置节点
                for prereq_id in prerequisites:
                    if prereq_id in node_ids and prereq_id not in connected_nodes:
                        # 前置节点也是孤立节点，先处理前置节点
                        pass
                    elif prereq_id in node_ids:
                        # 前置节点已连接，建立反向关系
                        edge_key = (node.get("id"), prereq_id)
                        if edge_key not in existing_edges:
                            new_edges.append({
                                "source": node.get("id"),
                                "target": prereq_id,
                                "relation": "前置依赖"
                            })
                            existing_edges.add(edge_key)
                            processed_isolated_ids.add(node.get("id"))
                            connected_nodes.add(node.get("id"))
                            added_count += 1
                            print(f"[孤立节点处理] '{node.get('name')}' -> '{prereq_id}' (前置依赖)")
                            break
        
        # 策略2：基础节点连接到中间节点
        foundation_isolated = [n for n in isolated_nodes if n.get("id") not in processed_isolated_ids and n.get("difficulty") == "foundation"]
        intermediate_nodes = [n for n in nodes if n.get("id") in connected_nodes and n.get("difficulty") in ["intermediate", "advanced"]]
        
        for fn in foundation_isolated:
            if fn.get("id") in processed_isolated_ids:
                continue
            if intermediate_nodes:
                target = intermediate_nodes[0]
                edge_key = (fn.get("id"), target.get("id"))
                if edge_key not in existing_edges:
                    new_edges.append({
                        "source": fn.get("id"),
                        "target": target.get("id"),
                        "relation": "进阶关系"
                    })
                    existing_edges.add(edge_key)
                    processed_isolated_ids.add(fn.get("id"))
                    connected_nodes.add(fn.get("id"))
                    added_count += 1
                    print(f"[孤立节点处理] '{fn.get('name')}' -> '{target.get('name')}' (进阶关系)")
        
        # 策略3：同类别节点之间建立关联
        categories = {}
        for node in isolated_nodes:
            if node.get("id") in processed_isolated_ids:
                continue
            cat = node.get("category", "核心理论")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(node)
        
        for cat, cat_nodes in categories.items():
            if len(cat_nodes) > 1:
                # 连接同类别的孤立节点
                for i in range(len(cat_nodes) - 1):
                    if cat_nodes[i].get("id") in processed_isolated_ids:
                        continue
                    target = cat_nodes[i + 1]
                    edge_key = (cat_nodes[i].get("id"), target.get("id"))
                    if edge_key not in existing_edges:
                        new_edges.append({
                            "source": cat_nodes[i].get("id"),
                            "target": target.get("id"),
                            "relation": "关联关系"
                        })
                        existing_edges.add(edge_key)
                        processed_isolated_ids.add(cat_nodes[i].get("id"))
                        connected_nodes.add(cat_nodes[i].get("id"))
                        added_count += 1
                        print(f"[孤立节点处理] '{cat_nodes[i].get('name')}' -> '{target.get('name')}' ({cat}类关联)")
        
        # 策略4：剩余孤立节点连接到任意已连接节点
        remaining_isolated = [n for n in isolated_nodes if n.get("id") not in processed_isolated_ids]
        connected_list = [n for n in nodes if n.get("id") in connected_nodes]
        
        for isolated in remaining_isolated:
            if connected_list:
                # 优先找同难度的已连接节点
                target = None
                for cn in connected_list:
                    if cn.get("difficulty") == isolated.get("difficulty"):
                        target = cn
                        break
                if not target:
                    target = connected_list[0]
                
                edge_key = (isolated.get("id"), target.get("id"))
                if edge_key not in existing_edges:
                    new_edges.append({
                        "source": isolated.get("id"),
                        "target": target.get("id"),
                        "relation": "关联关系"
                    })
                    existing_edges.add(edge_key)
                    processed_isolated_ids.add(isolated.get("id"))
                    connected_nodes.add(isolated.get("id"))
                    added_count += 1
                    print(f"[孤立节点处理] '{isolated.get('name')}' -> '{target.get('name')}' (强制关联)")
        
        # 最终检查：验证所有节点都已连接
        final_connected = set()
        for edge in new_edges:
            final_connected.add(edge.get("source"))
            final_connected.add(edge.get("target"))
        
        still_isolated = [n for n in nodes if n.get("id") not in final_connected]
        
        if still_isolated:
            print(f"[孤立节点处理] 警告：仍有 {len(still_isolated)} 个节点无法连接，将删除")
            # 删除仍然孤立的节点
            still_isolated_ids = {n.get("id") for n in still_isolated}
            nodes = [n for n in nodes if n.get("id") not in still_isolated_ids]
            print(f"[孤立节点处理] 已删除孤立节点: {[n.get('name') for n in still_isolated]}")
        
        print(f"[孤立节点处理] 完成，共添加 {added_count} 条边，{len(nodes)} 个节点保留")
        
        return {
            "nodes": nodes,
            "edges": new_edges
    }
    
    def _adjust_for_student(
        self, 
        nodes: List[dict], 
        student_background: dict
    ) -> List[dict]:
        """
        根据学生背景调整知识图谱
        
        Args:
            nodes: 原始节点列表
            student_background: 学生背景信息
            
        Returns:
            调整后的节点列表
        """
        adjusted = []
        
        student_level = student_background.get("student_level", "intermediate")
        
        # 难度映射：foundation -> easy, intermediate -> medium, advanced/expert -> hard
        difficulty_map = {
            "foundation": "easy",
            "intermediate": "medium", 
            "advanced": "hard",
            "expert": "hard"
        }
        
        for node in nodes:
            node_id = node.get("id", "")
            difficulty = node.get("difficulty", "intermediate")
            
            # 根据学生水平调整难度
            if student_level == "beginner":
                # 初学者：降低难度标记
                if difficulty == "expert":
                    node["adjusted_difficulty"] = "advanced"
                elif difficulty == "advanced":
                    node["adjusted_difficulty"] = "intermediate"
                elif difficulty == "intermediate":
                    node["adjusted_difficulty"] = "foundation"
                else:
                    node["adjusted_difficulty"] = difficulty
            elif student_level == "advanced":
                # 高级用户：提高基础内容的优先级
                if difficulty == "foundation":
                    node["adjusted_difficulty"] = "foundation"
                    node["importance"] = "optional"
                else:
                    node["adjusted_difficulty"] = difficulty
            else:
                # 中级用户：保持原样
                node["adjusted_difficulty"] = difficulty_map.get(difficulty, "medium")
            
            adjusted.append(node)
        
        return adjusted
    
    def _save_knowledge_nodes(self, graph_id: int, nodes: List[dict]):
        """保存知识点详情到数据库"""
        for node in nodes:
            knowledge_node = KnowledgeNode(
                graph_id=graph_id,
                node_id=node.get("id"),
                name=node.get("name"),
                description=node.get("description", ""),
                difficulty=node.get("adjusted_difficulty", node.get("difficulty", "medium")),
                estimated_hours=node.get("estimated_hours", 1.0),
                prerequisites=node.get("prerequisites", []),
                resources=node.get("resources")
            )
            self.db.add(knowledge_node)
        
        self.db.commit()
    
    def get_graph(self, graph_id: int) -> Optional[KnowledgeGraph]:
        """获取知识图谱"""
        return self.db.query(KnowledgeGraph).filter(KnowledgeGraph.id == graph_id).first()
    
    def get_graph_for_visualization(self, graph_id: int) -> dict:
        """
        获取用于 ECharts 可视化的数据格式
        
        Returns:
            {
                "nodes": [{"id": "", "name": "", "value": 0, "symbolSize": 0, ...}],
                "edges": [{"source": "", "target": "", "lineStyle": {...}}],
                "categories": [...],
                "metadata": {...}
            }
        """
        graph = self.get_graph(graph_id)
        if not graph:
            return {}
        
        # 解析 JSON 数据
        nodes = json.loads(graph.nodes) if isinstance(graph.nodes, str) else graph.nodes
        edges = json.loads(graph.edges) if isinstance(graph.edges, str) else graph.edges
        
        # 转换为 ECharts 格式
        echarts_nodes = []
        for node in nodes:
            difficulty = node.get("adjusted_difficulty", node.get("difficulty", "medium"))
            category = node.get("category", "核心概念")
            importance = node.get("importance", "important")
            
            # 根据难度和重要性设置节点大小
            base_size = {"foundation": 25, "intermediate": 35, "advanced": 45, "expert": 55}.get(difficulty, 35)
            if importance == "essential":
                base_size += 10
            elif importance == "optional":
                base_size -= 5
            
            echarts_nodes.append({
                "id": node.get("id"),
                "name": node.get("name"),
                "value": node.get("estimated_hours", 1.0),
                "symbolSize": base_size,
                "category": category,
                "difficulty": difficulty,
                "description": node.get("description", ""),
                "importance": importance,
                "prerequisites": node.get("prerequisites", []),
                "draggable": True
            })
        
        echarts_edges = []
        for edge in edges:
            echarts_edges.append({
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation": edge.get("relation", ""),
                "lineStyle": {
                    "curveness": 0.2,
                    "opacity": 0.6
                }
            })
        
        # 按类别分组
        categories = list(set([node.get("category", "核心概念") for node in nodes]))
        
        return {
            "nodes": echarts_nodes,
            "edges": echarts_edges,
            "categories": [{"name": cat} for cat in categories],
            "metadata": {
                "title": graph.title,
                "total_nodes": graph.total_nodes,
                "total_edges": graph.total_edges,
                "estimated_hours": graph.estimated_hours
            }
        }
    
    def update_graph_mastery(
        self, 
        graph_id: int, 
        node_mastery: Dict[str, float]
    ) -> dict:
        """
        更新知识图谱上各节点的掌握度（用于热力图）
        
        Args:
            graph_id: 图谱 ID
            node_mastery: {node_id: mastery_level} 掌握度字典 (0-100)
            
        Returns:
            更新后的可视化数据
        """
        graph = self.get_graph(graph_id)
        if not graph:
            return {}
        
        nodes = json.loads(graph.nodes) if isinstance(graph.nodes, str) else graph.nodes
        
        # 为每个节点添加掌握度信息
        for node in nodes:
            node_id = node.get("id")
            mastery = node_mastery.get(node_id, 0.0)
            
            # 掌握度映射到5个等级和颜色
            # 0-20: 萌芽期 (gray)
            # 21-40: 成长期 (blue)
            # 41-60: 发展期 (yellow)
            # 61-80: 成熟期 (orange)
            # 81-100: 精通期 (green)
            if mastery >= 81:
                node["mastery_level"] = mastery
                node["mastery_name"] = "精通"
                node["mastery_color"] = "#52c41a"  # 绿色
                node["mastery_index"] = 5
            elif mastery >= 61:
                node["mastery_level"] = mastery
                node["mastery_name"] = "熟练"
                node["mastery_color"] = "#faad14"  # 橙色
                node["mastery_index"] = 4
            elif mastery >= 41:
                node["mastery_level"] = mastery
                node["mastery_name"] = "理解"
                node["mastery_color"] = "#fadb14"  # 黄色
                node["mastery_index"] = 3
            elif mastery >= 21:
                node["mastery_level"] = mastery
                node["mastery_name"] = "入门"
                node["mastery_color"] = "#1890ff"  # 蓝色
                node["mastery_index"] = 2
            else:
                node["mastery_level"] = mastery
                node["mastery_name"] = "萌芽"
                node["mastery_color"] = "#8c8c8c"  # 灰色
                node["mastery_index"] = 1 if mastery > 0 else 0
        
        # 返回更新后的可视化数据
        return self.get_graph_for_visualization(graph_id)
    
    def get_mastery_stats(self, graph_id: int, student_id: int = 1) -> dict:
        """
        获取图谱的掌握度统计
        
        Args:
            graph_id: 图谱 ID
            student_id: 学生 ID
            
        Returns:
            掌握度统计信息
        """
        from app.models.node_mastery import NodeMastery
        
        graph = self.get_graph(graph_id)
        if not graph:
            return {}
        
        nodes = json.loads(graph.nodes) if isinstance(graph.nodes, str) else graph.nodes
        
        # 获取所有节点的掌握度
        masteries = self.db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == graph.study_goal_id,
            NodeMastery.student_id == student_id
        ).all()
        
        mastery_map = {m.node_id: m.mastery_level for m in masteries}
        
        # 统计各等级数量
        stats = {
            "total": len(nodes),
            "sprouting": 0,      # 萌芽 0%
            "learning": 0,        # 入门 1-20%
            "developing": 0,     # 发展 21-40%
            "understanding": 0,  # 理解 41-60%
            "proficient": 0,    # 熟练 61-80%
            "mastered": 0        # 精通 81-100%
        }
        
        for node in nodes:
            node_id = node.get("id")
            mastery = mastery_map.get(node_id, 0.0)
            
            if mastery >= 81:
                stats["mastered"] += 1
            elif mastery >= 61:
                stats["proficient"] += 1
            elif mastery >= 41:
                stats["understanding"] += 1
            elif mastery >= 21:
                stats["developing"] += 1
            elif mastery >= 1:
                stats["learning"] += 1
            else:
                stats["sprouting"] += 1
        
        return stats
