"""
习题库 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import asyncio
import os
import uuid
import random

from app.core.database import get_db
from app.api.deps import get_current_student_id
from app.services.engine_manager import get_module_provider
from app.schemas import Response
from app.models.study_goal import StudyGoal
from app.models.assessment import QuestionBank, Assessment
from app.models.node_mastery import NodeMastery
from app.models.knowledge_graph import KnowledgeGraph, KnowledgeNode
from app.models.learning_plan import LearningPlan, Lesson
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


def _get_ai_provider():
    """
    获取AI Provider实例（使用缓存的单例，确保连接复用）
    注意：配置变更时需要调用 reset_ai_provider_cache() 清除缓存
    """
    return get_module_provider("exercise")


def _parse_nodes(graph_nodes):
    """解析知识图谱节点，处理字符串或列表格式"""
    if not graph_nodes:
        return []
    
    # 如果是字符串，尝试解析JSON
    if isinstance(graph_nodes, str):
        try:
            return json.loads(graph_nodes)
        except json.JSONDecodeError:
            print(f"[解析节点] JSON解析失败: {graph_nodes[:100]}")
            return []
    
    # 如果已经是列表，直接返回
    if isinstance(graph_nodes, list):
        return graph_nodes
    
    return []


def _determine_difficulty(mastery_level: float, total_attempts: int) -> str:
    """
    根据掌握度和尝试次数确定推荐题目难度
    
    规则：
    - 刚开始学习(total_attempts < 3)或掌握度<60 → basic (基础题)
    - 掌握度60-80 → comprehensive (综合题)
    - 掌握度>=80 → challenge (挑战题)
    """
    if total_attempts < 3 or mastery_level < 60:
        return "basic"
    elif mastery_level < 80:
        return "comprehensive"
    else:
        return "challenge"


@router.get("/{goal_id}/knowledge-points", response_model=Response)
async def get_knowledge_points(
    goal_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取知识图谱中的所有知识点（用于生成题目时选择）
    
    ## 参数
    - goal_id: 学习目标ID
    """
    # 验证学习目标存在
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取知识图谱
    graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    
    nodes = _parse_nodes(graph.nodes if graph else None)
    
    if not nodes:
        return Response(
            success=True,
            message="该学习目标暂无知识图谱",
            data={"knowledge_points": []}
        )
    
    # 格式化知识点列表
    knowledge_points = []
    for node in nodes:
        knowledge_points.append({
            "id": node.get('id'),
            "name": node.get('label', node.get('name', '未命名')),
            "description": node.get('description', ''),
            "difficulty": node.get('difficulty', 'medium'),
            "category": node.get('category', '其他')
        })
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "knowledge_points": knowledge_points,
            "total": len(knowledge_points)
        }
    )


@router.get("/{goal_id}", response_model=Response)
async def list_questions(
    goal_id: int,
    difficulty: Optional[str] = None,
    knowledge_point_id: Optional[str] = None,
    knowledge_point_ids: Optional[str] = None,  # 多个知识点ID，逗号分隔
    question_type: Optional[str] = None,
    is_ai_generated: Optional[bool] = None,  # 是否AI生成筛选
    limit: int = 20,
    offset: int = 0,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取习题列表
    
    ## 参数
    - difficulty: 难度筛选 (basic/comprehensive/challenge)
    - knowledge_point_id: 单个知识点ID筛选
    - knowledge_point_ids: 多个知识点ID筛选（逗号分隔）
    - question_type: 题型筛选 (choice/fill_blank/short_answer)
    - is_ai_generated: 是否AI生成筛选 (true/false)
    - limit: 返回数量
    - offset: 偏移量
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    query = db.query(QuestionBank).filter(QuestionBank.study_goal_id == goal_id)
    
    if difficulty:
        query = query.filter(QuestionBank.difficulty == difficulty)
    if knowledge_point_id:
        query = query.filter(QuestionBank.knowledge_point_id == knowledge_point_id)
    if knowledge_point_ids:
        # 支持多个知识点ID筛选
        ids = [id.strip() for id in knowledge_point_ids.split(',') if id.strip()]
        if ids:
            query = query.filter(QuestionBank.knowledge_point_id.in_(ids))
    if question_type:
        query = query.filter(QuestionBank.question_type == question_type)
    if is_ai_generated is not None:
        query = query.filter(QuestionBank.is_ai_generated == is_ai_generated)
    
    total = query.count()
    questions = query.order_by(QuestionBank.created_at.desc()).offset(offset).limit(limit).all()
    
    # 获取知识图谱以查找知识点名称
    graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    nodes = _parse_nodes(graph.nodes if graph else None)
    node_name_map = {}
    for node in nodes:
        node_name_map[node.get('id')] = node.get('label', node.get('name', '未知知识点'))
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "total": total,
            "limit": limit,
            "offset": offset,
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "knowledge_point_id": q.knowledge_point_id,
                    "knowledge_point_name": node_name_map.get(q.knowledge_point_id, '未知知识点'),
                    "explanation": q.explanation if q.explanation and q.explanation.strip() else "本题考察相关知识点，请结合所学内容进行分析。",
                    "is_ai_generated": q.is_ai_generated,
                    "question_number": q.question_number,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                }
                for q in questions
            ]
        }
    )


class GenerateQuestionsRequest(BaseModel):
    node_id: Optional[str] = None  # 单个知识点ID（兼容旧接口）
    node_ids: Optional[List[str]] = None  # 多个知识点ID
    count: int = 5  # 每个知识点生成的题目数量
    difficulty: str = "basic"  # basic/comprehensive/challenge (基础题/综合题/挑战题)
    batch_mode: bool = False  # 是否为批量模式（为每个知识点生成count道题目）


# ============ 习题上传相关请求模型 ============

class QuestionOption(BaseModel):
    """题目选项"""
    key: str  # A, B, C, D
    text: str  # 选项内容


class CreateQuestionRequest(BaseModel):
    """创建单道题目请求"""
    question_text: str  # 题干
    question_type: str = "choice"  # 题型: choice/fill_blank/short_answer
    difficulty: str = "basic"  # 难度: basic/comprehensive/challenge
    knowledge_point_id: Optional[str] = None  # 关联知识点ID
    options: List[QuestionOption]  # 选项列表
    correct_answer: str  # 正确答案
    explanation: Optional[str] = None  # 答案解析


class BatchCreateQuestionsRequest(BaseModel):
    """批量创建题目请求"""
    questions: List[CreateQuestionRequest]


class ParseQuestionsResponse(BaseModel):
    """解析题目响应"""
    questions: List[dict]  # 解析出的题目列表
    total_count: int  # 解析出的题目数量
    parsing_status: str  # 解析状态: success/partial/failed
    message: Optional[str] = None  # 状态说明


# 难度配置映射
DIFFICULTY_MAP = {
    'basic': {
        'name': '基础题',
        'description': '考察基本概念、定义、事实性知识，题目直接明了',
        'old_map': 'easy'
    },
    'comprehensive': {
        'name': '综合题',
        'description': '考察理解、应用、简单分析，需要结合多个概念',
        'old_map': 'medium'
    },
    'challenge': {
        'name': '挑战题',
        'description': '考察综合分析、复杂应用、深度理解，题目有挑战性',
        'old_map': 'hard'
    }
}


def _generate_question_number(goal_id: int, db: Session) -> str:
    """生成唯一的题目编号"""
    import random
    timestamp = datetime.now().strftime('%Y%m%d')
    random_suffix = random.randint(1000, 9999)
    return f"Q-{goal_id}-{timestamp}-{random_suffix}"


def _get_existing_questions_by_node(db: Session, goal_id: int, node_id: str, difficulty: str = None) -> List[dict]:
    """
    获取指定知识点已有的AI生成题目列表
    仅返回题目和选项（不含解析），用于串行生成时的去重上下文
    按知识点和难度筛选
    """
    query = db.query(QuestionBank).filter(
        QuestionBank.study_goal_id == goal_id,
        QuestionBank.knowledge_point_id == node_id,
        QuestionBank.is_ai_generated == True
    )
    
    # 按难度筛选
    if difficulty:
        query = query.filter(QuestionBank.difficulty == difficulty)
    
    existing = query.all()
    
    result = []
    for q in existing:
        # 返回题目和选项，不包含解析
        options_text = ""
        if q.options:
            if isinstance(q.options, str):
                options_text = q.options
            elif isinstance(q.options, list):
                options_text = "\n".join([f"{opt.get('key', '')}. {opt.get('text', '')}" if isinstance(opt, dict) else str(opt) for opt in q.options])
        
        result.append({
            "question_text": q.question_text,
            "answer": q.correct_answer,
            "options": options_text,
            "difficulty": q.difficulty
        })
    
    return result


