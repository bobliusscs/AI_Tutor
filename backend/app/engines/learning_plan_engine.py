"""
学习规划引擎 - 根据知识依赖关系生成个性化学习路径
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.models.learning_plan import LearningPlan, Lesson, Chapter, Section, PlanStatus
from app.models.knowledge_graph import KnowledgeGraph
from app.services.ai_model_provider import AIModelProvider
from app.engines.prompts.learning_plan_prompts import (
    PLAN_CHAPTERS_PROMPT,
    PLAN_SECTIONS_FOR_CHAPTER_PROMPT,
    PLAN_STRUCTURE_PROMPT,
    CHAPTER_PPT_PROMPT,
    SECTION_PPT_PROMPT
)
from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError


class LearningPlanEngine:
    """学习规划引擎"""
    
    def __init__(self, db: Session, ai_provider: AIModelProvider):
        self.db = db
        self.ai_provider = ai_provider
    
    async def generate_plan(
        self,
        student_id: int,
        graph_id: int,
        study_goal_id: int = None,
        weekly_hours: float = 5.0,
        title: Optional[str] = None,
        description: Optional[str] = None,
        generate_lesson_content: bool = True  # 是否立即生成课时内容，默认为 True 确保内容质量
    ) -> LearningPlan:
        """
        生成学习计划
        
        Args:
            student_id: 学生 ID
            graph_id: 知识图谱 ID
            weekly_hours: 每周可用小时数
            title: 计划标题
            description: 计划描述
            generate_lesson_content: 是否立即调用 AI 生成课时详细内容，默认 True
            
        Returns:
            LearningPlan: 生成的学习计划对象
        """
        # 0. 获取学生信息（用于个性化内容生成）
        from app.models.student import Student
        student = self.db.query(Student).filter(Student.id == student_id).first()
        student_preferences = None
        if student:
            student_preferences = {
                "username": student.username,
                "nickname": student.nickname,
                "grade": student.grade,
                "background": student.background or {},
                "learning_style": student.learning_style or {}
            }
        
        # 1. 获取学习目标信息（用于课时内容生成）
        study_goal_title = None
        study_goal_description = None
        if study_goal_id:
            from app.models.study_goal import StudyGoal
            study_goal = self.db.query(StudyGoal).filter(StudyGoal.id == study_goal_id).first()
            if study_goal:
                study_goal_title = study_goal.title
                study_goal_description = study_goal.description
        
        # 1. 获取知识图谱
        knowledge_graph = self.db.query(KnowledgeGraph).filter(KnowledgeGraph.id == graph_id).first()
        if not knowledge_graph:
            raise ValueError(f"知识图谱不存在：{graph_id}")
        
        nodes = json.loads(knowledge_graph.nodes) if isinstance(knowledge_graph.nodes, str) else knowledge_graph.nodes
        edges = json.loads(knowledge_graph.edges) if isinstance(knowledge_graph.edges, str) else knowledge_graph.edges
        
        # 校验：确保所有节点都有有效ID和名称
        valid_nodes = []
        for node in nodes:
            node_id = node.get("id")
            # 如果节点没有name但有label，使用label作为name
            node_name = node.get("name")
            if not node_name and node.get("label"):
                node_name = node.get("label")
                node["name"] = node_name  # 同步更新，保持一致性
            
            if not node_id or not node_name:
                print(f"警告：跳过无效节点（缺少id或name）: {node}")
                continue
            valid_nodes.append(node)
        
        if len(valid_nodes) < len(nodes):
            print(f"警告：过滤了 {len(nodes) - len(valid_nodes)} 个无效节点")
        
        nodes = valid_nodes
        
        # 校验：检查节点ID是否唯一
        node_ids = [n.get("id") for n in nodes]
        if len(node_ids) != len(set(node_ids)):
            print("警告：发现重复的节点ID，将使用第一个出现的节点")
            seen = set()
            nodes = [n for n in nodes if n.get("id") not in seen and not seen.add(n.get("id"))]
        
        # 2. 拓扑排序 - 确定学习顺序
        sorted_nodes = self._topological_sort(nodes, edges)
        
        # 3. 计算总学时和预计完成时间
        total_hours = sum(node.get("estimated_hours", 1.0) for node in sorted_nodes)
        weeks_needed = total_hours / weekly_hours
        end_date = datetime.utcnow() + timedelta(weeks=weeks_needed)
        
        # 4. 创建学习计划
        learning_plan = LearningPlan(
            student_id=student_id,
            study_goal_id=study_goal_id,
            graph_id=graph_id,
            title=title or f"{knowledge_graph.title}学习计划",
            description=description or f"预计{weeks_needed:.1f}周完成，每周{weekly_hours}小时",
            status=PlanStatus.ACTIVE.value,
            start_date=datetime.utcnow(),
            end_date=end_date,
            weekly_hours=weekly_hours,
            total_lessons=len(sorted_nodes),
            completed_lessons=0
        )
        
        self.db.add(learning_plan)
        self.db.commit()
        self.db.refresh(learning_plan)
        
        # 5. 生成课时记录（不再调用 AI 生成详细内容，提升创建速度）
        lesson_sequence = []
        valid_node_ids = {node.get("id") for node in nodes}  # 使用验证后的节点ID集合
        
        for idx, node in enumerate(sorted_nodes):
            # 双重校验：确保节点ID在知识图谱中
            if node.get("id") not in valid_node_ids:
                print(f"警告：跳过不在知识图谱中的节点: {node.get('id')}")
                continue
            
            # 只有明确要求时才会调用 AI 生成课时内容
            if generate_lesson_content:
                lesson = await self._generate_lesson(
                    plan_id=learning_plan.id,
                    node=node,
                    order=idx + 1,
                    study_goal_title=study_goal_title,
                    study_goal_description=study_goal_description,
                    student_preferences=student_preferences
                )
            else:
                # 快速创建课时记录，不调用 AI
                lesson = self._create_lesson_quick(
                    plan_id=learning_plan.id,
                    node=node,
                    order=idx + 1
                )
            
            lesson_sequence.append({
                "lesson_id": lesson.id,
                "order": idx + 1,
                "node_id": node.get("id")
            })
        
        # 6. 更新课程序列
        learning_plan.lesson_sequence = json.dumps(lesson_sequence, ensure_ascii=False)
        self.db.commit()
        
        return learning_plan
    
    def _topological_sort(self, nodes: List[dict], edges: List[dict]) -> List[dict]:
        """
        基于知识依赖的拓扑排序
        
        Args:
            nodes: 节点列表
            edges: 边列表（source -> target 表示 source 是 target 的前置）
            
        Returns:
            排序后的节点列表
        """
        # 构建邻接表和入度表
        node_map = {node["id"]: node for node in nodes}
        in_degree = {node["id"]: 0 for node in nodes}
        adj_list = {node["id"]: [] for node in nodes}
        
        # 建立依赖关系
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in adj_list and target in in_degree:
                adj_list[source].append(target)
                in_degree[target] += 1
        
        # Kahn 算法进行拓扑排序
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        sorted_result = []
        
        while queue:
            # 选择当前可学习的节点（可以优化为优先选择简单的）
            current = queue.pop(0)
            sorted_result.append(node_map[current])
            
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 如果有环，返回所有节点（不保证顺序）
        if len(sorted_result) != len(nodes):
            return nodes
        
        return sorted_result
    
    async def _generate_lesson(
        self, 
        plan_id: int, 
        node: dict, 
        order: int,
        study_goal_title: str = None,
        study_goal_description: str = None,
        student_preferences: dict = None
    ) -> Lesson:
        """
        生成单个课时内容（PPT幻灯片格式）
        
        Args:
            plan_id: 学习计划 ID
            node: 知识点节点
            order: 课时序号
            study_goal_title: 学习目标标题（用于上下文关联）
            study_goal_description: 学习目标描述（用于上下文关联）
            student_preferences: 学生偏好信息（包含学习风格、背景等）
            
        Returns:
            Lesson: 课时对象
        """
        # 从学生偏好中推断学习水平
        student_level = "intermediate"
        if student_preferences:
            # 根据学习背景推断水平
            background = student_preferences.get("background", {})
            grade = background.get("grade", "")
            if grade:
                if any(keyword in grade for keyword in ["大一", "大一", "高中", "零基础", "初学"]):
                    student_level = "beginner"
                elif any(keyword in grade for keyword in ["大二", "大三", "考研", "进阶"]):
                    student_level = "intermediate"
                elif any(keyword in grade for keyword in ["大四", "研究生", "深入"]):
                    student_level = "advanced"
        
        # 使用 AI 生成课时内容（PPT幻灯片格式），注入学习目标和学生偏好上下文
        lesson_data = await self.ai_provider.generate_lesson_content(
            knowledge_point=node,
            student_level=student_level,
            student_preferences=student_preferences,
            study_goal_title=study_goal_title,
            study_goal_description=study_goal_description
        )
        
        # 提取幻灯片数据
        slides = lesson_data.get("slides", [])
        
        # 从幻灯片中提取各部分内容（兼容旧字段）
        introduction = ""
        explanation = ""
        example = ""
        summary = ""
        exercises = []
        
        for slide in slides:
            slide_type = slide.get("type", "")
            if slide_type == "cover":
                introduction = slide.get("content", "")
            elif slide_type == "content" and slide.get("title") == "课程引入":
                introduction = slide.get("content", "")
            elif slide_type == "content" and slide.get("title") == "核心讲解":
                explanation = slide.get("content", "")
            elif slide_type == "example":
                example = slide.get("content", "")
            elif slide_type == "exercise":
                exercises = slide.get("questions", [])
            elif slide_type == "summary":
                summary = slide.get("content", "")
        
        # 如果没有提取到内容，使用第一个内容幻灯片作为讲解
        if not explanation:
            for slide in slides:
                if slide.get("type") == "content":
                    explanation = slide.get("content", "")
                    break
        
        # 创建课时记录
        lesson = Lesson(
            plan_id=plan_id,
            lesson_number=order,
            title=node.get("name"),
            knowledge_point_id=node.get("id"),
            introduction=introduction,
            explanation=explanation,
            example=example,
            exercises=json.dumps(exercises, ensure_ascii=False),
            summary=summary,
            estimated_minutes=int(node.get("estimated_hours", 1.0) * 60)
        )
        
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        
        return lesson
    
    def _create_lesson_quick(
        self, 
        plan_id: int, 
        node: dict, 
        order: int
    ) -> Lesson:
        """
        快速创建课时记录（不调用 AI）
        
        Args:
            plan_id: 学习计划 ID
            node: 知识点节点
            order: 课时序号
            
        Returns:
            Lesson: 课时对象
        """
        # 创建课时记录，使用知识点基本信息作为内容
        lesson = Lesson(
            plan_id=plan_id,
            lesson_number=order,
            title=node.get("name"),
            knowledge_point_id=node.get("id"),
            introduction=f"本课时将学习：{node.get('name')}",
            explanation=node.get("description", ""),
            example="",
            exercises="[]",
            summary=f"完成{node.get('name')}的学习",
            estimated_minutes=int(node.get("estimated_hours", 1.0) * 60)
        )
        
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        
        return lesson
    
    def get_plan(self, plan_id: int) -> Optional[LearningPlan]:
        """获取学习计划"""
        return self.db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
    
    def get_lessons(self, plan_id: int) -> List[Lesson]:
        """获取计划的所有课时"""
        return self.db.query(Lesson).filter(
            Lesson.plan_id == plan_id
        ).order_by(Lesson.lesson_number).all()
    
    def get_next_lesson(self, plan_id: int) -> Optional[Lesson]:
        """获取下一个未完成的课时"""
        return self.db.query(Lesson).filter(
            Lesson.plan_id == plan_id,
            Lesson.is_completed == False
        ).order_by(Lesson.lesson_number).first()
    
    def complete_lesson(self, lesson_id: int) -> Optional[dict]:
        """
        标记课时完成

        Args:
            lesson_id: 课时ID

        Returns:
            None: 课时不存在
            dict: 包含 {"already_completed": bool, "all_completed": bool} 的结果字典
        """
        lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()

        if not lesson:
            print(f"[complete_lesson] 课时不存在: lesson_id={lesson_id}")
            return None

        # 幂等处理：如果课时已完成，直接返回不重复计数
        if lesson.is_completed:
            print(f"[complete_lesson] 课时已完成（幂等）: lesson_id={lesson_id}")
            # 检查该小节是否全部完成（幂等情况下也需要返回）
            all_section_completed = False
            if hasattr(lesson, 'section_id') and lesson.section_id:
                remaining = self.db.query(Lesson).filter(
                    Lesson.section_id == lesson.section_id,
                    Lesson.is_completed == False
                ).count()
                all_section_completed = (remaining == 0)
            return {"already_completed": True, "all_completed": all_section_completed}

        # 标记课时完成
        lesson.is_completed = True
        lesson.completed_at = datetime.utcnow()
        print(f"[complete_lesson] 标记课时完成: lesson_id={lesson_id}")

        # 更新计划的进度
        plan = self.db.query(LearningPlan).filter(LearningPlan.id == lesson.plan_id).first()
        if plan:
            plan.completed_lessons += 1
            print(f"[complete_lesson] 更新计划进度: plan_id={plan.id}, completed_lessons={plan.completed_lessons}/{plan.total_lessons}")

            # 检查是否全部完成
            if plan.completed_lessons >= plan.total_lessons:
                plan.status = PlanStatus.COMPLETED.value
                print(f"[complete_lesson] 学习计划已完成: plan_id={plan.id}")

        # 在 self.db.commit() 之前，查询该 lesson 所属 section 是否全部课时已完成
        all_section_completed = False
        if hasattr(lesson, 'section_id') and lesson.section_id:
            remaining = self.db.query(Lesson).filter(
                Lesson.section_id == lesson.section_id,
                Lesson.is_completed == False
            ).count()
            all_section_completed = (remaining == 0)

        self.db.commit()
        return {"already_completed": False, "all_completed": all_section_completed}
    
    def adjust_difficulty(
        self, 
        plan_id: int, 
        new_difficulty: str
    ) -> bool:
        """
        动态调整学习计划难度
        
        Args:
            plan_id: 计划 ID
            new_difficulty: 新难度（easy/medium/hard）
            
        Returns:
            bool: 是否调整成功
        """
        # TODO: 实现难度调整逻辑
        # 可以根据难度重新生成课时内容或调整课顺序
        return True

    # ==================== 章-节结构学习计划方法 ====================

    async def generate_chaptered_plan(
        self,
        student_id: int,
        graph_id: int,
        study_goal_id: int = None,
        weekly_hours: float = 5.0,
        max_chapters: int = 12,
        max_sections_per_chapter: int = 6,
        title: Optional[str] = None,
        description: Optional[str] = None,
        progress_callback=None
    ) -> LearningPlan:
        """
        生成带章节结构的学习计划（AI驱动）

        Args:
            student_id: 学生 ID
            graph_id: 知识图谱 ID
            study_goal_id: 学习目标 ID
            weekly_hours: 每周可用小时数
            max_chapters: 最大章节数（默认12）
            max_sections_per_chapter: 每章最大节数（默认6）
            title: 计划标题
            description: 计划描述
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            LearningPlan: 生成的学习计划对象（包含章节结构）
        """
        # 重置取消状态（新生成开始）
        from app.services.cancel_manager import reset_cancel
        reset_cancel()
        
        # 0. 获取学生信息（用于个性化内容生成）
        from app.models.student import Student
        student = self.db.query(Student).filter(Student.id == student_id).first()
        student_preferences = None
        if student:
            student_preferences = {
                "username": student.username,
                "nickname": student.nickname,
                "grade": student.grade,
                "background": student.background or {},
                "learning_style": student.learning_style or {}
            }
        
        # 1. 获取知识图谱
        knowledge_graph = self.db.query(KnowledgeGraph).filter(KnowledgeGraph.id == graph_id).first()
        if not knowledge_graph:
            raise ValueError(f"知识图谱不存在：{graph_id}")

        nodes = json.loads(knowledge_graph.nodes) if isinstance(knowledge_graph.nodes, str) else knowledge_graph.nodes
        edges = json.loads(knowledge_graph.edges) if isinstance(knowledge_graph.edges, str) else knowledge_graph.edges

        # 2. 校验和清理节点
        valid_nodes = []
        for node in nodes:
            node_id = node.get("id")
            node_name = node.get("name")
            if not node_name and node.get("label"):
                node_name = node.get("label")
                node["name"] = node_name

            if not node_id or not node_name:
                print(f"警告：跳过无效节点：{node}")
                continue
            valid_nodes.append(node)

        # 3. 拓扑排序确定学习顺序
        if progress_callback:
            await progress_callback(5, "正在分析知识图谱结构...")
        
        # 检查是否已取消
        await wait_if_cancelled()
        
        sorted_nodes = self._topological_sort(valid_nodes, edges)

        # 4. 构建节点映射（用于后续查询）
        node_map = {node["id"]: node for node in sorted_nodes}
        all_node_ids = set(node_map.keys())

        # ==================== 两阶段生成章节结构 ====================
        
        # 第一阶段：生成章节结构（仅生成章-知识点分配）
        if progress_callback:
            await progress_callback(5, "【生成章】正在准备生成章节结构...")
        
        # 检查是否已取消
        await wait_if_cancelled()
        
        # 发送更详细的进度：开始调用AI
        if progress_callback:
            await progress_callback(8, "【生成章】正在连接AI服务...")
        
        chapters_result = await self.ai_provider.generate_chapters_structure(
            nodes=sorted_nodes,
            edges=edges,
            constraints={
                "max_chapters": max_chapters,
                "max_sections_per_chapter": max_sections_per_chapter
            },
            graph_title=knowledge_graph.title,
            graph_description=knowledge_graph.description or "",
            progress_callback=progress_callback
        )
        
        # 获取章节列表
        chapters_data = chapters_result.get("chapters", [])
        
        if progress_callback:
            await progress_callback(52, f"【生成章】已完成！共{len(chapters_data)}章，开始生成节...")

        # 第二阶段：并行生成所有章节的节结构
        if progress_callback:
            await progress_callback(55, "【生成节】开始并行生成各章节的节结构...")
        
        # 检查是否已取消
        await wait_if_cancelled()
        
        # 并行生成所有章节的节结构
        updated_chapters = await self.ai_provider.generate_all_sections_parallel(
            chapters_data=chapters_data,
            nodes_map=node_map,
            max_sections_per_chapter=max_sections_per_chapter,
            progress_callback=progress_callback
        )
        
        # ==================== 两阶段生成完成 ====================
        
        plan_structure = {"chapters": updated_chapters}

        # 6. 计算总学时
        if progress_callback:
            await progress_callback(96, "正在分析章节结构...")
        
        # 检查是否已取消
        await wait_if_cancelled()
        
        total_hours = sum(node.get("estimated_hours", 1.0) for node in sorted_nodes)
        weeks_needed = total_hours / weekly_hours
        end_date = datetime.utcnow() + timedelta(weeks=weeks_needed)

        # 7. 创建学习计划
        if progress_callback:
            await progress_callback(80, "正在保存学习计划...")
        learning_plan = LearningPlan(
            student_id=student_id,
            study_goal_id=study_goal_id,
            graph_id=graph_id,
            title=title or f"{knowledge_graph.title}学习计划",
            description=description or f"预计{weeks_needed:.1f}周完成，每周{weekly_hours}小时",
            status=PlanStatus.ACTIVE.value,
            start_date=datetime.utcnow(),
            end_date=end_date,
            weekly_hours=weekly_hours,
            total_lessons=len(sorted_nodes),
            completed_lessons=0
        )

        self.db.add(learning_plan)
        self.db.commit()
        self.db.refresh(learning_plan)

        # 8. 创建章节和节结构
        chapters_data = plan_structure.get("chapters", [])
        used_node_ids = set()  # 跟踪已分配的节点ID
        lesson_counter = 0  # 全局课时计数器

        for chapter_data in chapters_data:
            # 创建章节
            chapter = Chapter(
                plan_id=learning_plan.id,
                chapter_number=chapter_data.get("chapter_number", 1),
                title=chapter_data.get("title", f"第{chapter_data.get('chapter_number', 1)}章"),
                description=chapter_data.get("description", ""),
                learning_objectives=chapter_data.get("learning_objectives", []),
                estimated_minutes=0,
                ppt_generated=False
            )
            self.db.add(chapter)
            self.db.commit()
            self.db.refresh(chapter)

            chapter_total_minutes = 0
            sections_data = chapter_data.get("sections", [])

            for section_data in sections_data:
                # 创建节
                section = Section(
                    chapter_id=chapter.id,
                    plan_id=learning_plan.id,
                    section_number=section_data.get("section_number", 1),
                    title=section_data.get("title", ""),
                    description=section_data.get("description", ""),
                    knowledge_point_ids=section_data.get("knowledge_point_ids", []),
                    key_concepts=section_data.get("key_concepts", []),
                    learning_objectives=section_data.get("learning_objectives", []),
                    estimated_minutes=0,
                    ppt_generated=False
                )
                self.db.add(section)
                self.db.commit()
                self.db.refresh(section)

                section_total_minutes = 0

                # 创建节内课时
                kp_ids = section_data.get("knowledge_point_ids", [])
                for idx, kp_id in enumerate(kp_ids):
                    if kp_id in node_map and kp_id not in used_node_ids:
                        used_node_ids.add(kp_id)
                        node = node_map[kp_id]
                        lesson_counter += 1

                        lesson = Lesson(
                            plan_id=learning_plan.id,
                            chapter_id=chapter.id,
                            section_id=section.id,
                            lesson_number=lesson_counter,
                            title=node.get("name"),
                            knowledge_point_id=kp_id,
                            introduction=f"本课时将学习：{node.get('name')}",
                            explanation=node.get("description", ""),
                            exercises="[]",
                            estimated_minutes=int(node.get("estimated_hours", 1.0) * 60)
                        )
                        self.db.add(lesson)
                        section_total_minutes += lesson.estimated_minutes

                # 更新节时长
                section.estimated_minutes = section_total_minutes
                chapter_total_minutes += section_total_minutes

            # 更新章节时长
            chapter.estimated_minutes = chapter_total_minutes

        # 9. 处理未分配的节点（如果有的话）
        unassigned_nodes = [n for n in sorted_nodes if n["id"] not in used_node_ids]
        if unassigned_nodes:
            # 为未分配节点创建一个默认章节
            default_chapter = Chapter(
                plan_id=learning_plan.id,
                chapter_number=len(chapters_data) + 1,
                title="补充章节",
                description="包含未归类的重要知识点",
                learning_objectives=["掌握相关知识点"],
                estimated_minutes=0,
                ppt_generated=False
            )
            self.db.add(default_chapter)
            self.db.commit()
            self.db.refresh(default_chapter)

            section_total_minutes = 0
            for node in unassigned_nodes:
                lesson_counter += 1
                lesson = Lesson(
                    plan_id=learning_plan.id,
                    chapter_id=default_chapter.id,
                    section_id=None,
                    lesson_number=lesson_counter,
                    title=node.get("name"),
                    knowledge_point_id=node.get("id"),
                    introduction=f"本课时将学习：{node.get('name')}",
                    explanation=node.get("description", ""),
                    exercises="[]",
                    estimated_minutes=int(node.get("estimated_hours", 1.0) * 60)
                )
                self.db.add(lesson)
                section_total_minutes += lesson.estimated_minutes

            default_chapter.estimated_minutes = section_total_minutes

        self.db.commit()
        
        # 报告完成
        if progress_callback:
            await progress_callback(100, f"学习计划生成完成！共{len(chapters_data)}章")

        return learning_plan

    def get_chapters(self, plan_id: int) -> List[Chapter]:
        """获取计划的所有章节"""
        return self.db.query(Chapter).filter(
            Chapter.plan_id == plan_id
        ).order_by(Chapter.chapter_number).all()

    def get_sections(self, chapter_id: int) -> List[Section]:
        """获取章节的所有节"""
        return self.db.query(Section).filter(
            Section.chapter_id == chapter_id
        ).order_by(Section.section_number).all()

    def get_plan_structure(self, plan_id: int) -> dict:
        """获取完整的章-节-课时结构"""
        plan = self.db.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
        if not plan:
            return None

        chapters = self.get_chapters(plan_id)
        result = {
            "id": plan.id,
            "title": plan.title,
            "description": plan.description,
            "status": plan.status,
            "total_lessons": plan.total_lessons,
            "completed_lessons": plan.completed_lessons,
            "weekly_hours": plan.weekly_hours,
            "chapters": []
        }

        for chapter in chapters:
            sections = self.get_sections(chapter.id)
            chapter_data = {
                "id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "description": chapter.description,
                "learning_objectives": chapter.learning_objectives or [],
                "estimated_minutes": chapter.estimated_minutes,
                "ppt_generated": chapter.ppt_generated,
                "sections": []
            }

            for section in sections:
                # 获取节内的课时
                lessons = self.db.query(Lesson).filter(
                    Lesson.section_id == section.id
                ).order_by(Lesson.lesson_number).all()

                section_data = {
                    "id": section.id,
                    "section_number": section.section_number,
                    "title": section.title,
                    "description": section.description,
                    "knowledge_point_ids": section.knowledge_point_ids or [],
                    "key_concepts": section.key_concepts or [],
                    "learning_objectives": section.learning_objectives or [],
                    "estimated_minutes": section.estimated_minutes,
                    "ppt_generated": section.ppt_generated,
                    "slides": section.ppt_content if section.ppt_generated else [],
                    "lessons": [
                        {
                            "id": lesson.id,
                            "lesson_number": lesson.lesson_number,
                            "title": lesson.title,
                            "is_completed": lesson.is_completed,
                            "estimated_minutes": lesson.estimated_minutes
                        }
                        for lesson in lessons
                    ]
                }
                chapter_data["sections"].append(section_data)

            result["chapters"].append(chapter_data)

        return result

    async def generate_chapter_ppt(self, chapter_id: int, progress_callback=None) -> dict:
        """
        为章节生成PPT内容（两步生成版：先规划，再并行生成）

        Args:
            chapter_id: 章节ID
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            dict: PPT内容（slides数组）
        """
        import traceback
        # 重置取消状态（新PPT生成开始）
        from app.services.cancel_manager import reset_cancel
        reset_cancel()
        print(f"[generate_chapter_ppt] 开始为章节 {chapter_id} 生成PPT，重置取消状态")
        print(f"[generate_chapter_ppt] 调用栈: {traceback.format_stack()[-3]}")
        
        if progress_callback:
            await progress_callback(0, "正在准备生成章节PPT...")
            
        chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"章节不存在：{chapter_id}")

        # 获取章节的所有节
        sections = self.get_sections(chapter_id)

        # 构建节详细内容
        sections_detail = []
        knowledge_points_detail = []

        for section in sections:
            # 获取该节关联的知识点详情
            kp_ids = section.knowledge_point_ids or []
            section_kps = []
            for kp_id in kp_ids:
                # 从知识图谱中获取知识点详情
                graph = self.db.query(KnowledgeGraph).filter(
                    KnowledgeGraph.id == chapter.plan_id
                ).first()
                if graph:
                    nodes = json.loads(graph.nodes) if isinstance(graph.nodes, str) else graph.nodes
                    for node in nodes:
                        if node.get("id") == kp_id:
                            section_kps.append({
                                "name": node.get("name"),
                                "description": node.get("description", ""),
                                "difficulty": node.get("difficulty", "intermediate")
                            })
                            break

            sections_detail.append({
                "section_number": section.section_number,
                "title": section.title,
                "description": section.description,
                "key_concepts": section.key_concepts or [],
                "learning_objectives": section.learning_objectives or []
            })

            knowledge_points_detail.extend(section_kps)

        # 构建上下文
        chapter_context = {
            "title": chapter.title,
            "chapter_number": chapter.chapter_number,
            "description": chapter.description or "",
            "learning_objectives": chapter.learning_objectives or [],
            "sections": sections_detail,
            "knowledge_points": knowledge_points_detail
        }
        
        # 步骤1：生成PPT结构规划 (0-30%)
        if progress_callback:
            await progress_callback(10, "正在规划章节PPT结构...")
        
        try:
            ppt_plan = await self.ai_provider.generate_ppt_plan(
                plan_type="chapter",
                context=chapter_context,
                progress_callback=progress_callback
            )
            
            slides_plan = ppt_plan.get("slides_plan", [])
            total_slides = ppt_plan.get("total_slides", len(slides_plan))
            
            if progress_callback:
                await progress_callback(30, f"规划完成，共{total_slides}页，开始生成内容...")
            
            # 步骤2：并行生成每页内容 (30-100%)
            chapter_context["total_slides"] = total_slides
            all_slides = await self._generate_slides_parallel(
                slides_plan=slides_plan,
                context=chapter_context,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                await progress_callback(100, "章节PPT生成完成！")
            
            # 保存PPT内容到章节
            chapter.ppt_generated = True
            chapter.ppt_content = all_slides
            self.db.commit()
            
            return {"slides": all_slides}
            
        except GenerationCancelledError:
            print(f"[generate_chapter_ppt] 用户取消了章节{chapter_id}的PPT生成")
            self.db.rollback()
            raise GenerationCancelledError(f"用户取消了章节{chapter_id}的PPT生成")
        except Exception as e:
            print(f"[generate_chapter_ppt] 章节{chapter_id}生成PPT时出错: {str(e)}")
            self.db.rollback()
            raise

    async def _generate_slides_parallel(
        self,
        slides_plan: list,
        context: dict,
        progress_callback=None
    ) -> list:
        """
        生成PPT幻灯片内容
        - Ollama模型：串行调用，每次生成3页，多次生成直到完成
        - 其他模型：并行调用，每次生成3页，2并发

        Args:
            slides_plan: PPT结构规划列表
            context: 上下文信息
            progress_callback: 进度回调函数

        Returns:
            list: 完整slides列表（如果被取消，可能只包含部分完成的内容）
        """
        import asyncio
        from app.services.cancel_manager import GenerationCancelledError
        
        total_slides = len(slides_plan)
        
        # 判断是否为 Ollama 模型
        is_ollama = self.ai_provider.is_ollama()
        
        # 将幻灯片分批：每批3页，减少AI调用次数
        batch_size = 3
        batches = []
        for i in range(0, total_slides, batch_size):
            batches.append(slides_plan[i:i + batch_size])
        
        # Ollama模型使用串行（更稳定），其他模型使用并行（更快）
        if is_ollama:
            max_concurrent = 1  # Ollama：串行
            print(f"[PPT生成] 使用Ollama模型，共{total_slides}页，分{len(batches)}批，每批{batch_size}页，串行生成")
        else:
            max_concurrent = 5  # 云端API：最大5并发
            print(f"[PPT生成] 使用云端模型，共{total_slides}页，分{len(batches)}批，每批{batch_size}页，{max_concurrent}并发生成")
        
        # 根据模型类型设置并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        # 用于存储已完成的结果
        completed_slides = []
        # 锁用于保护 completed_slides 的访问
        lock = asyncio.Lock()
        # 标记是否已取消
        is_cancelled = False
        # 当前进度
        current_progress = 0
        
        async def generate_batch(batch: list, batch_index: int) -> list:
            """生成一批幻灯片内容（一次调用生成批次内的所有幻灯片）"""
            nonlocal is_cancelled, current_progress
            
            async with semaphore:
                # 检查是否已取消
                if is_cancelled:
                    print(f"[PPT生成] 批次 {batch_index} 被跳过（已取消）")
                    return [
                        {
                            "index": slide_plan.get("index", 0),
                            "type": slide_plan.get("type", "content"),
                            "title": slide_plan.get("title", ""),
                            "content": f"【{slide_plan.get('title', '')}】\n\n" + "、".join(slide_plan.get("key_points", [])),
                            "notes": "",
                            "skipped": True
                        }
                        for slide_plan in batch
                    ]
                
                try:
                    # 一次调用生成批次内的所有幻灯片
                    batch_results = await self.ai_provider.generate_batch_slides_content(
                        slides_plan=batch,
                        context=context,
                        previous_slides=completed_slides
                    )
                    
                    # 更新进度
                    async with lock:
                        completed_slides.extend(batch_results)
                        current_progress += len(batch_results)
                        if progress_callback and total_slides > 0:
                            progress = 35 + int(current_progress / total_slides * 60)
                            await progress_callback(progress, f"生成中... ({current_progress}/{total_slides})")
                    
                    return batch_results
                    
                except GenerationCancelledError:
                    is_cancelled = True
                    print(f"[PPT生成] 批次 {batch_index} 检测到取消")
                    return [
                        {
                            "index": slide_plan.get("index", 0),
                            "type": slide_plan.get("type", "content"),
                            "title": slide_plan.get("title", ""),
                            "content": f"【{slide_plan.get('title', '')}】\n\n" + "、".join(slide_plan.get("key_points", [])),
                            "notes": "",
                            "skipped": True
                        }
                        for slide_plan in batch
                    ]
                except Exception as e:
                    print(f"[PPT生成] 批次 {batch_index} 生成失败: {e}")
                    return [
                        {
                            "index": slide_plan.get("index", 0),
                            "type": slide_plan.get("type", "content"),
                            "title": slide_plan.get("title", ""),
                            "content": f"【{slide_plan.get('title', '')}】\n\n" + "、".join(slide_plan.get("key_points", [])),
                            "notes": ""
                        }
                        for slide_plan in batch
                    ]
        
        # 并行生成所有批次
        tasks = [
            generate_batch(batch, idx)
            for idx, batch in enumerate(batches)
        ]
        
        if progress_callback:
            await progress_callback(35, f"开始生成{total_slides}页PPT（分{len(batches)}批，每批{batch_size}页）...")
        
        # 等待所有批次完成
        batch_results = await asyncio.gather(*tasks)
        
        # 合并所有结果
        all_slides = []
        for batch_result in batch_results:
            all_slides.extend(batch_result)
        
        # 按index排序
        all_slides.sort(key=lambda x: x.get("index", 0))
        
        if progress_callback:
            await progress_callback(100, "PPT生成完成！")
        
        return all_slides

    async def generate_section_ppt(self, section_id: int, progress_callback=None) -> dict:
        """
        为节生成PPT内容（两步生成版：先规划，再并行生成）

        Args:
            section_id: 节ID
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            dict: PPT内容（slides数组）
        """
        import traceback
        # 重置取消状态（新PPT生成开始）
        from app.services.cancel_manager import reset_cancel
        reset_cancel()
        print(f"[generate_section_ppt] 开始为节 {section_id} 生成PPT，重置取消状态")
        print(f"[generate_section_ppt] 调用栈: {traceback.format_stack()[-3]}")
        
        if progress_callback:
            await progress_callback(0, "正在准备生成PPT...")
        
        section = self.db.query(Section).filter(Section.id == section_id).first()
        if not section:
            raise ValueError(f"节不存在：{section_id}")

        if progress_callback:
            await progress_callback(5, f"正在获取节信息：{section.title}...")

        chapter = self.db.query(Chapter).filter(Chapter.id == section.chapter_id).first()

        # 获取知识点详情
        kp_ids_raw = section.knowledge_point_ids
        if kp_ids_raw is None:
            kp_ids = []
        elif isinstance(kp_ids_raw, str):
            try:
                kp_ids = json.loads(kp_ids_raw)
            except json.JSONDecodeError:
                kp_ids = []
        elif isinstance(kp_ids_raw, list):
            kp_ids = kp_ids_raw
        else:
            kp_ids = []
        
        knowledge_points_detail = []

        # 获取知识图谱
        if section.plan_id:
            graph = self.db.query(KnowledgeGraph).filter(
                KnowledgeGraph.id == section.plan_id
            ).first()
            
            if graph:
                nodes = graph.nodes
                if isinstance(nodes, str):
                    try:
                        nodes = json.loads(nodes)
                    except json.JSONDecodeError:
                        nodes = []
                
                if isinstance(nodes, list):
                    node_map = {}
                    for node in nodes:
                        node_id = node.get("id")
                        if isinstance(node_id, int):
                            node_map[node_id] = node
                        elif isinstance(node_id, str):
                            node_map[int(node_id) if node_id.isdigit() else node_id] = node
                    
                    for kp_id in kp_ids:
                        lookup_id = int(kp_id) if isinstance(kp_id, str) and kp_id.isdigit() else kp_id
                        node = node_map.get(lookup_id) or node_map.get(str(lookup_id))
                        if node:
                            knowledge_points_detail.append({
                                "id": node.get("id"),
                                "name": node.get("name"),
                                "description": node.get("description", ""),
                                "difficulty": node.get("difficulty", "intermediate"),
                                "estimated_hours": node.get("estimated_hours", 1.0)
                            })

        # 构建上下文
        section_context = {
            "title": section.title,
            "chapter_title": chapter.title if chapter else "",
            "section_number": section.section_number,
            "key_concepts": section.key_concepts or [],
            "learning_objectives": section.learning_objectives or [],
            "knowledge_points": knowledge_points_detail
        }
        
        # 步骤1：生成PPT结构规划 (0-30%)
        if progress_callback:
            await progress_callback(10, "正在规划PPT结构...")
        
        try:
            ppt_plan = await self.ai_provider.generate_ppt_plan(
                plan_type="section",
                context=section_context,
                progress_callback=progress_callback
            )
            
            slides_plan = ppt_plan.get("slides_plan", [])
            total_slides = ppt_plan.get("total_slides", len(slides_plan))
            
            if progress_callback:
                await progress_callback(30, f"规划完成，共{total_slides}页，开始生成内容...")
            
            # 步骤2：并行生成每页内容 (30-100%)
            section_context["total_slides"] = total_slides
            all_slides = await self._generate_slides_parallel(
                slides_plan=slides_plan,
                context=section_context,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                await progress_callback(100, "PPT生成完成！")
            
            # 保存PPT内容到节
            section.ppt_generated = True
            section.ppt_content = all_slides
            self.db.commit()
            
            return {"slides": section.ppt_content}
            
        except GenerationCancelledError:
            # 用户取消，返回已生成的部分内容
            print(f"[generate_section_ppt] 用户取消了节{section_id}的PPT生成")
            self.db.rollback()
            # 仍然抛出异常，让上层API能正确处理取消
            raise GenerationCancelledError(f"用户取消了节{section_id}的PPT生成")
        except Exception as e:
            print(f"[generate_section_ppt] 节{section_id}生成PPT时出错: {str(e)}")
            self.db.rollback()
            raise

    def get_chapter_ppt(self, chapter_id: int) -> Optional[dict]:
        """获取章节PPT内容"""
        chapter = self.db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            return None

        return {
            "chapter_id": chapter.id,
            "chapter_title": chapter.title,
            "ppt_generated": chapter.ppt_generated,
            "slides": chapter.ppt_content if chapter.ppt_generated else None
        }

    def get_section_ppt(self, section_id: int) -> Optional[dict]:
        """获取节PPT内容"""
        section = self.db.query(Section).filter(Section.id == section_id).first()
        if not section:
            return None

        return {
            "section_id": section.id,
            "section_title": section.title,
            "ppt_generated": section.ppt_generated,
            "slides": section.ppt_content if section.ppt_generated else None
        }
