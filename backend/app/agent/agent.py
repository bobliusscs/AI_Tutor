"""
SimpleAgent - 支持Skill和MCP工具的对话Agent

核心设计:
- 用户与AI对话
- 基于 ReAct 范式的工具调用循环
- 支持OpenAI Function Calling
- 支持Skill工具和MCP工具
- 流式返回AI回复
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import AsyncGenerator, Optional

from .orchestrator import ToolOrchestrator

logger = logging.getLogger(__name__)


class SimpleAgent:
    """
    支持工具的对话Agent
    
    工作流程:
    1. 接收用户消息
    2. 加载学习上下文
    3. 构建消息列表(系统提示词+历史+当前消息+工具定义)
    4. ReAct循环:
       - 调用LLM(带工具定义)
       - 如果有工具调用,执行工具并添加结果到消息历史
       - 重复直到LLM不再调用工具
    5. 流式返回AI回复
    """

    def __init__(
        self,
        db=None,
        ai_provider=None,
        student_id: int = None,
    ):
        """
        Args:
            db: 数据库会话
            ai_provider: AI模型提供者
            student_id: 学生ID
        """
        self.db = db
        self.ai_provider = ai_provider
        self.student_id = student_id
        
        # 初始化工具编排器
        self.orchestrator = ToolOrchestrator(db, student_id)
        self.orchestrator.discover_and_load_skills()
        
        # 最大工具调用轮数(防止无限循环)
        self.max_tool_rounds = 5

    async def run(
        self,
        message: str,
        session_id: str = None,
        history: list = None,
        images: list = None,
        documents: list = None,
        current_goal: dict = None,
        cancel_event=None,
    ) -> AsyncGenerator[dict, None]:
        """
        主入口 - 支持工具调用的对话模式
        """
        try:
            # 通知开始思考
            yield {"status": "thinking", "status_message": "正在思考..."}

            # 加载学习上下文
            learning_context = self._load_learning_context(current_goal)

            # 构建消息列表
            messages = self._build_messages(message, history, learning_context)

            # 调试：打印完整消息和原始history
            logger.info(f"[Agent] 原始history数量: {len(history) if history else 0}")
            if history:
                for idx, h in enumerate(history):
                    logger.info(f"[Agent] history[{idx}] = {json.dumps(h, ensure_ascii=False)[:300]}")
            for idx, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                content_preview = str(content)[:200] if content else "(empty)"
                extra_keys = [k for k in msg.keys() if k not in ("role", "content")]
                logger.info(f"[Agent] 消息[{idx}] role={role}, content长度={len(str(content))}, 额外字段={extra_keys}, preview={content_preview}")
                # 如果有额外字段，打印其内容
                for k in extra_keys:
                    logger.info(f"[Agent]   额外字段 {k} = {json.dumps(msg[k], ensure_ascii=False)[:300] if isinstance(msg[k], (dict, list)) else msg[k]}")

            # 获取工具定义
            tools = self.orchestrator.get_all_tools()

            # ReAct循环 - 流式输出
            full_response = ""
            
            for round_idx in range(self.max_tool_rounds):
                # 检查取消
                if cancel_event and cancel_event.is_set():
                    yield {"type": "error", "message": "请求已取消"}
                    return
                
                # 流式调用LLM(带工具定义)
                tool_calls_detected = []
                round_content = ""
                
                async for event in self._call_llm_with_tools_stream(messages, tools, cancel_event):
                    if event["type"] == "content":
                        round_content += event["content"]
                        # 实时发送内容给前端
                        if event["content"]:
                            yield {"type": "chunk", "content": event["content"]}
                    elif event["type"] == "tool_calls":
                        tool_calls_detected = event["tool_calls"]
                
                # 检查是否有工具调用
                if tool_calls_detected:
                    logger.info(f"[Agent] 第{round_idx + 1}轮: 检测到 {len(tool_calls_detected)} 个工具调用")
                    # 注意：工具调用前的 content 可能是模型的预输出，会被正常发送
                    
                    # 通知正在调用工具
                    tool_names = [tc["function"]["name"] for tc in tool_calls_detected]
                    yield {
                        "status": "thinking", 
                        "status_message": f"正在调用工具: {', '.join(tool_names)}"
                    }
                    
                    # 执行所有工具调用
                    tool_results = []
                    for tool_call in tool_calls_detected:
                        tool_name = tool_call["function"]["name"]
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        logger.info(f"[Agent] 执行工具: {tool_name}")
                        result = await self.orchestrator.execute_tool(tool_name, arguments)
                        tool_results.append(result)
                        
                        # 将工具调用结果通过SSE发送给前端
                        yield {
                            "tool_call": tool_name,
                            "tool_result": result
                        }
                    
                    # 将工具调用和结果添加到消息历史
                    messages.append({
                        "role": "assistant",
                        "tool_calls": tool_calls_detected
                    })
                    
                    for i, result in enumerate(tool_results):
                        # 对于课件/习题工具，只提取关键信息发送给LLM，避免token超限
                        tool_result_for_llm = result
                        try:
                            result_data = json.loads(result) if isinstance(result, str) else result
                            if result_data.get("success") and "slides" in result_data:
                                slide_titles = [s.get("title", "") for s in result_data.get("slides", [])]
                                tool_result_for_llm = json.dumps({
                                    "success": True,
                                    "content_source": result_data.get("content_source", ""),
                                    "lesson_title": result_data.get("lesson_title", ""),
                                    "chapter_number": result_data.get("chapter_number"),
                                    "chapter_title": result_data.get("chapter_title", ""),
                                    "section_number": result_data.get("section_number"),
                                    "section_title": result_data.get("section_title", ""),
                                    "slide_count": result_data.get("slide_count", 0),
                                    "slide_titles": slide_titles,
                                    "is_completed": result_data.get("is_completed", False),
                                    "progress": result_data.get("progress", {}),
                                    "section_lessons": result_data.get("section_lessons", []),
                                    "note": "完整课件内容已发送给前端展示，请简要介绍课件主题并引导用户学习，不要重复课件正文"
                                }, ensure_ascii=False)
                            elif result_data.get("success") and "exercises" in result_data:
                                tool_result_for_llm = json.dumps({
                                    "success": True,
                                    "exercise_type": result_data.get("exercise_type", ""),
                                    "section_title": result_data.get("section_title", ""),
                                    "chapter_number": result_data.get("chapter_number"),
                                    "chapter_title": result_data.get("chapter_title", ""),
                                    "section_number": result_data.get("section_number"),
                                    "total": result_data.get("total", 0),
                                    "difficulty_stats": result_data.get("difficulty_stats", {}),
                                    "summary": result_data.get("summary", ""),
                                    "progress": result_data.get("progress", {}),
                                    "note": "完整习题数据已发送给前端展示，请简要说明题目数量和难度分布，鼓励学生完成练习，不要重复题目内容或泄露答案"
                                }, ensure_ascii=False)
                        except:
                            pass
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_calls_detected[i].get("id", ""),
                            "content": tool_result_for_llm
                        })
                    
                    # 继续下一轮
                    continue
                else:
                    # 无工具调用 → 最终回答（已经实时流式发送了）
                    full_response = round_content
                    break
            
            yield {"done": True, "full_response": full_response}

        except Exception as e:
            logger.error("Agent run error: %s", e, exc_info=True)
            yield {"error": str(e)}
            yield {"done": True, "full_response": f"处理时遇到问题:{str(e)}"}

    def _load_learning_context(self, current_goal: dict = None) -> dict:
        """加载学习上下文（包含用户信息和学习目标）"""
        context = {
            "student_info": None,
            "current_goal": None,
            "all_goals": [],
        }

        if not self.db or not self.student_id:
            return context

        try:
            from app.models.student import Student
            from app.models.study_goal import StudyGoal, StudyGoalStatus
            from app.models.learning_plan import LearningPlan

            # 1. 加载学生信息
            student = self.db.query(Student).filter(Student.id == self.student_id).first()
            if student:
                context["student_info"] = {
                    "id": student.id,
                    "username": student.username,
                    "nickname": student.nickname or student.username,
                    "grade": student.grade or "未设置",
                    "total_learning_time": student.total_learning_time or 0,
                    "study_streak": student.study_streak or 0,
                    "learning_style": student.learning_style or {},
                }

            # 2. 查询该学生的所有学习目标
            goals = self.db.query(StudyGoal).filter(
                StudyGoal.student_id == self.student_id,
                StudyGoal.status == StudyGoalStatus.ACTIVE.value
            ).order_by(StudyGoal.created_at.desc()).all()

            goals_info = []
            current_goal_id = current_goal.get("id") if current_goal else None

            for goal in goals:
                goal_info = {
                    "id": goal.id,
                    "title": goal.title,
                    "description": goal.description or "",
                    "completed_lessons": goal.completed_lessons,
                    "total_lessons": 0,
                    "progress_percent": 0,
                }
                
                if goal.total_knowledge_points > 0:
                    goal_info["progress_percent"] = round(
                        goal.mastered_points / goal.total_knowledge_points * 100, 1
                    )
                
                # 从学习计划获取课时进度
                plan = self.db.query(LearningPlan).filter(
                    LearningPlan.study_goal_id == goal.id,
                    LearningPlan.student_id == self.student_id
                ).first()
                if plan:
                    goal_info["total_lessons"] = plan.total_lessons or 0
                    goal_info["completed_lessons"] = plan.completed_lessons or 0
                    goal_info["plan_id"] = plan.id
                
                goals_info.append(goal_info)
                
                if goal.id == current_goal_id:
                    context["current_goal"] = goal_info

            if not context["current_goal"] and goals_info:
                context["current_goal"] = goals_info[0]

            context["all_goals"] = goals_info

        except Exception as e:
            logger.warning("加载学习上下文失败: %s", e)

        return context

    def _build_messages(self, message: str, history: list = None, learning_context: dict = None) -> list:
        """构建消息列表"""
        system_prompt = self._build_system_prompt(learning_context)
        
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史记录
        if history:
            for h in history:
                role = h.get("role", "user")
                content = h.get("content", "")
                
                if content is None:
                    content = ""
                if not isinstance(content, str):
                    content = str(content)
                
                # assistant消息带工具调用记录：重建OpenAI标准的tool_calls+tool消息序列
                if role == "assistant" and h.get("toolCalls") and len(h["toolCalls"]) > 0:
                    # 1. 添加带tool_calls的assistant消息
                    openai_tool_calls = []
                    tool_results = []
                    
                    for i, tc in enumerate(h["toolCalls"]):
                        tool_name = tc.get("toolName", "")
                        tool_result = tc.get("toolResult", "")
                        
                        # 生成稳定的tool_call_id
                        tool_call_id = tc.get("id") or f"call_hist_{i}_{tool_name}"
                        
                        # 从toolResult反推arguments（简化处理：提取关键参数）
                        arguments = self._reconstruct_tool_arguments(tool_name, tool_result)
                        
                        openai_tool_calls.append({
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": arguments
                            }
                        })
                        
                        # 精简tool result，避免token膨胀
                        result_summary = self._summarize_tool_result(tool_name, tool_result)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_summary
                        })
                    
                    # 工具调用消息：tool_calls + tool消息已足够让LLM知道之前调过工具
                    messages.append({
                        "role": "assistant",
                        "content": content.strip() if content.strip() else None,
                        "tool_calls": openai_tool_calls
                    })
                    
                    # tool消息
                    for tr in tool_results:
                        messages.append(tr)
                    
                    continue
                
                # 只允许 user 和 assistant 角色
                if role not in ("user", "assistant"):
                    continue
                
                # 跳过空内容的assistant消息（可能导致API错误）
                if role == "assistant" and not content.strip():
                    continue
                
                messages.append({"role": role, "content": content})

        # 添加当前消息
        messages.append({"role": "user", "content": message})

        return messages

    def _reconstruct_tool_arguments(self, tool_name: str, tool_result: str) -> str:
        """从工具结果反推调用参数（用于重建历史消息中的tool_calls）"""
        try:
            result_data = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
            args = {}
            if isinstance(result_data, dict):
                # 从结果中提取已知字段
                if result_data.get("goal_id"):
                    args["goal_id"] = result_data["goal_id"]
                if result_data.get("chapter_number") is not None:
                    args["chapter_number"] = result_data["chapter_number"]
                if result_data.get("section_number") is not None:
                    args["section_number"] = result_data["section_number"]
            return json.dumps(args, ensure_ascii=False) if args else "{}"
        except:
            return "{}"

    def _summarize_tool_result(self, tool_name: str, tool_result: str) -> str:
        """精简工具结果摘要（用于历史消息，避免token膨胀）"""
        try:
            result_data = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
            if not isinstance(result_data, dict):
                return str(tool_result)[:200]
            
            if result_data.get("success") and "slides" in result_data:
                # 课件工具：只保留摘要信息
                return json.dumps({
                    "success": True,
                    "lesson_title": result_data.get("lesson_title", ""),
                    "chapter_title": result_data.get("chapter_title", ""),
                    "section_title": result_data.get("section_title", ""),
                    "slide_count": result_data.get("slide_count", 0),
                    "is_completed": result_data.get("is_completed", False),
                    "progress": result_data.get("progress", {}),
                    "note": "课件已展示给用户"
                }, ensure_ascii=False)
            elif result_data.get("success") and "exercises" in result_data:
                # 习题工具：只保留统计信息
                return json.dumps({
                    "success": True,
                    "section_title": result_data.get("section_title", ""),
                    "total": result_data.get("total", 0),
                    "difficulty_stats": result_data.get("difficulty_stats", {}),
                    "note": "习题已展示给用户"
                }, ensure_ascii=False)
            else:
                # 其他工具：截断到200字符
                return str(tool_result)[:200]
        except:
            return str(tool_result)[:200]

    def _build_system_prompt(self, learning_context: dict = None) -> str:
        """构建系统提示词 - 从SYSTEM.md加载并替换动态部分"""
        try:
            # 读取SYSTEM.md模板
            system_md_path = Path(__file__).parent.parent / "prompts" / "bootstrap" / "SYSTEM.md"
            if system_md_path.exists():
                with open(system_md_path, "r", encoding="utf-8") as f:
                    template = f.read()
            else:
                # 兜底:使用默认模板
                template = self._get_fallback_template()
            
            # 1. 构建用户信息
            student_text = ""
            if learning_context and learning_context.get("student_info"):
                student = learning_context["student_info"]
                learning_style = student.get("learning_style", {})
                primary_style = learning_style.get("primary_style", "未设置")
                
                student_text = f"""