def _check_duplicate_question(new_question: str, existing_questions: List[dict], similarity_threshold: float = 0.6) -> tuple:
    """
    检查新题目是否与已有题目重复
    
    Args:
        new_question: 新题目的题干
        existing_questions: 已有的题目列表（包含 question_text, answer, options）
        similarity_threshold: 相似度阈值，超过则认为是重复
    
    Returns:
        (is_duplicate: bool, similar_question: str or None)
    """
    if not existing_questions:
        return False, None
    
    # 简单文本相似度检查：去除标点符号和空格后比较
    normalized_new = ''.join(c for c in new_question if c.isalnum()).lower()
    
    for existing in existing_questions:
        question_text = existing.get('question_text', '')
        normalized_existing = ''.join(c for c in question_text if c.isalnum()).lower()
        
        # 计算字符集重叠度 (Jaccard Similarity)
        set_new = set(normalized_new)
        set_existing = set(normalized_existing)
        
        if not set_new or not set_existing:
            continue
            
        intersection = len(set_new & set_existing)
        union = len(set_new | set_existing)
        similarity = intersection / union if union > 0 else 0
        
        # 长度相近且相似度高，认为是重复
        len_ratio = min(len(normalized_new), len(normalized_existing)) / max(len(normalized_new), len(normalized_existing)) if max(len(normalized_new), len(normalized_existing)) > 0 else 0
        
        if similarity >= similarity_threshold and len_ratio >= 0.7:
            return True, question_text
    
    return False, None


async def _generate_questions_by_node_group(
    node_group: List[dict],
    difficulty: str,
    goal_title: str,
    max_retries: int = 3,
    goal_description: str = None,
    section_title: str = None
) -> List[dict]:
    """
    为同一知识点+难度的多个题目生成任务串行生成（保证不重复）
    
    Args:
        node_group: 同一知识点的节点列表（可能重复）
        difficulty: 难度级别
        goal_title: 学习目标标题
        max_retries: 最大重试次数
        goal_description: 学习目标描述（可选）
        section_title: 当前学习小节标题（可选）
    
    Returns:
        生成的题目列表
    """
    if not node_group:
        return []

    # 获取知识点ID和名称
    node_id = node_group[0].get('id', '')
    node_name = node_group[0].get('label', node_group[0].get('name', ''))
    goal_id = node_group[0].get('goal_id', 0)

    # 获取该知识点+难度的已有题目（从数据库实时查询，确保最新）
    db = next(get_db())
    existing_questions = _get_existing_questions_by_node(db, goal_id, node_id, difficulty=difficulty)
    db.close()

    print(f"[串行生成] 知识点 '{node_name}', 难度 '{difficulty}', 已有 {len(existing_questions)} 道题目")

    results = []

    from app.services.cancel_manager import wait_if_cancelled

    for i, node in enumerate(node_group):
        # 检查是否已取消
        await wait_if_cancelled()
        print(f"[串行生成] 知识点 '{node_name}' 题目 {i+1}/{len(node_group)}")
        
        try:
            result = await _generate_question_for_node(
                node=node,
                difficulty=difficulty,
                goal_title=goal_title,
                existing_questions=existing_questions,
                max_retries=max_retries,
                goal_description=goal_description,
                section_title=section_title
            )
            
            if result is None:
                print(f"[串行生成] 知识点 '{node_name}' 题目 {i+1} 生成失败")
                continue
            
            # 将新生成的题目添加到已有列表（用于后续去重）
            existing_questions.append({
                "question_text": result['question'],
                "answer": result.get('answer', ''),
                "options": "\n".join(result.get('options', [])) if result.get('options') else ''
            })
            
            results.append(result)
            
        except GenerationCancelledError:
            # 取消异常向上传播
            raise
        except Exception as e:
            print(f"[串行生成] 知识点 '{node_name}' 题目 {i+1} 异常: {e}")
            continue
    
    return results


async def _generate_parallel_node_groups(
    node_groups: List[tuple],
    difficulty: str,
    goal_title: str,
    concurrency: int = 5,
    max_retries: int = 3,
    goal_description: str = None,
    section_title: str = None
) -> List[dict]:
    """
    并行生成多个知识点组的题目
    - 不同知识点之间：并行（并发数5）
    - 同知识点不同难度：并行
    - 同知识点同难度：串行（保证不重复）
    
    Args:
        node_groups: [(node, count), ...] 元组列表
        difficulty: 难度级别
        goal_title: 学习目标标题
        concurrency: 并发数（默认5）
        max_retries: 最大重试次数
        goal_description: 学习目标描述（可选）
        section_title: 当前学习小节标题（可选）
    
    Returns:
        所有生成的题目列表
    """
    import asyncio
    
    # 创建知识点节点列表（每个节点复制 count 次）
    expanded_nodes = []
    for node, count in node_groups:
        for _ in range(count):
            expanded_nodes.append(node)

    if not expanded_nodes:
        return []

    # 按知识点ID分组
    node_id_map = {}
    for node in expanded_nodes:
        nid = node.get('id', '')
        if nid not in node_id_map:
            node_id_map[nid] = []
        node_id_map[nid].append(node)

    # 使用信号量控制并发数
    semaphore = asyncio.Semaphore(concurrency)

    async def generate_single_node_group(nid: str, nodes: List[dict]):
        """
        为单个知识点生成多道题目（串行生成，保证同知识点同难度不重复）
        """
        node_name = nodes[0].get('label', nodes[0].get('name', ''))
        goal_id = nodes[0].get('goal_id', 0)
        
        # 获取该知识点+难度的已有题目
        db = next(get_db())
        existing_questions = _get_existing_questions_by_node(db, goal_id, nid, difficulty=difficulty)
        db.close()
        
        print(f"[并行生成] 知识点 '{node_name}', 难度 '{difficulty}', 已有 {len(existing_questions)} 道题目")

        results = []
        for i, node in enumerate(nodes):
            print(f"[并行生成] 知识点 '{node_name}' 题目 {i+1}/{len(nodes)}")
            
            result = await _generate_question_for_node(
                node=node,
                difficulty=difficulty,
                goal_title=goal_title,
                existing_questions=existing_questions,
                max_retries=max_retries,
                goal_description=goal_description,
                section_title=section_title
            )
            
            if result is None:
                continue
            
            # 将新生成的题目添加到已有列表（用于后续去重）
            existing_questions.append({
                "question_text": result['question'],
                "answer": result.get('answer', ''),
                "options": "\n".join(result.get('options', [])) if result.get('options') else ''
            })
            
            results.append(result)
        
        return results
    
    async def generate_with_limit(nid: str, nodes: List[dict]):
        async with semaphore:
            return await generate_single_node_group(nid, nodes)
    
    # 并行执行所有知识点组的生成任务
    tasks = [generate_with_limit(nid, nodes) for nid, nodes in node_id_map.items()]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 收集所有结果
    all_results = []
    for results in results_list:
        if isinstance(results, list):
            all_results.extend(results)
        elif isinstance(results, Exception):
            print(f"[并行生成] 任务异常: {results}")
    
    return all_results


def _group_nodes_by_knowledge_point(
    target_nodes: List[dict]
) -> List[tuple]:
    """
    将目标节点按知识点分组
    
    Args:
        target_nodes: 目标节点列表
    
    Returns:
        [(node, count), ...] 元组列表
    """
    # 按知识点ID分组
    node_id_map = {}
    for node in target_nodes:
        nid = node.get('id', '')
        if nid not in node_id_map:
            node_id_map[nid] = {
                'node': node,
                'count': 0
            }
        node_id_map[nid]['count'] += 1
    
    # 返回元组列表
    return [(v['node'], v['count']) for v in node_id_map.values()]


async def _generate_question_for_node(
    node: dict,
    difficulty: str,
    goal_title: str,
    existing_questions: List[dict] = None,
    max_retries: int = 3,
    goal_description: str = None,
    section_title: str = None
) -> Optional[dict]:
    """
    为单个知识点生成题目
    
    Args:
        node: 知识点节点信息
        difficulty: 难度级别 (basic/comprehensive/challenge)
        goal_title: 学习目标标题
        existing_questions: 该知识点已有的题目列表（用于去重）
        max_retries: 最大重试次数（生成重复题目时）
        goal_description: 学习目标描述（可选）
        section_title: 当前学习小节标题（可选）
    
    Returns:
        生成的题目字典，失败返回None
    """
    node_id = node.get('id', '')
    node_name = node.get('label', node.get('name', ''))
    node_description = node.get('description', '')
    
    # 获取难度配置
    difficulty_config = DIFFICULTY_MAP.get(difficulty, DIFFICULTY_MAP['basic'])
    difficulty_name = difficulty_config['name']
    difficulty_desc = difficulty_config['description']
    
    # 构建已有题目上下文（用于去重）
    existing_context = ""
    if existing_questions and len(existing_questions) > 0:
        existing_list = []
        for q in existing_questions[:5]:
            item = f"题目: {q['question_text']}"
            if q.get('options'):
                item += f"\n选项:\n{q['options']}"
            if q.get('answer'):
                item += f"\n答案: {q['answer']}"
            existing_list.append(item)
        existing_context = f"""
【该知识点已有的题目（请务必生成与以下题目不同的新题目，从不同角度、问法来考察）】\n""" + "\n\n".join([f"- {item}" for item in existing_list])
    
    # 构建学习目标背景信息
    goal_background = f"- 学习目标：{goal_title}"
    if goal_description:
        goal_background += f"\n- 目标描述：{goal_description}"
    
    # 构建小节信息
    section_info = ""
    if section_title:
        section_info = f"- 小节：{section_title}"
    
    # 构建增强版提示词，加入严格约束
    system_prompt = f"""你是一位专业的出题老师。

【学习目标背景】
{goal_background}
{section_info if section_info else ""}

【知识点详情】
- 知识点名称：{node_name}
- 知识点描述：{node_description}
- 难度级别：{difficulty_name}

【严格出题要求】
1. 题目必须100%围绕「{node_name}」这个知识点展开
2. 题目内容必须与「{goal_title}」学习目标的范畴保持一致
3. 绝对禁止引入与「{node_name}」无关的内容或超出「{goal_title}」范围的知识
4. 题干清晰、选项区分度高、答案准确
5. 禁止与已有题目重复
6. **重要：question 字段必须填写完整的题干内容，不能为空！**

{existing_context}

难度要求：{difficulty_desc}

输出JSON格式：
{{"question":"**完整的中文问题题干（必须填写，不能为空）**","options":[{{"key":"A","text":"选项A"}},{{"key":"B","text":"选项B"}},{{"key":"C","text":"选项C"}},{{"key":"D","text":"选项D"}}],"answer":"A","explanation":"解析"}}"""

    user_prompt = f"""请根据以上要求，为知识点「{node_name}」生成一道{difficulty_name}。
知识点描述：{node_description}
**重要提醒：生成的题目题干（question 字段）必须是完整的中文问题，不能为空！**"""

    from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError

    for attempt in range(max_retries):
        try:
            # 检查是否已取消
            await wait_if_cancelled()

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 每次调用都获取最新的 AI Provider，确保使用最新配置
            ai_provider = _get_ai_provider()
            response = await ai_provider.chat(messages, temperature=0.7)
            
            # 检查是否已取消（AI调用完成后立即检查）
            await wait_if_cancelled()
            
            # 解析JSON响应
            try:
                # 预处理：去除 markdown 代码块包裹
                cleaned_response = response.strip()
                if cleaned_response.startswith('```'):
                    lines = cleaned_response.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    cleaned_response = '\n'.join(lines)
                
                question_data = json.loads(cleaned_response)
                
                # 验证必要字段
                if not all(k in question_data for k in ['question', 'options', 'answer']):
                    print(f"[生成题目] 缺少必要字段: {question_data.keys()}")
                    continue
                
                # 验证选项格式
                options = question_data.get('options', [])
                if len(options) < 4:
                    print(f"[生成题目] 选项数量不足: {len(options)}")
                    continue
                
                # 检查是否与已有题目重复
                if existing_questions:
                    is_dup, similar_q = _check_duplicate_question(
                        question_data.get('question', ''),
                        existing_questions
                    )
                    if is_dup:
                        print(f"[生成题目] 检测到重复题目，重试 {attempt + 1}/{max_retries}")
                        print(f"  新题目: {question_data.get('question', '')[:50]}...")
                        print(f"  相似题目: {similar_q[:50]}...")
                        existing_questions.append({
                            "question_text": question_data.get('question', ''),
                            "answer": question_data.get('answer', '')
                        })
                        continue
                
                # 格式化选项
                formatted_options = []
                for opt in options:
                    if isinstance(opt, dict):
                        formatted_options.append(f"{opt.get('key', '')}. {opt.get('text', '')}")
                    else:
                        formatted_options.append(str(opt))
                
                return {
                    'node_id': node_id,
                    'node_name': node_name,
                    'question': question_data.get('question', ''),
                    'options': formatted_options,
                    'answer': question_data.get('answer', ''),
                    'explanation': question_data.get('explanation', ''),
                    'difficulty': difficulty
                }
                
            except json.JSONDecodeError as e:
                print(f"[生成题目] JSON解析失败: {e}, 原始响应: {response[:200]}")
                continue
                
        except GenerationCancelledError:
            # 取消异常向上传播
            raise
        except Exception as e:
            print(f"[生成题目] AI调用失败: {e}")
            continue
    
    print(f"[生成题目] 达到最大重试次数，生成失败")
    return None