- 用户ID: {student['id']}
- 用户名: {student['nickname']}
- 年级: {student['grade']}
- 总学习时间: {student['total_learning_time']} 分钟
- 连续学习天数: {student['study_streak']} 天
- 学习风格: {primary_style}
"""
            else:
                student_text = "未登录用户"
            
            # 2. 构建学习目标文本
            goals_text = ""
            if learning_context and learning_context.get("all_goals"):
                goals_list = []
                for i, goal in enumerate(learning_context["all_goals"], 1):
                    progress_parts = []
                    # 课时进度（从学习计划获取，最直观）
                    total = goal.get("total_lessons", 0)
                    completed = goal.get("completed_lessons", 0)
                    if total > 0:
                        progress_parts.append(f"课时进度{completed}/{total}")
                    elif completed > 0:
                        progress_parts.append(f"已完成{completed}课时")
                    # 知识点掌握度
                    if goal.get("progress_percent", 0) > 0:
                        progress_parts.append(f"掌握度{goal['progress_percent']}%")
                    progress_str = "，".join(progress_parts) if progress_parts else "刚开始学习"
                    goals_list.append(f"{i}. [id={goal['id']}] {goal['title']}({progress_str})")
                goals_text = "\n".join(goals_list) if goals_list else "无"
            else:
                goals_text = "无"
            
            # 3. 替换占位符
            prompt = template.replace("{{student_info}}", student_text.strip())
            prompt = prompt.replace("{{all_goals}}", goals_text)
            
            # 4. 注入工具描述（含触发规则，已合并进description）
            tools_desc = self.orchestrator.get_tools_description()
            prompt = prompt.replace("{{tools}}", tools_desc)
            
            # 调试日志：检查消息大小和占位符
            total_chars = len(prompt)
            logger.info(f"[Agent] 系统提示词大小: {total_chars} 字符")
            
            # 检查是否还有未替换的占位符
            placeholders = ["{{student_info}}", "{{all_goals}}", "{{tools}}"]
            for placeholder in placeholders:
                if placeholder in prompt:
                    logger.warning(f"[Agent] 发现未替换的占位符: {placeholder}")
            
            if total_chars > 8000:
                logger.warning(f"[Agent] 系统提示词过大: {total_chars} 字符，可能导致400错误")
            
            return prompt.strip()
            
        except Exception as e:
            logger.warning("加载SYSTEM.md失败，使用默认模板: %s", e)
            return self._get_fallback_template()
    
    async def _call_llm_with_tools(self, messages: list, tools: list) -> dict:
        """
        调用LLM(支持工具调用) - 非流式，仅作为降级使用
        
        Args:
            messages: 消息列表
            tools: 工具定义列表(OpenAI格式)
            
        Returns:
            {"content": str, "tool_calls": list} 或 {"content": str}
        """
        try:
            # 调试：打印工具定义
            if tools:
                logger.info(f"[Agent] 调用LLM, 工具数量={len(tools)}")
                for t in tools:
                    func = t.get("function", {})
                    logger.info(f"[Agent] 工具定义: name={func.get('name')}, params={json.dumps(func.get('parameters', {}), ensure_ascii=False)[:200]}")
            else:
                logger.info(f"[Agent] 调用LLM, 无工具")
            
            # 检查AI Provider是否支持工具调用
            if hasattr(self.ai_provider, "chat_with_tools"):
                try:
                    return await self.ai_provider.chat_with_tools(messages, tools)
                except Exception as tool_error:
                    # 工具调用失败，尝试不带工具的普通对话
                    logger.warning(f"[Agent] 带工具调用失败: {tool_error}, 尝试不带工具的普通对话")
                    # 记录详细错误信息
                    error_str = str(tool_error)
                    if "400" in error_str:
                        logger.error(f"[Agent] 400错误详情: {error_str}")
                        # 降级到普通对话：只保留system/user/assistant消息，过滤掉tool消息
                        safe_messages = [m for m in messages if m.get("role") in ("system", "user", "assistant")]
                        # 确保assistant消息的content不为空
                        for m in safe_messages:
                            if m.get("role") == "assistant" and not m.get("content", "").strip():
                                m["content"] = "(继续对话)"
                            # 移除tool_calls等额外字段（普通对话不需要）
                            m.pop("tool_calls", None)
                        result = await self.ai_provider.chat(safe_messages)
                        return {"content": result}
                    raise
            else:
                # 降级到普通对话
                logger.warning("AI Provider不支持工具调用,使用普通对话")
                result = await self.ai_provider.chat(messages)
                return {"content": result}
        except Exception as e:
            logger.error(f"调用LLM失败: {e}", exc_info=True)
            return {"content": f"调用AI服务时遇到问题: {str(e)}"}
    
    async def _call_llm_with_tools_stream(self, messages: list, tools: list, cancel_event=None):
        """
        流式调用LLM(支持工具调用)
        
        优先使用chat_with_tools_stream实现真正的流式输出，
        不支持时降级到非流式chat_with_tools。
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            cancel_event: 取消事件
        
        Yields:
            {"type": "content", "content": str} - 文本内容块
            {"type": "tool_calls", "tool_calls": list} - 完整的工具调用列表
        """
        try:
            if hasattr(self.ai_provider, "chat_with_tools_stream"):
                async for event in self.ai_provider.chat_with_tools_stream(messages, tools):
                    if cancel_event and cancel_event.is_set():
                        return
                    
                    if event.get("type") == "content":
                        yield {"type": "content", "content": event["content"]}
                    elif event.get("type") == "tool_calls":
                        yield {"type": "tool_calls", "tool_calls": event["tool_calls"]}
            else:
                # 降级：使用非流式chat_with_tools，然后假流式输出内容
                logger.info("[Agent] AI Provider不支持流式工具调用，降级到非流式")
                result = await self._call_llm_with_tools(messages, tools)
                
                if result.get("tool_calls"):
                    yield {"type": "tool_calls", "tool_calls": result["tool_calls"]}
                else:
                    # 假流式：逐字输出
                    content = result.get("content", "")
                    for char in content:
                        if cancel_event and cancel_event.is_set():
                            return
                        yield {"type": "content", "content": char}
        except Exception as e:
            logger.error(f"流式调用LLM失败: {e}", exc_info=True)
            yield {"type": "content", "content": f"调用AI服务时遇到问题: {str(e)}"}
    
    def _get_fallback_template(self) -> str:
        """兜底模板"""
        return """你是小智，AI学习助手。使命:引导学生完成学习目标。