@router.post("/{goal_id}/generate", response_model=Response)
async def generate_questions(
    goal_id: int,
    request: GenerateQuestionsRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    AI生成习题 - 基于知识图谱知识点生成
    
    ## 参数
    - node_id: 单个知识点ID（兼容旧接口，与node_ids互斥）
    - node_ids: 多个知识点ID列表（批量生成时使用）
    - count: 每个知识点生成的题目数量
    - difficulty: 难度 (basic/comprehensive/challenge)
    - batch_mode: 是否为批量模式（为每个知识点生成count道题目）
    """
    import random
    
    # 重置取消状态，确保新请求不受上次取消的影响
    from app.services.cancel_manager import reset_cancel
    reset_cancel()
    
    # 调试日志
    print(f"[生成题目] 接收参数: goal_id={goal_id}, node_ids={request.node_ids}, count={request.count}, batch_mode={request.batch_mode}")
    
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取知识图谱
    graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    
    nodes = _parse_nodes(graph.nodes if graph else None)
    
    if not nodes:
        raise HTTPException(status_code=400, detail="该学习目标没有知识图谱，请先创建知识图谱")
    
    # 构建节点映射表
    node_map = {n.get('id'): n for n in nodes if n.get('id')}
    
    # 确定要生成题目的知识点列表
    target_nodes = []
    
    if request.node_ids and len(request.node_ids) > 0:
        # 使用指定的知识点列表，每个知识点生成 count 道题目
        for node_id in request.node_ids:
            if node_id in node_map:
                # 无论 batch_mode 如何，指定知识点时按 count 生成
                target_nodes.extend([node_map[node_id]] * request.count)
    elif request.node_id:
        # 使用单个知识点（兼容旧接口）
        if request.node_id in node_map:
            target_nodes = [node_map[request.node_id]] * request.count
        else:
            raise HTTPException(status_code=404, detail="指定的知识点不存在")
    else:
        # 随机选择知识点
        random.seed()
        candidate_nodes = list(node_map.values())
        if request.batch_mode:
            # 批量模式：为每个知识点生成count道题目
            for node in candidate_nodes:
                target_nodes.extend([node] * request.count)
        else:
            # 普通模式：随机选择count个知识点
            target_nodes = [random.choice(candidate_nodes) for _ in range(request.count)]
    
    if not target_nodes:
        raise HTTPException(status_code=400, detail="没有有效的知识点用于生成题目")
    
    print(f"[生成题目] 目标节点数量: {len(target_nodes)}, 节点列表: {[n.get('label', n.get('name')) for n in target_nodes]}")
    
    # 获取每个节点已有的题目（用于去重）
    node_existing_questions = {}
    for node in target_nodes:
        node_id = node.get('id', '')
        if node_id not in node_existing_questions:
            existing = _get_existing_questions_by_node(db, goal_id, node_id)
            node_existing_questions[node_id] = existing
            if existing:
                print(f"[生成题目] 知识点 {node.get('label', node.get('name'))} 已有 {len(existing)} 道题目")
    
    # 为每个节点添加 goal_id 用于后续查询
    for node in target_nodes:
        node['goal_id'] = goal_id
    
    # 检查是否为 Ollama 模型
    ai_provider = _get_ai_provider()
    is_ollama = ai_provider.is_ollama()
    print(f"[生成题目] AI模型类型: {'Ollama (串行)' if is_ollama else 'API服务 (并行)'}")
    
    # 按知识点分组
    node_groups = _group_nodes_by_knowledge_point(target_nodes)
    
    # 生成题目
    generated_results = []
    
    if is_ollama:
        # Ollama 模型：全部串行生成
        print(f"[生成题目] 使用 Ollama 串行策略")
        for node, count in node_groups:
            # 创建该知识点的节点组
            node_group = [node] * count
            node_group[0]['goal_id'] = goal_id
            
            results = await _generate_questions_by_node_group(
                node_group=node_group,
                difficulty=request.difficulty,
                goal_title=goal.title,
                max_retries=3,
                goal_description=goal.description,
                section_title=None
            )
            generated_results.extend(results)
    else:
        # 非 Ollama 模型：并行生成（不同知识点并行，同知识点串行）
        print(f"[生成题目] 使用并行策略，并发数=5")
        generated_results = await _generate_parallel_node_groups(
            node_groups=node_groups,
            difficulty=request.difficulty,
            goal_title=goal.title,
            concurrency=5,
            max_retries=3,
            goal_description=goal.description,
            section_title=None
        )
    
    print(f"[生成题目] AI生成结果数量: {len(generated_results)}")
    
    # 保存到数据库
    generated_questions = []
    for result in generated_results:
        if result is None:
            continue
        
        try:
            # 生成唯一题目编号
            question_number = _generate_question_number(goal_id, db)
            
            # 验证题目内容不为空
            question_text = result.get('question', '')
            if not question_text or len(question_text.strip()) < 5:
                print(f"[生成题目] 题目内容为空或过短，跳过: node_id={result.get('node_id')}")
                continue
            
            question = QuestionBank(
                study_goal_id=goal_id,
                knowledge_point_id=result['node_id'],
                question_text=question_text,
                question_type="choice",
                difficulty=request.difficulty,
                options=result['options'],
                correct_answer=result['answer'],
                explanation=result['explanation'],
                is_ai_generated=True,
                question_number=question_number
            )
            db.add(question)
            db.flush()
            
            generated_questions.append({
                "id": question.id,
                "question_text": question.question_text,
                "difficulty": question.difficulty,
                "knowledge_point_id": question.knowledge_point_id,
                "knowledge_point_name": result['node_name'],
                "question_number": question_number
            })
        except Exception as e:
            print(f"[生成题目] 保存失败: {e}")
            continue
    
    print(f"[生成题目] 最终保存数量: {len(generated_questions)}/{len(target_nodes)}")
    db.commit()
    
    if not generated_questions:
        raise HTTPException(status_code=500, detail="题目生成失败，请稍后重试")
    
    return Response(
        success=True,
        message=f"成功生成 {len(generated_questions)} 道题目",
        data={
            "generated_count": len(generated_questions),
            "questions": generated_questions
        }
    )


# ============ 习题生成 SSE 流式接口 ============

# 取消生成状态管理
_generation_cancelled = False


def _cancel_generation():
    """取消生成"""
    global _generation_cancelled
    _generation_cancelled = True
    # 同时通知 cancel_manager，以便中断正在进行的 Ollama 请求
    from app.services.cancel_manager import request_cancel
    request_cancel()
    print("[生成题目] 收到取消请求")


@router.post("/{goal_id}/generate/stream")
async def generate_questions_stream(
    goal_id: int,
    request: GenerateQuestionsRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    AI生成习题 - SSE流式版本（带进度返回）
    
    ## 参数
    - node_id: 单个知识点ID（兼容旧接口，与node_ids互斥）
    - node_ids: 多个知识点ID列表（批量生成时使用）
    - count: 每个知识点生成的题目数量
    - difficulty: 难度 (basic/comprehensive/challenge)
    - batch_mode: 是否为批量模式（为每个知识点生成count道题目）
    
    ## 生成策略
    - 不同知识点：并行生成（并发数5）
    - 相同知识点：串行生成（保证不重复）
    - Ollama模型：全部串行（本地算力有限）
    """
    import random
    import asyncio
    from fastapi.responses import StreamingResponse
    
    global _generation_cancelled
    _generation_cancelled = False
    # 同时重置 cancel_manager 中的取消状态，确保新请求不受上次取消的影响
    from app.services.cancel_manager import reset_cancel
    reset_cancel()
    
    async def generate_stream():
        from app.services.cancel_manager import GenerationCancelledError
        try:
            # 发送开始状态
            yield f"data: {json.dumps({'type': 'status', 'status': 'starting', 'message': '正在准备生成任务...', 'progress': 0}, ensure_ascii=False)}\n\n"
            
            # 验证学习目标
            goal = db.query(StudyGoal).filter(
                StudyGoal.id == goal_id,
                StudyGoal.student_id == current_student_id
            ).first()
            
            if not goal:
                yield f"data: {json.dumps({'type': 'error', 'message': '学习目标不存在'}, ensure_ascii=False)}\n\n"
                return
            
            # 获取知识图谱
            graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
            nodes = _parse_nodes(graph.nodes if graph else None)
            
            if not nodes:
                yield f"data: {json.dumps({'type': 'error', 'message': '该学习目标没有知识图谱，请先创建知识图谱'}, ensure_ascii=False)}\n\n"
                return
            
            # 构建节点映射表
            node_map = {n.get('id'): n for n in nodes if n.get('id')}
            
            # 确定要生成题目的知识点列表
            target_nodes = []
            
            if request.node_ids and len(request.node_ids) > 0:
                for node_id in request.node_ids:
                    if node_id in node_map:
                        target_nodes.extend([node_map[node_id]] * request.count)
            elif request.node_id:
                if request.node_id in node_map:
                    target_nodes = [node_map[request.node_id]] * request.count
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': '指定的知识点不存在'}, ensure_ascii=False)}\n\n"
                    return
            else:
                random.seed()
                candidate_nodes = list(node_map.values())
                if request.batch_mode:
                    for node in candidate_nodes:
                        target_nodes.extend([node] * request.count)
                else:
                    target_nodes = [random.choice(candidate_nodes) for _ in range(request.count)]
            
            if not target_nodes:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有有效的知识点用于生成题目'}, ensure_ascii=False)}\n\n"
                return
            
            # 为每个节点添加 goal_id
            for node in target_nodes:
                node['goal_id'] = goal_id
            
            total_nodes = len(target_nodes)
            
            # 检查是否为 Ollama 模型
            ai_provider = _get_ai_provider()
            is_ollama = ai_provider.is_ollama()
            print(f"[SSE生成] AI模型类型: {'Ollama (串行)' if is_ollama else 'API服务 (并行)'}")
            
            # 按知识点分组
            node_groups = _group_nodes_by_knowledge_point(target_nodes)
            
            # 发送准备完成状态
            yield f"data: {json.dumps({'type': 'status', 'status': 'preparing', 'message': f'准备生成 {total_nodes} 道题目', 'progress': 5}, ensure_ascii=False)}\n\n"
            
            # 生成题目
            generated_questions = []
            generated_count = 0
            
            if is_ollama:
                # Ollama 模型：完全串行生成（避免并发导致超时）
                print(f"[SSE生成] 使用 Ollama 完全串行策略")
                
                for idx, (node, count) in enumerate(node_groups):
                    # 检查是否被取消
                    if _generation_cancelled:
                        yield f"data: {json.dumps({'type': 'cancelled', 'message': '用户取消了生成', 'progress': int((idx / len(node_groups)) * 100)}, ensure_ascii=False)}\n\n"
                        break
                    
                    node_name = node.get('label', node.get('name', ''))
                    node_copy = node.copy()
                    node_copy['goal_id'] = goal_id
                    node_group = [node_copy] * count
                    
                    # 发送该知识点开始状态
                    yield f"data: {json.dumps({
                        'type': 'progress',
                        'status': 'generating',
                        'message': f'正在生成知识点 "{node_name}" 的 {count} 道题目',
                        'progress': int((idx / len(node_groups)) * 100),
                        'current_node': node_name,
                        'current_index': generated_count + 1,
                        'total': total_nodes
                    }, ensure_ascii=False)}\n\n"
                    
                    # 串行生成
                    results = await _generate_questions_by_node_group(
                        node_group=node_group,
                        difficulty=request.difficulty,
                        goal_title=goal.title,
                        max_retries=3,
                        goal_description=goal.description,
                        section_title=None
                    )

                    # 保存每道题目
                    for result in results:
                        if result is None:
                            continue
                        
                        question_number = _generate_question_number(goal_id, db)
                        question = QuestionBank(
                            study_goal_id=goal_id,
                            knowledge_point_id=result['node_id'],
                            question_text=result['question'],
                            question_type="choice",
                            difficulty=request.difficulty,
                            options=result['options'],
                            correct_answer=result['answer'],
                            explanation=result['explanation'],
                            is_ai_generated=True,
                            created_at=datetime.now()
                        )
                        db.add(question)
                        generated_questions.append({
                            **result,
                            'question_number': question_number,
                            'node_name': result.get('node_name', '')
                        })
                        generated_count += 1
                        
                        # 发送单题完成消息
                        yield f"data: {json.dumps({
                            'type': 'question_complete',
                            'message': f'已完成 {generated_count}/{total_nodes} 道题目',
                            'progress': int((generated_count / total_nodes) * 100),
                            'current_node': result.get('node_name', ''),
                            'current_index': generated_count,
                            'total': total_nodes
                        }, ensure_ascii=False)}\n\n"
                
                # 提交数据库
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"[SSE生成] 保存题目失败: {e}")
                
                # 发送完成状态
                yield f"data: {json.dumps({
                    'type': 'complete',
                    'message': f'生成完成！共生成 {generated_count} 道题目',
                    'progress': 100,
                    'total': generated_count,
                    'questions': generated_questions
                }, ensure_ascii=False)}\n\n"
            else:
                # 非 Ollama 模型：并行生成（不同知识点并行，同知识点串行）
                print(f"[SSE生成] 使用并行策略，并发数=5")
                
                # 使用信号量控制并发数
                semaphore = asyncio.Semaphore(5)
                lock = asyncio.Lock()
                
                async def generate_node_group_task(node: dict, count: int):
                    """单个知识点组的生成任务"""
                    async with semaphore:
                        node_name = node.get('label', node.get('name', ''))
                        node_group = [node] * count
                        node_group[0]['goal_id'] = goal_id
                        
                        results = await _generate_questions_by_node_group(
                            node_group=node_group,
                            difficulty=request.difficulty,
                            goal_title=goal.title,
                            max_retries=3,
                            goal_description=goal.description,
                            section_title=None
                        )

                        # 收集生成的消息
                        messages = []
                        
                        for result in results:
                            if result is None:
                                continue
                            
                            question_number = _generate_question_number(goal_id, db)
                            question = QuestionBank(
                                study_goal_id=goal_id,
                                knowledge_point_id=result['node_id'],
                                question_text=result['question'],
                                question_type="choice",
                                difficulty=request.difficulty,
                                options=result['options'],
                                correct_answer=result['answer'],
                                explanation=result['explanation'],
                                is_ai_generated=True,
                                question_number=question_number
                            )
                            db.add(question)
                            db.flush()
                            
                            generated_questions.append({
                                "id": question.id,
                                "question_text": question.question_text,
                                "difficulty": question.difficulty,
                                "knowledge_point_id": question.knowledge_point_id,
                                "knowledge_point_name": result['node_name'],
                                "question_number": question_number
                            })
                            
                            # 发送单题生成完成
                            messages.append(f"data: {json.dumps({
                                'type': 'question_complete',
                                'question': generated_questions[-1],
                                'progress': 0,
                                'generated_count': len(generated_questions),
                                'total': total_nodes
                            }, ensure_ascii=False)}\n\n")
                        
                        return messages
                
                # 并行执行所有任务
                tasks = [generate_node_group_task(node, count) for node, count in node_groups]
                results_list = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for task_result in results_list:
                    if isinstance(task_result, Exception):
                        print(f"[SSE生成] 任务异常: {task_result}")
                        continue
                    for msg in task_result:
                        yield msg
            
            db.commit()
            
            # 发送完成状态
            yield f"data: {json.dumps({
                'type': 'complete',
                'status': 'completed',
                'message': f'成功生成 {len(generated_questions)} 道题目',
                'progress': 100,
                'generated_count': len(generated_questions),
                'questions': generated_questions
            }, ensure_ascii=False)}\n\n"
            
        except GenerationCancelledError:
            # 用户取消：发送取消状态
            yield f"data: {json.dumps({
                'type': 'cancelled',
                'status': 'cancelled',
                'message': '用户取消了生成',
                'progress': 0
            }, ensure_ascii=False)}\n\n"
        except Exception as e:
            print(f"[生成题目] SSE生成异常: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/cancel-generation")