## 铁律
1. 严禁编造数据
2. 直接回答用户问题
3. 不知道的信息要诚实说明

## 规范
- ≤100字，简洁直接
- 中文，通俗易懂
- 鼓励为主
- 末尾加建议

## 风格
- 像朋友聊天
- 用生活例子
"""

    async def _stream_chat(self, messages: list, cancel_event=None) -> AsyncGenerator[dict, None]:
        """流式聊天"""
        try:
            if hasattr(self.ai_provider, "chat_stream"):
                async for chunk in self.ai_provider.chat_stream(messages):
                    if cancel_event and cancel_event.is_set():
                        yield {"type": "error", "message": "请求已取消"}
                        return

                    if isinstance(chunk, str):
                        piece = chunk
                    elif isinstance(chunk, dict):
                        piece = chunk.get("content") or chunk.get("message", {}).get("content", "")
                    else:
                        piece = str(chunk)

                    if piece:
                        yield {"type": "chunk", "content": piece}
            else:
                result = await self.ai_provider.chat(messages)
                if isinstance(result, str):
                    response = result
                elif isinstance(result, dict):
                    response = result.get("content", str(result))
                else:
                    response = str(result)
                yield {"type": "chunk", "content": response}

        except Exception as e:
            yield {"type": "error", "message": str(e)}


# 兼容性别名
AgentCore = SimpleAgent