async def cancel_question_generation():
    """
    取消习题生成
    """
    _cancel_generation()
    return Response(
        success=True,
        message="取消请求已发送",
        data={"cancelled": True}
    )


@router.post("/{goal_id}/submit", response_model=Response)
async def submit_answer(
    goal_id: int,
    question_id: int,
    answer: str,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    提交答案
    
    ## 参数
    - question_id: 题目ID
    - answer: 学生答案
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    question = db.query(QuestionBank).filter(
        QuestionBank.id == question_id,
        QuestionBank.study_goal_id == goal_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 判断对错
    is_correct = answer.strip().upper() == question.correct_answer.strip().upper()
    
    # 更新知识点掌握度
    if question.knowledge_point_id:
        mastery = db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == current_student_id,
            NodeMastery.node_id == question.knowledge_point_id
        ).first()
        
        if mastery:
            mastery.total_attempts += 1
            if is_correct:
                mastery.correct_attempts += 1
            # 更新掌握度
            accuracy = mastery.correct_attempts / mastery.total_attempts
            mastery.mastery_level = min(100, accuracy * 100)
            mastery.updated_at = datetime.utcnow()
        else:
            # 创建新的掌握度记录
            mastery = NodeMastery(
                student_id=current_student_id,
                study_goal_id=goal_id,
                node_id=question.knowledge_point_id,
                node_name="",  # 可以从知识图谱获取
                mastery_level=100 if is_correct else 0,
                total_attempts=1,
                correct_attempts=1 if is_correct else 0
            )
            db.add(mastery)
    
    db.commit()
    
    # 处理解析：如果为空，生成默认解析
    explanation = question.explanation
    if not explanation or not explanation.strip():
        # 生成默认解析
        options_text = ""
        if question.options:
            if isinstance(question.options, str):
                options_text = question.options
            elif isinstance(question.options, list):
                options_text = "\n".join([str(opt) for opt in question.options])
        explanation = f"本题考察{question.question_text[:20]}...相关知识点。正确答案是{question.correct_answer}。"
    
    return Response(
        success=True,
        message="提交成功",
        data={
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "explanation": explanation,
            "knowledge_point_id": question.knowledge_point_id
        }
    )


@router.get("/{goal_id}/practice", response_model=Response)
async def get_practice_questions(
    goal_id: int,
    count: int = 10,
    focus_weak_points: bool = True,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取练习题（智能推荐）
    
    ## 参数
    - count: 题目数量
    - focus_weak_points: 是否优先推荐薄弱知识点
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    if focus_weak_points:
        # 获取薄弱知识点
        weak_masteries = db.query(NodeMastery).filter(
            NodeMastery.study_goal_id == goal_id,
            NodeMastery.student_id == current_student_id,
            NodeMastery.mastery_level < 60
        ).all()
        
        weak_node_ids = [m.node_id for m in weak_masteries]
        
        if weak_node_ids:
            # 从薄弱知识点出题
            questions = db.query(QuestionBank).filter(
                QuestionBank.study_goal_id == goal_id,
                QuestionBank.knowledge_point_id.in_(weak_node_ids)
            ).limit(count).all()
        else:
            # 没有薄弱点则随机出题
            questions = db.query(QuestionBank).filter(
                QuestionBank.study_goal_id == goal_id
            ).limit(count).all()
    else:
        questions = db.query(QuestionBank).filter(
            QuestionBank.study_goal_id == goal_id
        ).limit(count).all()
    
    return Response(
        success=True,
        message="获取成功",
        data={
            "count": len(questions),
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "options": q.options,
                    "knowledge_point_id": q.knowledge_point_id
                }
                for q in questions
            ]
        }
    )


@router.get("/{goal_id}/personalized-practice", response_model=Response)
async def get_personalized_practice(
    goal_id: int,
    count: int = 10,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取个性化练习推荐
    
    根据学生当前的知识掌握水平，从题库中推荐适合的习题。
    优先推荐薄弱知识点的题目，并根据掌握度自动匹配难度。
    
    ## 参数
    - goal_id: 学习目标ID
    - count: 题目数量，只允许 5 或 10
    
    ## 返回
    - exercise_id: 练习会话ID
    - exercises: 推荐的题目列表
    - total: 实际返回数量
    - recommendation_summary: 推荐摘要信息
    """
    # 参数校验：count 只允许 5 或 10
    if count not in [5, 10]:
        return Response(
            success=False,
            message="题目数量只支持 5 或 10",
            data=None
        )
    
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 1. 查询该学生该目标下所有 NodeMastery 记录
    masteries = db.query(NodeMastery).filter(
        NodeMastery.student_id == current_student_id,
        NodeMastery.study_goal_id == goal_id
    ).order_by(NodeMastery.mastery_level.asc()).all()
    
    # 2. 构建知识点名称映射（优先从 KnowledgeNode 表获取，其次从 KnowledgeGraph 获取）
    node_name_map = {}
    
    # 方法1: 从 KnowledgeNode 表获取
    knowledge_nodes = db.query(KnowledgeNode).join(
        KnowledgeGraph, KnowledgeNode.graph_id == KnowledgeGraph.id
    ).filter(
        KnowledgeGraph.study_goal_id == goal_id
    ).all()
    
    for kn in knowledge_nodes:
        node_name_map[kn.node_id] = kn.name
    
    # 方法2: 从 KnowledgeGraph 的 nodes JSON 获取（补充）
    kg = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    if kg:
        nodes = _parse_nodes(kg.nodes)
        for node in nodes:
            node_id = str(node.get('id', ''))
            if node_id not in node_name_map:
                node_name_map[node_id] = node.get('label', '') or node.get('name', '') or node_id
    
    # 3. 按掌握度升序排列，优先推荐薄弱知识点
    mastery_list = []
    for m in masteries:
        total = m.total_attempts or 0
        correct = m.correct_attempts or 0
        correct_rate = round(correct / total * 100, 1) if total > 0 else 0
        mastery_list.append({
            "node_id": m.node_id,
            "node_name": node_name_map.get(m.node_id, m.node_id),
            "mastery_level": m.mastery_level or 0,
            "correct_rate": correct_rate,
            "total_attempts": total
        })
    
    # 如果没有任何掌握度记录，尝试从知识图谱获取所有知识点
    if not mastery_list:
        if kg:
            nodes = _parse_nodes(kg.nodes)
            for node in nodes:
                node_id = str(node.get('id', ''))
                mastery_list.append({
                    "node_id": node_id,
                    "node_name": node_name_map.get(node_id, node_id),
                    "mastery_level": 0,
                    "correct_rate": 0,
                    "total_attempts": 0
                })
    
    # 4. 为每个知识点确定推荐难度并筛选题目
    selected_questions = []
    question_ids_used = set()
    weak_points_count = 0
    
    # 难度降级顺序
    difficulty_fallback = {
        "challenge": ["challenge", "comprehensive", "basic"],
        "comprehensive": ["comprehensive", "basic", "challenge"],
        "basic": ["basic", "comprehensive", "challenge"]
    }
    
    for m in mastery_list:
        if len(selected_questions) >= count:
            break
            
        node_id = m["node_id"]
        mastery_level = m["mastery_level"]
        total_attempts = m["total_attempts"]
        
        # 统计薄弱知识点数量（掌握度 < 60）
        if mastery_level < 60:
            weak_points_count += 1
        
        # 确定推荐难度
        target_difficulty = _determine_difficulty(mastery_level, total_attempts)
        
        # 按难度降级策略查找题目
        found_question = None
        for diff in difficulty_fallback.get(target_difficulty, ["basic", "comprehensive", "challenge"]):
            q = db.query(QuestionBank).filter(
                QuestionBank.study_goal_id == goal_id,
                QuestionBank.knowledge_point_id == str(node_id),
                QuestionBank.difficulty == diff,
                ~QuestionBank.id.in_(question_ids_used) if question_ids_used else True
            ).first()
            
            if q:
                found_question = q
                break
        
        if found_question:
            selected_questions.append({
                "id": found_question.id,
                "question_text": found_question.question_text,
                "question_type": found_question.question_type,
                "difficulty": found_question.difficulty,
                "target_difficulty": target_difficulty,
                "options": found_question.options,
                "correct_answer": found_question.correct_answer,
                "explanation": found_question.explanation,
                "knowledge_point_id": found_question.knowledge_point_id,
                "mastery_info": {
                    "node_id": node_id,
                    "node_name": node_name_map.get(node_id, node_id),
                    "mastery_level": mastery_level,
                    "correct_rate": m["correct_rate"],
                    "total_attempts": total_attempts
                }
            })
            question_ids_used.add(found_question.id)
    
    # 5. 如果薄弱知识点不够，扩展到所有知识点（已经在上面的循环中处理）
    # 6. 如果整个题库题目不足 count 数，返回所有可用题目
    
    # 7. 打乱题目顺序
    random.shuffle(selected_questions)
    
    # 生成练习会话ID
    exercise_id = f"personalized_{goal_id}_{int(datetime.utcnow().timestamp())}"
    
    # 统计覆盖的知识点数
    covered_kp_count = len(set(q["knowledge_point_id"] for q in selected_questions))
    
    return Response(
        success=True,
        message=f"已推荐 {len(selected_questions)} 道练习题",
        data={
            "exercise_id": exercise_id,
            "exercises": selected_questions,
            "total": len(selected_questions),
            "recommendation_summary": {
                "weak_points_count": weak_points_count,
                "covered_knowledge_points": covered_kp_count
            }
        }
    )


@router.get("/{goal_id}/wrong-questions", response_model=Response)
async def get_wrong_questions(
    goal_id: int,
    limit: int = 50,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取错题本

    返回指定学习目标下学生的所有错题记录
    """
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()

    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")

    # 获取该学生的所有 Assessment（通过 LearningPlan → StudyGoal 关联）
    assessments = db.query(Assessment).join(
        Lesson, Assessment.lesson_id == Lesson.id
    ).join(
        LearningPlan, Lesson.plan_id == LearningPlan.id
    ).filter(
        LearningPlan.study_goal_id == goal_id,
        Assessment.student_id == current_student_id
    ).order_by(Assessment.created_at.desc()).limit(limit).all()

    # 提取错题
    wrong_questions_list = []
    for assessment in assessments:
        if assessment.wrong_questions:
            wrong_qs = json.loads(assessment.wrong_questions) if isinstance(assessment.wrong_questions, str) else assessment.wrong_questions
            for wq in wrong_qs:
                wq['assessment_id'] = assessment.id
                wq['submitted_at'] = assessment.created_at.isoformat() if assessment.created_at else None
                wq['score'] = assessment.score
                wrong_questions_list.append(wq)

    # 获取题目详情（关联 QuestionBank）
    for wq in wrong_questions_list:
        if wq.get('question_id'):
            question = db.query(QuestionBank).filter(
                QuestionBank.id == wq['question_id']
            ).first()
            if question:
                wq['knowledge_point_id'] = question.knowledge_point_id
                wq['difficulty'] = question.difficulty
                wq['explanation'] = question.explanation

    return Response(
        success=True,
        message="获取成功",
        data={
            "goal_id": goal_id,
            "goal_title": goal.title,
            "total_wrong": len(wrong_questions_list),
            "wrong_questions": wrong_questions_list
        }
    )


@router.get("/{goal_id}/answer-history", response_model=Response)
async def get_answer_history(
    goal_id: int,
    limit: int = 20,
    offset: int = 0,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    获取答题历史

    返回指定学习目标下学生的答题历史记录
    """
    # 验证学习目标
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()

    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")

    # 获取 Assessment 记录
    assessments = db.query(Assessment).join(
        Lesson, Assessment.lesson_id == Lesson.id
    ).join(
        LearningPlan, Lesson.plan_id == LearningPlan.id
    ).filter(
        LearningPlan.study_goal_id == goal_id,
        Assessment.student_id == current_student_id
    ).order_by(Assessment.created_at.desc()).offset(offset).limit(limit).all()

    # 格式化历史记录
    history = []
    for a in assessments:
        history.append({
            "assessment_id": a.id,
            "lesson_id": a.lesson_id,
            "lesson_title": a.lesson.title if a.lesson else "未知课时",
            "score": a.score,
            "total_questions": a.total_questions,
            "correct_answers": a.correct_answers,
            "submitted_at": a.created_at.isoformat() if a.created_at else None,
            "time_spent": a.time_spent
        })

    return Response(
        success=True,
        message="获取成功",
        data={
            "goal_id": goal_id,
            "goal_title": goal.title,
            "history": history
        }
    )


# 提交测试请求模型
class SubmitTestRequest(BaseModel):
    goal_id: int
    questions: List[dict]  # 题目列表
    answers: List[dict]   # 答案列表 [{"question_id": 1, "answer": "A"}]
    time_spent: int = 0   # 花费时间（秒）


def _update_node_mastery(db: Session, student_id: int, goal_id: int, wrong_question: dict):
    """更新知识点掌握度"""
    if not wrong_question.get("knowledge_point_id"):
        return

    mastery = db.query(NodeMastery).filter(
        NodeMastery.study_goal_id == goal_id,
        NodeMastery.student_id == student_id,
        NodeMastery.node_id == wrong_question["knowledge_point_id"]
    ).first()

    if mastery:
        mastery.total_attempts += 1
        mastery.correct_attempts = max(0, mastery.correct_attempts - 1)  # 错一题，正确数-1
        accuracy = mastery.correct_attempts / mastery.total_attempts if mastery.total_attempts > 0 else 0
        mastery.mastery_level = min(100, max(0, accuracy * 100))
    else:
        mastery = NodeMastery(
            student_id=student_id,
            study_goal_id=goal_id,
            node_id=wrong_question["knowledge_point_id"],
            node_name="",
            mastery_level=0,
            total_attempts=1,
            correct_attempts=0
        )
        db.add(mastery)


@router.post("/submit-test", response_model=Response)
async def submit_test_result(
    request: SubmitTestRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    提交测试结果（用于 Chat 中的测试）

    计算得分，记录错题，更新知识点掌握度
    """
    # 计算得分
    correct = 0
    wrong_list = []

    for idx, ans in enumerate(request.answers):
        q = request.questions[idx] if idx < len(request.questions) else {}
        user_answer = ans.get("answer", "").upper()
        correct_answer = q.get("answer", "").upper() if q else ""

        is_correct = user_answer == correct_answer

        if is_correct:
            correct += 1
        else:
            wrong_list.append({
                "question_id": q.get("id"),
                "question": q.get("question"),
                "user_answer": ans.get("answer"),
                "correct_answer": q.get("answer"),
                "knowledge_point_id": q.get("knowledge_point_id"),
                "difficulty": q.get("difficulty")
            })

    score = (correct / len(request.answers) * 100) if request.answers else 0

    # 查找关联的 Lesson（如果有）
    lesson_id = None
    if request.goal_id:
        plan = db.query(LearningPlan).filter(
            LearningPlan.study_goal_id == request.goal_id
        ).first()
        if plan:
            next_lesson = db.query(Lesson).filter(
                Lesson.plan_id == plan.id,
                Lesson.is_completed == False
            ).order_by(Lesson.lesson_number).first()
            if next_lesson:
                lesson_id = next_lesson.id

    # 创建 Assessment 记录
    assessment = Assessment(
        student_id=current_student_id,
        lesson_id=lesson_id or 1,
        assessment_type="practice",
        questions=json.dumps(request.questions, ensure_ascii=False),
        total_questions=len(request.questions),
        correct_answers=correct,
        score=score,
        time_spent=request.time_spent,
        wrong_questions=json.dumps(wrong_list, ensure_ascii=False)
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # 更新知识点掌握度
    for wq in wrong_list:
        if wq.get("knowledge_point_id"):
            _update_node_mastery(db, current_student_id, request.goal_id, wq)
    db.commit()

    # 更新学习目标进度
    if request.goal_id:
        goal = db.query(StudyGoal).filter(StudyGoal.id == request.goal_id).first()
        if goal:
            # 统计已掌握的知识点
            mastered = db.query(NodeMastery).filter(
                NodeMastery.study_goal_id == request.goal_id,
                NodeMastery.student_id == current_student_id,
                NodeMastery.mastery_level >= 60
            ).count()
            goal.mastered_points = mastered
            db.commit()

    return Response(
        success=True,
        message="提交成功",
        data={
            "score": score,
            "correct": correct,
            "total": len(request.answers),
            "wrong_count": len(wrong_list),
            "assessment_id": assessment.id
        }
    )


@router.delete("/{goal_id}/{question_id}", response_model=Response)
async def delete_question(
    goal_id: int,
    question_id: int,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    删除习题
    
    ## 参数
    - goal_id: 学习目标ID
    - question_id: 题目ID
    """
    # 验证学习目标存在
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 查找题目
    question = db.query(QuestionBank).filter(
        QuestionBank.id == question_id,
        QuestionBank.study_goal_id == goal_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 删除题目
    db.delete(question)
    db.commit()
    
    return Response(
        success=True,
        message="题目删除成功",
        data={"deleted_id": question_id}
    )


@router.get("/{goal_id}/export", response_model=Response)
async def export_questions(
    goal_id: int,
    format: str = "json",  # json, csv, word
    difficulty: Optional[str] = None,
    knowledge_point_ids: Optional[str] = None,
    is_ai_generated: Optional[bool] = None,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    导出习题
    
    ## 参数
    - format: 导出格式 (json/csv/word)
    - difficulty: 难度筛选
    - knowledge_point_ids: 知识点ID筛选（逗号分隔）
    - is_ai_generated: 是否AI生成筛选
    """
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 构建查询
    query = db.query(QuestionBank).filter(QuestionBank.study_goal_id == goal_id)
    
    if difficulty:
        query = query.filter(QuestionBank.difficulty == difficulty)
    if knowledge_point_ids:
        ids = [id.strip() for id in knowledge_point_ids.split(',') if id.strip()]
        if ids:
            query = query.filter(QuestionBank.knowledge_point_id.in_(ids))
    if is_ai_generated is not None:
        query = query.filter(QuestionBank.is_ai_generated == is_ai_generated)
    
    questions = query.all()
    
    # 获取知识图谱以查找知识点名称
    graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    nodes = _parse_nodes(graph.nodes if graph else None)
    node_name_map = {}
    for node in nodes:
        node_name_map[node.get('id')] = node.get('label', node.get('name', '未知知识点'))
    
    # 准备导出数据
    export_data = []
    for q in questions:
        export_data.append({
            "编号": q.question_number or f"Q-{q.id}",
            "题目": q.question_text,
            "题型": "选择题" if q.question_type == "choice" else q.question_type,
            "难度": {
                'basic': '基础题',
                'comprehensive': '综合题',
                'challenge': '挑战题'
            }.get(q.difficulty, q.difficulty),
            "知识点": node_name_map.get(q.knowledge_point_id, '未知知识点'),
            "选项": "\n".join(q.options) if q.options else "",
            "正确答案": q.correct_answer,
            "解析": q.explanation or "",
            "来源": "AI生成" if q.is_ai_generated else "用户上传",
            "创建时间": q.created_at.strftime('%Y-%m-%d %H:%M') if q.created_at else ""
        })
    
    if format == "json":
        return Response(
            success=True,
            message="导出成功",
            data={
                "format": "json",
                "count": len(export_data),
                "questions": export_data
            }
        )
    
    elif format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
        
        return Response(
            success=True,
            message="导出成功",
            data={
                "format": "csv",
                "count": len(export_data),
                "content": output.getvalue()
            }
        )
    
    elif format == "word":
        # 返回结构化数据，前端可进一步处理为Word
        return Response(
            success=True,
            message="导出成功",
            data={
                "format": "word",
                "count": len(export_data),
                "questions": export_data,
                "title": f"{goal.title} - 习题库"
            }
        )
    
    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式")


# ============ 习题上传相关 API ============

@router.post("/{goal_id}/upload", response_model=Response)
async def upload_question(
    goal_id: int,
    request: CreateQuestionRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    结构化上传单道习题
    
    ## 参数
    - question_text: 题干内容
    - question_type: 题型 (choice/fill_blank/short_answer)
    - difficulty: 难度 (basic/comprehensive/challenge)
    - knowledge_point_id: 关联知识点ID（可选）
    - options: 选项列表 [{"key": "A", "text": "选项内容"}]
    - correct_answer: 正确答案
    - explanation: 答案解析（可选）
    """
    # 验证学习目标存在
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 验证知识点是否存在（如果提供了）
    if request.knowledge_point_id:
        graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
        nodes = _parse_nodes(graph.nodes if graph else None)
        node_ids = [n.get('id') for n in nodes if n.get('id')]
        if request.knowledge_point_id not in node_ids:
            raise HTTPException(status_code=400, detail="指定的知识点不存在")
    
    # 生成题目编号
    question_number = _generate_question_number(goal_id, db)
    
    # 格式化选项
    formatted_options = [f"{opt.key}. {opt.text}" for opt in request.options]
    
    # 创建题目
    question = QuestionBank(
        study_goal_id=goal_id,
        knowledge_point_id=request.knowledge_point_id,
        question_text=request.question_text,
        question_type=request.question_type,
        difficulty=request.difficulty,
        options=formatted_options,
        correct_answer=request.correct_answer,
        explanation=request.explanation,
        is_ai_generated=False,  # 用户上传
        question_number=question_number
    )
    
    db.add(question)
    db.commit()
    db.refresh(question)
    
    return Response(
        success=True,
        message="题目上传成功",
        data={
            "id": question.id,
            "question_number": question_number,
            "question_text": question.question_text,
            "difficulty": question.difficulty,
            "knowledge_point_id": question.knowledge_point_id
        }
    )


@router.post("/{goal_id}/upload/batch", response_model=Response)
async def batch_upload_questions(
    goal_id: int,
    request: BatchCreateQuestionsRequest,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    批量结构化上传习题
    
    ## 参数
    - questions: 题目列表，每道题包含结构化信息
    """
    # 验证学习目标存在
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取知识图谱节点
    graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    nodes = _parse_nodes(graph.nodes if graph else None)
    node_ids = [n.get('id') for n in nodes if n.get('id')]
    
    # 批量创建题目
    created_questions = []
    failed_questions = []
    
    for idx, q_request in enumerate(request.questions):
        try:
            # 验证知识点（如果提供了）
            if q_request.knowledge_point_id and q_request.knowledge_point_id not in node_ids:
                failed_questions.append({
                    "index": idx,
                    "reason": "知识点不存在"
                })
                continue
            
            # 生成题目编号
            question_number = _generate_question_number(goal_id, db)
            
            # 格式化选项
            formatted_options = [f"{opt.key}. {opt.text}" for opt in q_request.options]
            
            # 创建题目
            question = QuestionBank(
                study_goal_id=goal_id,
                knowledge_point_id=q_request.knowledge_point_id,
                question_text=q_request.question_text,
                question_type=q_request.question_type,
                difficulty=q_request.difficulty,
                options=formatted_options,
                correct_answer=q_request.correct_answer,
                explanation=q_request.explanation,
                is_ai_generated=False,
                question_number=question_number
            )
            
            db.add(question)
            created_questions.append({
                "index": idx,
                "question_number": question_number,
                "question_text": q_request.question_text[:50] + "..." if len(q_request.question_text) > 50 else q_request.question_text
            })
            
        except Exception as e:
            failed_questions.append({
                "index": idx,
                "reason": str(e)
            })
    
    db.commit()
    
    return Response(
        success=True,
        message=f"成功上传 {len(created_questions)} 道题目，失败 {len(failed_questions)} 道",
        data={
            "created_count": len(created_questions),
            "failed_count": len(failed_questions),
            "created_questions": created_questions,
            "failed_questions": failed_questions
        }
    )


async def _parse_questions_with_ai(file_content: str, file_type: str, goal_title: str = "") -> dict:
    """
    使用AI解析文件中的习题
    
    Args:
        file_content: 文件内容文本
        file_type: 文件类型 (txt/doc/docx/pdf)
        goal_title: 学习目标标题（用于上下文）
    
    Returns:
        解析结果，包含题目列表
    """
    system_prompt = f"""你是一位专业的教育内容解析与改编专家。你的任务是从文件中提取习题，并将所有题型**统一改编为单项选择题**。

【学习目标背景】
{goal_title if goal_title else "通用学习目标"}

【核心任务 - 必须遵守】
1. **识别文件中的所有习题**（选择题、填空题、简答题、判断题、计算题等）
2. **将所有题型改编为单项选择题**：
   - 如果原文是选择题：保持题干和选项结构，确保有4个选项(A/B/C/D)
   - 如果原文是填空题：将填空内容改编为4个选项，题干改为提问形式
   - 如果原文是简答题/问答题：根据答案内容，设计4个选项，让正确答案成为其中之一
   - 如果原文是判断题：将判断内容改编为4个选项（正确/错误/部分正确/无法确定等变体）
   - 如果原文是计算题：将计算结果和常见错误答案作为4个选项

【改编规则】
1. **选项设计原则**：
   - 必须生成4个选项(A/B/C/D)
   - 正确答案必须明确对应其中一个选项
   - 干扰项要似是而非，具有迷惑性但明显错误
   - 选项长度尽量保持一致

2. **题干改编原则**：
   - 保持原题的核心知识点和考察意图
   - 将开放式问题改为选择形式
   - 确保题干清晰、完整、无歧义

3. **难度保持**：
   - 保持原题的难度层次(basic/comprehensive/challenge)
   - 基础题：直接考察概念记忆
   - 综合题：需要理解、分析或简单计算
   - 挑战题：需要深入思考、综合应用

【输出格式】
请以JSON格式返回，所有题目必须是choice类型：
{{
  "questions": [
    {{
      "question_text": "改编后的题干内容（必须是选择形式）",
      "question_type": "choice",
      "difficulty": "basic",  // basic/comprehensive/challenge
      "options": [
        {{"key": "A", "text": "选项A内容"}},
        {{"key": "B", "text": "选项B内容"}},
        {{"key": "C", "text": "选项C内容"}},
        {{"key": "D", "text": "选项D内容"}}
      ],
      "correct_answer": "A",  // 必须是A/B/C/D之一
      "explanation": "答案解析：说明为什么选这个答案，以及其他选项为什么错误"
    }}
  ],
  "total_count": 解析出的题目数量,
  "parsing_status": "success",  // success/partial/failed
  "message": "解析说明，包括改编的题目数量和类型分布"
}}

【示例改编】
原文（填空题）："Python中用于定义函数的关键字是______。"
改编后：
{{
  "question_text": "Python中用于定义函数的关键字是什么？",
  "question_type": "choice",
  "difficulty": "basic",
  "options": [
    {{"key": "A", "text": "def"}},
    {{"key": "B", "text": "function"}},
    {{"key": "C", "text": "define"}},
    {{"key": "D", "text": "func"}}
  ],
  "correct_answer": "A",
  "explanation": "在Python中，使用def关键字定义函数。B选项function是JavaScript的用法，C和D都不是Python的关键字。"
}}

原文（简答题）："请简述深度学习中梯度消失问题的原因。"
改编后：
{{
  "question_text": "深度学习中梯度消失问题的主要原因是什么？",
  "question_type": "choice",
  "difficulty": "comprehensive",
  "options": [
    {{"key": "A", "text": "激活函数导数小于1，多层连乘后梯度指数级减小"}},
    {{"key": "B", "text": "学习率设置过大导致无法收敛"}},
    {{"key": "C", "text": "训练数据量不足导致模型欠拟合"}},
    {{"key": "D", "text": "网络层数太少导致表达能力不足"}}
  ],
  "correct_answer": "A",
  "explanation": "梯度消失主要是因为使用sigmoid等激活函数时，其导数最大值为0.25，多层连乘后梯度会指数级减小。B是学习率问题，C是数据问题，D与梯度消失无关。"
}}

【注意事项】
1. **只返回JSON格式**，不要包含其他文字说明
2. **所有题目必须是choice类型**，禁止返回其他类型
3. 如果无法解析任何题目，返回空数组和failed状态
4. 尽可能准确地提取和改编题目信息
5. 确保每道题都有完整的4个选项和明确的正确答案"""

    user_prompt = f"""请解析以下文件内容，提取其中的习题：

【文件类型】{file_type}

【文件内容】
{file_content[:8000]}  // 限制长度避免超出token限制

请严格按照JSON格式返回解析结果。"""

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 每次调用都获取最新的 AI Provider，确保使用最新配置
        ai_provider = _get_ai_provider()
        response = await ai_provider.chat(messages, temperature=0.3)
        
        # 解析JSON响应
        cleaned_response = response.strip()
        if cleaned_response.startswith('```'):
            lines = cleaned_response.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned_response = '\n'.join(lines)
        
        result = json.loads(cleaned_response)
        
        # 验证结果格式
        if 'questions' not in result:
            result['questions'] = []
        if 'total_count' not in result:
            result['total_count'] = len(result.get('questions', []))
        if 'parsing_status' not in result:
            result['parsing_status'] = 'success' if result['total_count'] > 0 else 'failed'
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"[AI解析] JSON解析失败: {e}")
        return {
            "questions": [],
            "total_count": 0,
            "parsing_status": "failed",
            "message": f"解析失败：无法识别题目格式 - {str(e)}"
        }
    except Exception as e:
        print(f"[AI解析] 调用失败: {e}")
        return {
            "questions": [],
            "total_count": 0,
            "parsing_status": "failed",
            "message": f"解析失败：{str(e)}"
        }


@router.post("/{goal_id}/upload/parse", response_model=Response)
async def parse_questions_from_file(
    goal_id: int,
    file: UploadFile = File(...),
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    上传文件并自动解析习题（调用大模型API）
    
    ## 参数
    - file: 上传的文件（支持 txt, doc, docx, pdf）
    
    ## 返回
    - 解析出的题目列表（预览模式，不保存到数据库）
    """
    # 验证学习目标存在
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 验证文件类型
    allowed_extensions = {'.txt', '.doc', '.docx', '.pdf'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{file_ext}，仅支持 {', '.join(allowed_extensions)}")
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 根据文件类型提取文本
        file_text = ""
        if file_ext == '.txt':
            # 尝试多种编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    file_text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
        elif file_ext in ['.doc', '.docx']:
            # 使用python-docx库解析Word文档
            try:
                from docx import Document
                import io
                doc = Document(io.BytesIO(content))
                file_text = '\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            except ImportError:
                raise HTTPException(status_code=500, detail="缺少docx解析库，请安装 python-docx")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Word文档解析失败: {str(e)}")
        elif file_ext == '.pdf':
            # 使用PyPDF2或pdfplumber解析PDF
            try:
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    file_text = '\n'.join([page.extract_text() or '' for page in pdf.pages])
            except ImportError:
                raise HTTPException(status_code=500, detail="缺少pdf解析库，请安装 pdfplumber")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"PDF解析失败: {str(e)}")
        
        if not file_text.strip():
            raise HTTPException(status_code=400, detail="无法从文件中提取文本内容")
        
        # 调用AI解析
        parse_result = await _parse_questions_with_ai(
            file_content=file_text,
            file_type=file_ext[1:],  # 去掉点号
            goal_title=goal.title
        )
        
        return Response(
            success=True,
            message=f"成功解析 {parse_result.get('total_count', 0)} 道题目",
            data={
                "filename": file.filename,
                "file_type": file_ext[1:],
                "questions": parse_result.get('questions', []),
                "total_count": parse_result.get('total_count', 0),
                "parsing_status": parse_result.get('parsing_status', 'failed'),
                "message": parse_result.get('message', '')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[文件解析] 错误: {e}")
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")


@router.post("/{goal_id}/upload/parse-confirm", response_model=Response)
async def confirm_parsed_questions(
    goal_id: int,
    request: ParseQuestionsResponse,
    current_student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db)
):
    """
    确认并保存解析出的习题
    
    ## 参数
    - questions: 解析出的题目列表（来自 /upload/parse 接口的返回）
    - 可选为每道题指定知识点ID
    """
    # 验证学习目标存在
    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.student_id == current_student_id
    ).first()
    
    if not goal:
        raise HTTPException(status_code=404, detail="学习目标不存在")
    
    # 获取知识图谱节点
    graph = db.query(KnowledgeGraph).filter(KnowledgeGraph.study_goal_id == goal_id).first()
    nodes = _parse_nodes(graph.nodes if graph else None)
    node_ids = [n.get('id') for n in nodes if n.get('id')]
    
    # 批量保存题目
    created_questions = []
    failed_questions = []
    
    for idx, q_data in enumerate(request.questions):
        try:
            # 验证知识点（如果提供了）
            kp_id = q_data.get('knowledge_point_id')
            if kp_id and kp_id not in node_ids:
                kp_id = None  # 知识点不存在则设为None
            
            # 生成题目编号
            question_number = _generate_question_number(goal_id, db)
            
            # 格式化选项
            options = q_data.get('options', [])
            if isinstance(options, list) and len(options) > 0:
                if isinstance(options[0], dict):
                    formatted_options = [f"{opt.get('key', '')}. {opt.get('text', '')}" for opt in options]
                else:
                    formatted_options = options
            else:
                formatted_options = []
            
            # 创建题目
            question = QuestionBank(
                study_goal_id=goal_id,
                knowledge_point_id=kp_id,
                question_text=q_data.get('question_text', ''),
                question_type=q_data.get('question_type', 'choice'),
                difficulty=q_data.get('difficulty', 'basic'),
                options=formatted_options,
                correct_answer=q_data.get('correct_answer', ''),
                explanation=q_data.get('explanation', ''),
                is_ai_generated=False,  # 虽然是AI解析，但来源是用户上传
                question_number=question_number
            )
            
            db.add(question)
            created_questions.append({
                "index": idx,
                "id": question.id,
                "question_number": question_number,
                "question_text": q_data.get('question_text', '')[:50] + "..."
            })
            
        except Exception as e:
            failed_questions.append({
                "index": idx,
                "reason": str(e)
            })
    
    db.commit()
    
    return Response(
        success=True,
        message=f"成功保存 {len(created_questions)} 道题目，失败 {len(failed_questions)} 道",
        data={
            "created_count": len(created_questions),
            "failed_count": len(failed_questions),
            "created_questions": created_questions,
            "failed_questions": failed_questions
        }
    )
