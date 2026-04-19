"""
AI 模型适配器 - 支持多种模型
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import asyncio
import httpx
import json


class BaseModelProvider(ABC):
    """模型提供商基类"""

    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> str:
        """发送对话请求"""
        pass

    async def chat_stream(self, messages: list, **kwargs):
        """发送对话请求（流式输出）"""
        # 默认实现：先获取完整回复，然后逐个字符输出
        response = await self.chat(messages, **kwargs)
        for char in response:
            yield char

    @abstractmethod
    async def decompose_topic(self, topic: str, context: dict) -> dict:
        """拆解学习主题"""
        pass

    @abstractmethod
    async def decompose_into_categories(self, topic: str, context: dict) -> dict:
        """
        将学习主题拆分为多个类别
        
        Args:
            topic: 学习主题
            context: 上下文信息
            
        Returns:
            dict: {"categories": [{"id": "", "name": "", "description": "", "scope": ""}]}
        """
        pass

    @abstractmethod
    async def generate_sub_graph(self, category: dict, topic: str, context: dict, study_depth: str = "intermediate") -> dict:
        """
        为单个类别生成子知识图谱
        
        Args:
            category: 类别信息 {"id", "name", "description", "scope"}
            topic: 学习主题
            context: 上下文信息
            study_depth: 学习深度 (basic/intermediate/advanced)
            
        Returns:
            dict: {"nodes": [], "edges": []}
        """
        pass

    def _parse_json_response(self, response: str, max_retries: int = 3) -> dict:
        """
        解析 JSON 响应，支持多种格式提取和自动修复
        
        Args:
            response: AI 返回的原始响应
            max_retries: 最大重试次数
            
        Returns:
            dict: 解析后的 JSON 对象
        """
        import json
        import re
        
        # 尝试次数计数器
        attempts = 0
        
        while attempts < max_retries:
            attempts += 1
            
            # 1. 尝试直接解析
            try:
                result = json.loads(response)
                if self._validate_graph_data(result):
                    return result
            except json.JSONDecodeError:
                pass
            
            # 2. 尝试从 markdown 代码块中提取 JSON
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                try:
                    # 尝试修复常见 JSON 错误
                    json_str = self._fix_json_string(json_str)
                    result = json.loads(json_str)
                    if self._validate_graph_data(result):
                        return result
                except json.JSONDecodeError:
                    pass
            
            # 3. 尝试提取任何包含 nodes 的 JSON 对象
            match = re.search(r'\{[\s\S]*?"nodes"[\s\S]*?"edges"[\s\S]*?\}', response)
            if match:
                json_str = match.group(0)
                try:
                    json_str = self._fix_json_string(json_str)
                    result = json.loads(json_str)
                    if self._validate_graph_data(result):
                        return result
                except json.JSONDecodeError:
                    pass
            
            # 4. 如果解析失败但内容看起来是有效的 JSON，尝试修复
            if '"nodes"' in response and '"edges"' in response:
                # 尝试找到 JSON 的开始和结束位置
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    try:
                        json_str = self._fix_json_string(json_str)
                        result = json.loads(json_str)
                        if self._validate_graph_data(result):
                            return result
                    except json.JSONDecodeError:
                        pass
            
            # 4. 如果当前尝试失败，不等待，直接进入下一次尝试
            # 注意：这个函数是同步的，不支持真正的重试
            # 如果解析失败，会直接返回空结果
            pass
        
        # 所有尝试都失败了
        print(f"JSON 解析失败（已尝试 {max_retries} 次），原始响应：{response[:500]}...")
        return {"nodes": [], "edges": []}
    
    def _fix_json_string(self, json_str: str) -> str:
        """
        自动修复常见的 JSON 格式错误
        
        Args:
            json_str: 可能存在格式问题的 JSON 字符串
            
        Returns:
            str: 修复后的 JSON 字符串
        """
        import re
        
        # 移除 BOM 头
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        
        # 移除控制字符（除了换行和制表符）
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
        
        # 将单引号替换为双引号（用于字符串值）
        # 注意：这需要更复杂的处理来区分属性名和字符串值
        # 这里只处理明显的情况：'key': -> "key":
        json_str = re.sub(r"'([^']*)'\s*:", r'"\1":', json_str)
        # 简单处理单引号字符串值（不处理含逗号的情况）
        json_str = re.sub(r':\s*"([^"]*)"', r': "\1"', json_str)
        
        # 移除尾随逗号
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 移除注释（// 或 /* */）
        json_str = re.sub(r'//.*?(\n|$)', '\1', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        return json_str
    
    def _validate_graph_data(self, data: dict) -> bool:
        """
        验证知识图谱数据的有效性
        
        Args:
            data: 待验证的图谱数据
            
        Returns:
            bool: 是否有效（至少包含 5 个有效节点）
        """
        if not isinstance(data, dict):
            return False
        
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        
        # 检查节点是否存在且数量足够
        if not isinstance(nodes, list) or len(nodes) < 5:
            print(f"节点数量不足：{len(nodes) if isinstance(nodes, list) else 0}")
            return False
        
        # 检查节点是否有必要的字段
        valid_nodes = 0
        for node in nodes:
            if isinstance(node, dict) and "id" in node and "name" in node:
                valid_nodes += 1
        
        if valid_nodes < 5:
            print(f"有效节点数量不足：{valid_nodes}")
            return False
        
        return True


class OpenAIProvider(BaseModelProvider):
    """OpenAI API 提供商"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    async def chat(self, messages: list, **kwargs) -> str:
        """OpenAI 对话"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def decompose_topic(self, topic: str, context: dict) -> dict:
        """使用 OpenAI 拆解学习主题"""
        system_prompt = """你是一位资深的知识架构师，擅长将复杂的学习领域拆解为层次分明、逻辑清晰、内容丰富的知识图谱。

## 你的任务
根据用户提供的学习目标信息，生成一个结构完整、专业且内容丰富的知识图谱。你需要尽可能全面地覆盖该领域的核心知识点。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名，如 python_basics）",
      "name": "知识点名称（中文，简洁有力）",
      "description": "详细描述该知识点的核心内容、学习目标及应用场景（2-3句话）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时，浮点数）,
      "prerequisites": ["前置知识点ID列表，如无则为空数组"],
      "category": "所属类别（如：基础概念、核心理论、实践技能、进阶应用、工具框架、最佳实践等）",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种，请根据实际关系选择）"
    }
  ]
}
```

## 重要约束（必须遵守！）
1. **每个节点必须有边**：生成的每个知识点节点都必须与至少一个其他节点建立关系
2. **禁止孤立节点**：绝对不能生成没有任何边连接的孤立节点
3. **边数量要求**：如果生成 N 个节点，边数量必须 >= N-1，确保图谱连通
4. **节点上限**：420个，超过必须删除

## 知识点设计原则
1. **全面覆盖**：深入分析学习主题，生成 15-30 个知识点，确保覆盖该领域的核心概念、理论、技能和应用
2. **层次递进**：构建清晰的学习路径，从入门基础 → 核心概念 → 实践应用 → 高级进阶
3. **结构合理**：
   - foundation（基础）：入门级概念，5-30 分钟（0.1-0.5小时），占比约 25%
   - intermediate（中等）：核心技能，20-60 分钟（0.3-1小时），占比约 40%
   - advanced（进阶）：深入理解，30-120 分钟（0.5-2小时），占比约 25%
   - expert（专家）：精通掌握，60-180 分钟（1-3小时），占比约 10%
4. **依赖清晰**：每个进阶知识点应有明确的前置依赖，形成完整的学习链路
5. **分类精细**：使用 4-8 个类别对知识点进行分组，便于学习者理解知识结构
6. **关系丰富**：知识点之间不仅要有前置依赖，还应包含组成关系、进阶关系、关联关系等

## 边（Edges）关系类型（共8种，必须至少使用3种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分，B由多个A组成（如：傅里叶级数组成傅里叶变换）
3. **进阶关系**：A是B的基础，A掌握后才能学B（如：导数→积分）
4. **对立关系**：A与B是互斥的或相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可以类比学习，有助于理解差异（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的具体应用场景（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质上是相同的原理或方法（如：奈奎斯特采样定理⇔抽样定理）
8. **关联关系**：A与B存在某种联系，但不属于以上任何类型

## 类别设计建议
根据学科特点，可包含以下类别（灵活调整）：
- 基础概念：入门必备的基础理论和术语
- 核心理论：学科的核心原理和关键理论
- 实践技能：实际操作和应用能力
- 工具框架：相关的工具、框架和平台
- 进阶应用：高级应用场景和复杂案例
- 最佳实践：行业标准和经验总结
- 前沿拓展：新兴技术和发展趋势

## 难度级别说明
- foundation（基础）：入门级概念
- intermediate（中等）：需要一定基础
- advanced（进阶）：需要扎实基础
- expert（专家）：需要大量练习和深入理解

请生成一个内容丰富、结构完整、专业实用的知识图谱，确保知识点之间的逻辑连贯性和学习路径的合理性。**重要：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        # 构建用户提示词
        subject = context.get("subject", "")
        description = context.get("description", "")
        student_level = context.get("student_level", "intermediate")
        
        user_prompt = f"""## 学习目标信息
- 学习主题：{topic}
- 学科领域：{subject}
- 目标描述：{description}
- 学生水平：{student_level}

## 请根据以上信息，生成该领域的知识图谱

【重要】只生成与「{topic}」直接相关的专业知识，不要生成任何通用编程知识或AI基础知识！

禁止生成的知识点类型：
- Python/Java/JavaScript等编程语言基础
- 大模型、LLM、Transformer、BERT、GPT等AI模型基础
- 类与对象、面向对象编程等通用编程概念
- Web开发、前端、后端等技术
- 数据结构、算法、计算机网络等计算机基础课程

应该生成的知识点类型（以「信号与系统」为例）：
- 信号分类（连续/离散、确定/随机）
- 傅里叶变换、拉普拉斯变换、Z变换
- 系统响应（冲激响应、频率响应）
- 滤波器设计（低通/高通/带通）
- 卷积运算

要求：
1. **知识点数量**：生成 30-50 个知识点
2. **层次分明**：从基础到进阶
3. **分类精细**：合理分组
4. **时长合理**：根据难度分配
5. **关系丰富**：边的关系类型要多样化，不能只有前置依赖"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        # 使用新的解析方法
        result = self._parse_json_response(response)
        if not self._validate_graph_data(result):
            # 如果解析失败，尝试直接使用结果（可能是空字典）
            return result
        return result

    async def decompose_into_categories(self, topic: str, context: dict) -> dict:
        """
        将学习主题拆分为多个类别
        
        使用策略：
        1. 调用模型将主题拆分为6-12个类别
        2. 每个类别包含：id, name, description, scope（涵盖范围）
        """
        system_prompt = """你是知识架构师，擅长将复杂领域拆解为层次分明的知识体系。

## 你的任务
将给定的学习主题拆分为 6-12 个互不重叠、逻辑清晰的类别/模块。

## 输出要求
请严格按照以下 JSON 格式输出，只输出 categories 数组，不要输出其他内容：

```json
{
  "categories": [
    {
      "id": "唯一标识符（英文驼峰）",
      "name": "类别名称（简洁的中文名称）",
      "description": "该类别的简要描述（1-2句话）",
      "scope": "该类别涵盖的具体知识点范围（用中文描述）"
    }
  ]
}
```

## 设计原则
1. **互不重叠**：每个类别应聚焦于一个明确的子领域
2. **覆盖全面**：涵盖主题的所有重要方面
3. **层次清晰**：按逻辑顺序排列
4. **数量适中**：6-12个类别最佳"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}
- 学科：{context.get('subject', '')}
- 描述：{context.get('description', '')}

请将「{topic}」拆分为多个类别。

【重要】
1. 只生成与「{topic}」直接相关的专业类别
2. 不要生成「通用编程」「数据结构」等与主题无关的类别
3. 类别数量控制在 6-12 个"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        
        # 解析响应（失败时重试一次）
        import re
        max_retries = 2
        for attempt in range(max_retries):
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(response)
                break
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"[Provider] JSON解析失败（第{attempt+1}次），重新调用API...")
                    response = await self.chat(messages, temperature=0.7)
                else:
                    # 最后一次尝试，尝试查找JSON对象
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end > start:
                        result = json.loads(response[start:end])
                    else:
                        result = {"categories": []}
        
        # 验证结果
        categories = result.get("categories", [])
        if len(categories) < 6:
            print(f"警告：类别数量不足({len(categories)}个)，期望6-12个")
        if len(categories) > 12:
            print(f"警告：类别数量过多({len(categories)}个)，将截断到12个")
            result["categories"] = categories[:12]
        
        return result

    async def generate_sub_graph(self, category: dict, topic: str, context: dict, study_depth: str = "intermediate") -> dict:
        """
        为单个类别生成子知识图谱
        
        根据学习深度调整知识点数量：
        - basic(了解): 4-6 个知识点
        - intermediate(熟悉): 8-12 个知识点
        - advanced(深入): 13-18 个知识点
        """
        # 根据学习深度确定知识点数量范围
        depth_config = {
            "basic": {"min": 4, "max": 6, "target": 5, "desc": "4-6"},
            "intermediate": {"min": 8, "max": 12, "target": 10, "desc": "8-12"},
            "advanced": {"min": 13, "max": 18, "target": 15, "desc": "13-18"}
        }
        config = depth_config.get(study_depth, depth_config["intermediate"])
        
        system_prompt = f"""你是知识架构师，擅长为特定领域生成专业的知识图谱。

## 你的任务
为指定的类别生成结构完整的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{{
  "nodes": [
    {{
      "id": "唯一标识符（英文驼峰，格式：类别ID_序号，如 cat1_1）",
      "name": "知识点名称（中文）",
      "description": "详细描述该知识点（2-3句话）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时，浮点数）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别（使用传入的类别名称）",
      "importance": "重要程度（essential/important/optional）"
    }}
  ],
  "edges": [
    {{
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型"
    }}
  ]
}}
```

## 重要约束（必须遵守！）
1. **每个节点必须有边**：生成的每个知识点节点都必须与至少一个其他节点建立关系
2. **禁止孤立节点**：绝对不能生成没有任何边连接的孤立节点
3. **边数量要求**：如果生成 N 个节点，边数量必须 >= N-1，确保图谱连通
4. **节点上限**：420个，超过必须删除

## 知识点设计原则
1. **聚焦范围**：只生成属于该类别范围内的专业知识
2. **数量要求**：{config['min']}-{config['max']} 个知识点
3. **层次递进**：从基础到进阶
4. **依赖清晰**：建立合理的前置依赖关系
5. **关系丰富**：使用前置依赖、组成关系、进阶关系等多种关系

## 难度级别说明
- foundation（基础）：0.1-0.5小时
- intermediate（中等）：0.3-1小时
- advanced（进阶）：0.5-2小时
- expert（专家）：1-3小时

## 边关系类型（8种）
1. 前置依赖：A是B的前置知识
2. 组成关系：A是B的组成部分
3. 进阶关系：A是B的基础
4. 对立关系：A与B是相反概念
5. 对比关系：A与B可类比学习
6. 应用关系：A是B的具体应用
7. 等价关系：A和B本质相同
8. 关联关系：A与B存在某种联系"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}

## 当前类别
- 类别ID：{category.get('id', '')}
- 类别名称：{category.get('name', '')}
- 类别描述：{category.get('description', '')}
- 涵盖范围：{category.get('scope', '')}

请为该类别生成 {config['desc']} 个知识点，形成完整的知识图谱。

【重要】
1. 只生成属于「{category.get('name', '')}」范围内的专业知识
2. 知识点ID必须以「{category.get('id', '')}_」为前缀
3. 不要生成其他类别的知识点
4. 确保知识点之间有清晰的学习路径

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        
        # 解析响应（失败时重试一次）
        import re
        max_retries = 2
        for attempt in range(max_retries):
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(response)
                if self._validate_graph_data(result):
                    break
                raise ValueError("Invalid graph data structure")
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    print(f"[Provider] JSON解析失败（第{attempt+1}次），重新调用API...")
                    response = await self.chat(messages, temperature=0.7)
                else:
                    print(f"JSON解析最终失败，使用空结果: {e}")
                    result = {"nodes": [], "edges": []}
        
        # 验证节点数量
        nodes = result.get("nodes", [])
        if len(nodes) < config["min"]:
            print(f"警告：类别「{category.get('name', '')}」的知识点数量较少({len(nodes)}个)，期望{config['desc']}个")
        
        return result


class OllamaProvider(BaseModelProvider):
    """Ollama API 提供商 - 支持本地部署的 Qwen 等开源模型"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3.5:9B"):
        self.base_url = base_url
        self.model = model
        print(f"初始化 Ollama 模型：{model} (地址：{base_url})")
    
    async def chat(self, messages: list, **kwargs) -> str:
        """Ollama 对话（带取消检查和快速响应）"""
        import asyncio
        import httpx
        from app.services.cancel_manager import wait_if_cancelled, is_cancelled, GenerationCancelledError
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Ollama 使用 OpenAI 兼容格式
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            **kwargs
        }
        
        # 禁用代理，避免 Privoxy 等代理软件干扰本地请求
        transport = httpx.AsyncHTTPTransport(proxy=None)
        
        # 使用较长单次请求超时（180秒），以便生成习题等耗时操作
        request_timeout = 180.0
        max_total_attempts = 1  # 单次请求即可完成
        last_error = None
        
        for attempt in range(max_total_attempts):
            # 每次请求前检查取消
            if is_cancelled():
                raise GenerationCancelledError()
            
            try:
                async with httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(request_timeout, connect=10.0)) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                # 超时时立即检查取消状态，实现快速响应取消
                if is_cancelled():
                    print("[Ollama.chat] 检测到取消请求，立即停止")
                    raise GenerationCancelledError()
                last_error = f"请求超时（第{attempt + 1}次）"
                print(f"[Ollama.chat] {last_error}，继续等待...")
                continue
            except GenerationCancelledError:
                raise
            except Exception as e:
                if is_cancelled():
                    raise GenerationCancelledError()
                last_error = f"请求异常（第{attempt + 1}次）: {e}"
                print(f"[Ollama.chat] {last_error}")
                continue
        
        raise ConnectionError(f"Ollama 请求失败: {last_error}")
    
    def _convert_messages_for_ollama(self, messages: list) -> list:
        """
        将消息转换为 Ollama 多模态格式
        Ollama 支持的多模态格式：
        {
            "role": "user",
            "content": "描述图片",
            "images": ["base64encodedstring"]
        }
        """
        converted = []
        for msg in messages:
            if isinstance(msg, dict):
                # 如果消息包含 images 字段，保持原样（已经是多模态格式）
                if 'images' in msg and msg['images']:
                    converted.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                        "images": msg["images"]
                    })
                else:
                    converted.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            else:
                converted.append(msg)
        return converted
    
    async def _process_single_image_batch(
        self,
        batch_images: list,
        batch_num: int,
        total_batches: int,
        context: dict,
        image_processor,
        global_chunk_num: int,
        total_chunks: int,
        progress_callback
    ) -> dict:
        """
        处理单个图片批次（供并行调用）
        
        Args:
            batch_images: 图片base64编码列表
            batch_num: 当前批次号
            total_batches: 总批次数量
            context: 上下文信息
            image_processor: 图片处理器
            global_chunk_num: 全局分块序号
            total_chunks: 总分块数
            progress_callback: 进度回调函数
            
        Returns:
            该批次的知识图谱数据
        """
        # 检查是否已取消
        from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError
        await wait_if_cancelled()
        
        topic = context.get("topic", "")
        subject = context.get("subject", "")
        description = context.get("description", "")
        
        # 计算进度
        if total_chunks > 0:
            progress_before = int(25 + (global_chunk_num - 1) / total_chunks * 60)
            progress_after = int(25 + global_chunk_num / total_chunks * 60)
        else:
            progress_before = 50
            progress_after = 60
        
        # 发送开始进度
        if progress_callback:
            await progress_callback({
                "status": "generating_graph",
                "progress": progress_before,
                "message": f"正在并行处理第 {global_chunk_num}/{total_chunks} 个分块...",
                "total_chunks": total_chunks,
                "chunk": global_chunk_num
            })
        
        system_prompt = """你是一位资深的知识架构师，擅长从教材、课件等学习资料中提取结构化的知识图谱。

## 你的任务
从提供的学习资料图片中，提取知识点和它们之间的关系，生成一个结构化的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名）",
      "name": "知识点名称（中文）",
      "description": "知识点描述（必须详细，50字以上）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种）"
    }
  ]
}
```

## 边（Edges）关系类型（共8种，必须至少使用2种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分（如：傅里叶级数→傅里叶变换）
3. **进阶关系**：A是B的基础（如：导数→积分）
4. **对立关系**：A与B是相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可类比学习（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的应用（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质相同（如：抽样定理=奈奎斯特采样定理）
8. **关联关系**：A与B存在某种联系

## 知识点发现要求（重要！）
1. **仔细阅读图片**：逐行分析图片中的标题、定义、定理、公式、图表
2. **提取所有关键术语**：包括专业名词、概念名称、方法名称
3. **发现隐含知识点**：不仅提取明显的内容，还要挖掘图片中暗示的概念
4. **建立关系**：分析知识点之间的逻辑关系，不能只有前置依赖
5. **数量要求**：每个批次应提取 5-20 个知识点，宁多勿少
6. **质量要求**：每个知识点的描述必须详细，不能过于简略"""
        
        user_prompt = f"""## 当前批次信息
这是第 {batch_num}/{total_batches} 批次的内容。

## 学习主题
- 主题：{topic}
- 学科：{subject}
- 描述：{description}

## 请分析这批图片内容，提取知识点和依赖关系

【重要】请仔细阅读图片中的所有内容，包括：
- 标题和章节名称
- 定义和概念
- 定理和公式
- 示例和图表
- 术语解释

请提取尽可能多的知识点，并建立丰富的语义关系。

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
                "images": batch_images
            }
        ]
        
        try:
            response = await self.chat(messages, temperature=0.7)
            result = self._parse_json_response(response)
            
            # 发送完成进度
            if progress_callback:
                await progress_callback({
                    "status": "generating_graph",
                    "progress": progress_after,
                    "message": f"已完成第 {global_chunk_num}/{total_chunks} 个分块",
                    "total_chunks": total_chunks,
                    "chunk": global_chunk_num
                })
            
            return result
        except Exception as e:
            print(f"批次 {batch_num} 处理失败: {e}")
            return {"nodes": [], "edges": []}
    
    async def extract_knowledge_from_images(
        self,
        images: List[str],
        context: dict,
        image_processor=None,
        batch_size: int = 5,
        progress_callback=None,
        chunk_offset: int = 0,
        total_chunks: int = None,
        max_parallel: int = 3
    ) -> dict:
        """
        从图片中提取知识（用于处理扫描版PDF）- 真正并行处理版本
        
        Args:
            images: 图片路径列表
            context: 上下文信息（学习目标等）
            image_processor: 图片处理器（用于base64编码）
            batch_size: 每批处理的图片数量
            progress_callback: 进度回调函数
            chunk_offset: 全局分块偏移量
            total_chunks: 总分块数
            max_parallel: 最大并行批次数量（默认3，用于控制并发数）
            
        Returns:
            提取的知识图谱数据 {nodes: [], edges: []}
        """
        if not images:
            return {"nodes": [], "edges": []}
        
        # 计算总分块数
        if total_chunks is None:
            total_chunks = (len(images) + batch_size - 1) // batch_size
        
        # 将图片分成批次
        batches = []
        for i in range(0, len(images), batch_size):
            batch_images = images[i:i + batch_size]
            batches.append(batch_images)
        
        total_batches = len(batches)
        print(f"[并行处理] 共 {total_batches} 个批次，启用真正的并行处理（并发数: {max_parallel}）")
        
        # 预处理所有图片为base64
        all_base64_images = []
        for batch_images in batches:
            image_batches = []
            for img_path in batch_images:
                try:
                    if image_processor:
                        img_base64 = image_processor.image_to_base64(img_path)
                        image_batches.append(img_base64)
                    else:
                        import base64
                        with open(img_path, 'rb') as f:
                            image_batches.append(base64.b64encode(f.read()).decode('utf-8'))
                except Exception as e:
                    print(f"读取图片失败: {img_path}, 错误: {e}")
                    continue
            all_base64_images.append(image_batches)
        
        # 真正的并行处理：所有批次同时启动
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def process_with_semaphore(idx, batch_images):
            async with semaphore:
                batch_num = idx + 1
                global_chunk_num = chunk_offset + batch_num
                
                return await self._process_single_image_batch(
                    batch_images=batch_images,
                    batch_num=batch_num,
                    total_batches=total_batches,
                    context=context,
                    image_processor=image_processor,
                    global_chunk_num=global_chunk_num,
                    total_chunks=total_chunks,
                    progress_callback=progress_callback
                )
        
        # 创建所有任务并真正并行执行
        tasks = []
        for idx, batch_images in enumerate(all_base64_images):
            task = process_with_semaphore(idx, batch_images)
            tasks.append(task)
        
        # 使用 asyncio.gather 并行执行所有任务
        print(f"[并行处理] 启动 {len(tasks)} 个并行任务...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        all_nodes = []
        all_edges = []
        completed = 0
        
        for result in results:
            if isinstance(result, Exception):
                print(f"[并行处理] 任务异常: {result}")
                continue
            if "nodes" in result:
                all_nodes.extend(result["nodes"])
            if "edges" in result:
                all_edges.extend(result["edges"])
            completed += 1
        
        print(f"[并行处理] 完成，共处理 {completed}/{total_batches} 个批次")
        
        # 合并去重
        merged_result = self._merge_knowledge_results(
            [{"nodes": all_nodes, "edges": all_edges}],
            context
        )
        
        return merged_result
    
    async def _process_single_text_chunk(
        self,
        chunk: str,
        chunk_num: int,
        total_chunks: int,
        context: dict,
        global_chunk_num: int,
        progress_callback
    ) -> dict:
        """
        处理单个文本批次（供并行调用）
        
        Args:
            chunk: 文本内容
            chunk_num: 当前批次号
            total_chunks: 总批次数量
            context: 上下文信息
            global_chunk_num: 全局分块序号
            progress_callback: 进度回调函数
            
        Returns:
            该批次的知识图谱数据
        """
        # 检查是否已取消
        from app.services.cancel_manager import wait_if_cancelled
        await wait_if_cancelled()
        
        topic = context.get("topic", "")
        subject = context.get("subject", "")
        description = context.get("description", "")
        
        # 计算进度
        if total_chunks > 0:
            progress_before = int(25 + (global_chunk_num - 1) / total_chunks * 60)
            progress_after = int(25 + global_chunk_num / total_chunks * 60)
        else:
            progress_before = 50
            progress_after = 60
        
        # 发送开始进度
        if progress_callback:
            await progress_callback({
                "status": "generating_graph",
                "progress": progress_before,
                "message": f"正在并行处理第 {global_chunk_num}/{total_chunks} 个分块...",
                "total_chunks": total_chunks,
                "chunk": global_chunk_num
            })
        
        system_prompt = """你是一位资深的知识架构师，擅长从教材、文档等学习资料中提取结构化的知识图谱。

## 你的任务
从提供的学习资料文本中，提取知识点和它们之间的关系，生成一个结构化的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出：

```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名）",
      "name": "知识点名称（中文）",
      "description": "知识点描述（必须详细，50字以上）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种）"
    }
  ]
}
```

## 边（Edges）关系类型（共8种，必须至少使用2种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分（如：傅里叶级数→傅里叶变换）
3. **进阶关系**：A是B的基础（如：导数→积分）
4. **对立关系**：A与B是相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可类比学习（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的应用（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质相同（如：抽样定理=奈奎斯特采样定理）
8. **关联关系**：A与B存在某种联系

## 知识点发现要求（重要！）
1. **仔细阅读文本**：逐句分析文本中的标题、定义、定理、公式
2. **提取所有关键术语**：包括专业名词、概念名称、方法名称
3. **发现隐含知识点**：不仅提取明显的内容，还要挖掘文本中暗示的概念
4. **建立关系**：分析知识点之间的逻辑关系，不能只有前置依赖
5. **数量要求**：每个批次应提取 5-20 个知识点，宁多勿少
6. **质量要求**：每个知识点的描述必须详细，不能过于简略"""
        
        user_prompt = f"""## 当前批次信息
这是第 {chunk_num}/{total_chunks} 批次的内容。

## 学习主题
- 主题：{topic}
- 学科：{subject}
- 描述：{description}

## 学习资料内容（第 {chunk_num} 部分）
---
{chunk}
---

【重要】请仔细阅读文本中的所有内容，包括：
- 标题和章节名称
- 定义和概念
- 定理和公式
- 示例和图表
- 术语解释

请提取尽可能多的知识点，并建立丰富的语义关系。

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.chat(messages, temperature=0.7)
            result = self._parse_json_response(response)
            
            # 发送完成进度
            if progress_callback:
                await progress_callback({
                    "status": "generating_graph",
                    "progress": progress_after,
                    "message": f"已完成第 {global_chunk_num}/{total_chunks} 个分块",
                    "total_chunks": total_chunks,
                    "chunk": global_chunk_num
                })
            
            return result
        except Exception as e:
            print(f"文本批次 {chunk_num} 处理失败: {e}")
            return {"nodes": [], "edges": []}
    
    async def extract_knowledge_from_text(
        self,
        text_chunks: List[str],
        context: dict,
        progress_callback=None,
        chunk_offset: int = 0,
        total_chunks: int = None,
        max_parallel: int = 5
    ) -> dict:
        """
        从文本中提取知识（用于处理文字版PDF、Word、PPT等）- 真正并行处理版本
        
        Args:
            text_chunks: 分好批的文本块列表
            context: 上下文信息
            progress_callback: 进度回调函数
            chunk_offset: 全局分块偏移量
            total_chunks: 总分块数
            max_parallel: 最大并行批次数量（默认5，用于控制并发数）
            
        Returns:
            提取的知识图谱数据
        """
        if not text_chunks:
            return {"nodes": [], "edges": []}
        
        # 计算总分块数
        if total_chunks is None:
            total_chunks = len(text_chunks)
        
        print(f"[并行处理] 共 {total_chunks} 个文本批次，启用真正的并行处理（并发数: {max_parallel}）")
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def process_text_with_semaphore(idx, chunk):
            async with semaphore:
                chunk_num = idx + 1
                global_chunk_num = chunk_offset + chunk_num
                
                return await self._process_single_text_chunk(
                    chunk=chunk,
                    chunk_num=chunk_num,
                    total_chunks=total_chunks,
                    context=context,
                    global_chunk_num=global_chunk_num,
                    progress_callback=progress_callback
                )
        
        # 创建所有任务并真正并行执行
        tasks = []
        for idx, chunk in enumerate(text_chunks):
            task = process_text_with_semaphore(idx, chunk)
            tasks.append(task)
        
        # 使用 asyncio.gather 并行执行所有任务
        print(f"[并行处理] 启动 {len(tasks)} 个并行任务...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        all_nodes = []
        all_edges = []
        completed = 0
        
        for result in results:
            if isinstance(result, Exception):
                print(f"[并行处理] 任务异常: {result}")
                continue
            if "nodes" in result:
                all_nodes.extend(result["nodes"])
            if "edges" in result:
                all_edges.extend(result["edges"])
            completed += 1
        
        print(f"[并行处理] 完成，共处理 {completed}/{total_chunks} 个文本批次")
        
        # 合并去重
        merged_result = self._merge_knowledge_results(
            [{"nodes": all_nodes, "edges": all_edges}],
            context
        )
        
        return merged_result
    
    def _merge_knowledge_results(self, results: List[dict], context: dict) -> dict:
        """
        合并多次提取的知识图谱结果
        
        Args:
            results: 多次提取的结果列表
            context: 上下文信息
            
        Returns:
            合并后的知识图谱数据
        """
        all_nodes = []
        all_edges = []
        
        for result in results:
            if "nodes" in result:
                all_nodes.extend(result["nodes"])
            if "edges" in result:
                all_edges.extend(result["edges"])
        
        # 去重节点（基于ID）
        unique_nodes = {}
        for node in all_nodes:
            node_id = node.get("id", "")
            if node_id and node_id not in unique_nodes:
                unique_nodes[node_id] = node
        
        # 处理跨批次边：只保留两端节点都存在的边
        valid_node_ids = set(unique_nodes.keys())
        valid_edges = []
        seen_edges = set()
        
        for edge in all_edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            
            # 检查边是否有效（两端节点都存在）
            if source in valid_node_ids and target in valid_node_ids:
                # 去重
                edge_key = f"{source}->{target}"
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    valid_edges.append(edge)
        
        # 合并相似节点（基于名称相似度）
        merged_nodes = self._merge_similar_nodes(list(unique_nodes.values()))
        
        return {
            "nodes": merged_nodes,
            "edges": valid_edges
        }
    
    def _merge_similar_nodes(self, nodes: List[dict], similarity_threshold: float = 0.8) -> List[dict]:
        """
        合并相似的节点（基于名称相似度）
        
        Args:
            nodes: 节点列表
            similarity_threshold: 相似度阈值
            
        Returns:
            去重后的节点列表
        """
        if not nodes:
            return []
        
        # 简单的名称相似度检查（后续可以改进为更复杂的算法）
        unique_nodes = []
        node_names = []
        
        for node in nodes:
            name = node.get("name", "")
            # 简单的完全匹配去重
            if name not in node_names:
                node_names.append(name)
                unique_nodes.append(node)
        
        return unique_nodes

    async def chat_stream(self, messages: list, **kwargs):
        """Ollama 流式对话 - 使用原生 API 支持 think 参数和多模态"""
        headers = {
            "Content-Type": "application/json"
        }
        
        # 检查是否需要启用思维链
        enable_think = kwargs.pop('think', False)
        
        # 转换消息格式以支持多模态
        converted_messages = self._convert_messages_for_ollama(messages)
        
        # 使用 Ollama 原生 API 格式
        payload = {
            "model": self.model,
            "messages": converted_messages,
            "stream": True,
            "think": enable_think,  # 启用思维链
            **kwargs
        }
        
        transport = httpx.AsyncHTTPTransport(proxy=None)
        async with httpx.AsyncClient(transport=transport) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",  # Ollama 原生 API 端点
                headers=headers,
                json=payload,
                timeout=None
            ) as response:
                response.raise_for_status()
                in_thinking = False
                thinking_ended = False  # 标记思维链是否已结束
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                                        
                        if 'message' in data:
                            msg = data['message']
                                            
                            # 处理思维链输出 (在 message.thinking 字段)
                            if enable_think and 'thinking' in msg:
                                think_chunk = msg['thinking']
                                if think_chunk:
                                    # 直接输出思维链内容
                                    yield think_chunk
                                            
                            # 输出正式回复 - 在思维链和正式回答之间添加分隔符
                            if 'content' in msg and msg['content']:
                                if enable_think and not thinking_ended:
                                    # 如果是第一次输出 content，且之前有思维链，输出分隔符
                                    yield "\n---END_OF_THINKING---\n"
                                    thinking_ended = True
                                yield msg['content']
                    except Exception as e:
                        print(f"解析错误：{e}")
                        pass
    
    async def decompose_topic(self, topic: str, context: dict) -> dict:
        """使用 Ollama 拆解学习主题"""
        system_prompt = """你是一位资深的知识架构师，擅长将复杂的学习领域拆解为层次分明、逻辑清晰、内容丰富的知识图谱。

## 你的任务
根据用户提供的学习目标信息，生成一个结构完整、专业且内容丰富的知识图谱。你需要尽可能全面地覆盖该领域的核心知识点。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名，如 python_basics）",
      "name": "知识点名称（中文，简洁有力）",
      "description": "详细描述该知识点的核心内容、学习目标及应用场景（2-3句话）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时，浮点数）,
      "prerequisites": ["前置知识点ID列表，如无则为空数组"],
      "category": "所属类别（如：基础概念、核心理论、实践技能、进阶应用、工具框架、最佳实践等）",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种，请根据实际关系选择）"
    }
  ]
}
```

## 重要约束（必须遵守！）
1. **每个节点必须有边**：生成的每个知识点节点都必须与至少一个其他节点建立关系
2. **禁止孤立节点**：绝对不能生成没有任何边连接的孤立节点
3. **边数量要求**：如果生成 N 个节点，边数量必须 >= N-1，确保图谱连通
4. **节点上限**：420个，超过必须删除

## 知识点设计原则
1. **全面覆盖**：深入分析学习主题，生成 15-30 个知识点，确保覆盖该领域的核心概念、理论、技能和应用
2. **层次递进**：构建清晰的学习路径，从入门基础 → 核心概念 → 实践应用 → 高级进阶
3. **结构合理**：
   - foundation（基础）：入门级概念，5-30 分钟（0.1-0.5小时），占比约 25%
   - intermediate（中等）：核心技能，20-60 分钟（0.3-1小时），占比约 40%
   - advanced（进阶）：深入理解，30-120 分钟（0.5-2小时），占比约 25%
   - expert（专家）：精通掌握，60-180 分钟（1-3小时），占比约 10%
4. **依赖清晰**：每个进阶知识点应有明确的前置依赖，形成完整的学习链路
5. **分类精细**：使用 4-8 个类别对知识点进行分组，便于学习者理解知识结构
6. **关系丰富**：知识点之间不仅要有前置依赖，还应包含组成关系、进阶关系、关联关系等

## 边（Edges）关系类型（共8种，必须至少使用3种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分，B由多个A组成（如：傅里叶级数组成傅里叶变换）
3. **进阶关系**：A是B的基础，A掌握后才能学B（如：导数→积分）
4. **对立关系**：A与B是互斥的或相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可以类比学习，有助于理解差异（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的具体应用场景（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质上是相同的原理或方法（如：奈奎斯特采样定理⇔抽样定理）
8. **关联关系**：A与B存在某种联系，但不属于以上任何类型

## 类别设计建议
根据学科特点，可包含以下类别（灵活调整）：
- 基础概念：入门必备的基础理论和术语
- 核心理论：学科的核心原理和关键理论
- 实践技能：实际操作和应用能力
- 工具框架：相关的工具、框架和平台
- 进阶应用：高级应用场景和复杂案例
- 最佳实践：行业标准和经验总结
- 前沿拓展：新兴技术和发展趋势

## 难度级别说明
- foundation（基础）：入门级概念
- intermediate（中等）：需要一定基础
- advanced（进阶）：需要扎实基础
- expert（专家）：需要大量练习和深入理解

请生成一个内容丰富、结构完整、专业实用的知识图谱，确保知识点之间的逻辑连贯性和学习路径的合理性。**重要：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        # 构建用户提示词
        subject = context.get("subject", "")
        description = context.get("description", "")
        student_level = context.get("student_level", "intermediate")
        
        user_prompt = f"""## 学习目标信息
- 学习主题：{topic}
- 学科领域：{subject}
- 目标描述：{description}
- 学生水平：{student_level}

## 请根据以上信息，生成该领域的知识图谱

【重要】只生成与「{topic}」直接相关的专业知识，不要生成任何通用编程知识或AI基础知识！

禁止生成的知识点类型：
- Python/Java/JavaScript等编程语言基础
- 大模型、LLM、Transformer、BERT、GPT等AI模型基础
- 类与对象、面向对象编程等通用编程概念
- Web开发、前端、后端等技术
- 数据结构、算法、计算机网络等计算机基础课程

应该生成的知识点类型（以「信号与系统」为例）：
- 信号分类（连续/离散、确定/随机）
- 傅里叶变换、拉普拉斯变换、Z变换
- 系统响应（冲激响应、频率响应）
- 滤波器设计（低通/高通/带通）
- 卷积运算

要求：
1. **知识点数量**：生成 20-40 个知识点
2. **层次分明**：从基础到进阶
3. **分类精细**：合理分组
4. **时长合理**：根据难度分配"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        # 使用新的解析方法
        result = self._parse_json_response(response)
        if not self._validate_graph_data(result):
            # 如果解析失败，尝试直接使用结果（可能是空字典）
            return result
        return result

    async def decompose_into_categories(self, topic: str, context: dict) -> dict:
        """
        将学习主题拆分为多个类别
        
        使用策略：
        1. 调用模型将主题拆分为6-12个类别
        2. 每个类别包含：id, name, description, scope（涵盖范围）
        """
        system_prompt = """你是知识架构师，擅长将复杂领域拆解为层次分明的知识体系。

## 你的任务
将给定的学习主题拆分为 6-12 个互不重叠、逻辑清晰的类别/模块。

## 输出要求
请严格按照以下 JSON 格式输出，只输出 categories 数组，不要输出其他内容：

```json
{
  "categories": [
    {
      "id": "唯一标识符（英文驼峰）",
      "name": "类别名称（简洁的中文名称）",
      "description": "该类别的简要描述（1-2句话）",
      "scope": "该类别涵盖的具体知识点范围（用中文描述）"
    }
  ]
}
```

## 设计原则
1. **互不重叠**：每个类别应聚焦于一个明确的子领域
2. **覆盖全面**：涵盖主题的所有重要方面
3. **层次清晰**：按逻辑顺序排列
4. **数量适中**：6-12个类别最佳

## 类别示例（以「人工智能」为例）
- 机器学习基础：涵盖监督学习、无监督学习等基础概念
- 深度学习核心：涵盖神经网络、反向传播等
- 计算机视觉：涵盖图像处理、目标检测等
- 自然语言处理：涵盖文本处理、语义理解等"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}
- 学科：{context.get('subject', '')}
- 描述：{context.get('description', '')}

请将「{topic}」拆分为多个类别。

【重要】
1. 只生成与「{topic}」直接相关的专业类别
2. 不要生成「通用编程」「数据结构」等与主题无关的类别
3. 类别数量控制在 6-12 个"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        
        # 解析响应
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            try:
                result = json.loads(response)
            except:
                # 尝试查找 JSON 对象
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    result = json.loads(response[start:end])
                else:
                    result = {"categories": []}
        
        # 验证结果
        categories = result.get("categories", [])
        if len(categories) < 6:
            print(f"警告：类别数量不足({len(categories)}个)，期望6-12个")
        if len(categories) > 12:
            print(f"警告：类别数量过多({len(categories)}个)，将截断到12个")
            result["categories"] = categories[:12]
        
        return result

    async def generate_sub_graph(self, category: dict, topic: str, context: dict, study_depth: str = "intermediate") -> dict:
        """
        为单个类别生成子知识图谱
        
        根据学习深度调整知识点数量：
        - basic(了解): 4-6 个知识点
        - intermediate(熟悉): 8-12 个知识点
        - advanced(深入): 13-18 个知识点
        """
        # 根据学习深度确定知识点数量范围
        depth_config = {
            "basic": {"min": 4, "max": 6, "target": 5, "desc": "4-6"},
            "intermediate": {"min": 8, "max": 12, "target": 10, "desc": "8-12"},
            "advanced": {"min": 13, "max": 18, "target": 15, "desc": "13-18"}
        }
        config = depth_config.get(study_depth, depth_config["intermediate"])
        
        system_prompt = f"""你是知识架构师，擅长为特定领域生成专业的知识图谱。

## 你的任务
为指定的类别生成结构完整的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{{
  "nodes": [
    {{
      "id": "唯一标识符（英文驼峰，格式：类别ID_序号，如 cat1_1）",
      "name": "知识点名称（中文）",
      "description": "详细描述该知识点（2-3句话）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时，浮点数）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别（使用传入的类别名称）",
      "importance": "重要程度（essential/important/optional）"
    }}
  ],
  "edges": [
    {{
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型"
    }}
  ]
}}
```

## 重要约束（必须遵守！）
1. **每个节点必须有边**：生成的每个知识点节点都必须与至少一个其他节点建立关系
2. **禁止孤立节点**：绝对不能生成没有任何边连接的孤立节点
3. **边数量要求**：如果生成 N 个节点，边数量必须 >= N-1，确保图谱连通
4. **节点上限**：420个，超过必须删除

## 知识点设计原则
1. **聚焦范围**：只生成属于该类别范围内的专业知识
2. **数量要求**：{config['min']}-{config['max']} 个知识点
3. **层次递进**：从基础到进阶
4. **依赖清晰**：建立合理的前置依赖关系
5. **关系丰富**：使用前置依赖、组成关系、进阶关系等多种关系

## 难度级别说明
- foundation（基础）：0.1-0.5小时
- intermediate（中等）：0.3-1小时
- advanced（进阶）：0.5-2小时
- expert（专家）：1-3小时

## 边关系类型（8种）
1. 前置依赖：A是B的前置知识
2. 组成关系：A是B的组成部分
3. 进阶关系：A是B的基础
4. 对立关系：A与B是相反概念
5. 对比关系：A与B可类比学习
6. 应用关系：A是B的具体应用
7. 等价关系：A和B本质相同
8. 关联关系：A与B存在某种联系"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}

## 当前类别
- 类别ID：{category.get('id', '')}
- 类别名称：{category.get('name', '')}
- 类别描述：{category.get('description', '')}
- 涵盖范围：{category.get('scope', '')}

请为该类别生成 {config['desc']} 个知识点，形成完整的知识图谱。

【重要】
1. 只生成属于「{category.get('name', '')}」范围内的专业知识
2. 知识点ID必须以「{category.get('id', '')}_」为前缀
3. 不要生成其他类别的知识点
4. 确保知识点之间有清晰的学习路径

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        
        # 解析响应（失败时重试一次）
        import re
        max_retries = 2
        for attempt in range(max_retries):
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(response)
                if self._validate_graph_data(result):
                    break
                raise ValueError("Invalid graph data structure")
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    print(f"[Provider] JSON解析失败（第{attempt+1}次），重新调用API...")
                    response = await self.chat(messages, temperature=0.7)
                else:
                    print(f"JSON解析最终失败，使用空结果: {e}")
                    result = {"nodes": [], "edges": []}
        
        # 验证节点数量
        nodes = result.get("nodes", [])
        if len(nodes) < config["min"]:
            print(f"警告：类别「{category.get('name', '')}」的知识点数量较少({len(nodes)}个)，期望{config['desc']}个")
        
        return result


class QwenProvider(BaseModelProvider):
    """通义千问本地模型提供商（简化实现）"""
    
    def __init__(self, model_path: str, device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        # TODO: 加载本地模型
        print(f"初始化 Qwen 模型：{model_path} (设备：{device})")
    
    async def chat(self, messages: list, **kwargs) -> str:
        """Qwen 对话（占位实现）"""
        # TODO: 实现本地模型推理
        return "[Qwen本地模型] 这是一个示例响应"
    
    async def decompose_topic(self, topic: str, context: dict) -> dict:
        """使用 Qwen 拆解学习主题"""
        # TODO: 实现本地模型的推理
        return {
            "nodes": [
                {
                    "id": "intro",
                    "name": f"{topic}入门",
                    "description": f"了解{topic}的基本概念",
                    "difficulty": "easy",
                    "estimated_hours": 2.0,
                    "prerequisites": []
                }
            ],
            "edges": []
        }


class CustomProvider(BaseModelProvider):
    """
    自定义 OpenAI 兼容 API 提供商
    支持配置任意 OpenAI 格式的 API 端点，如：
    - 通义千问 (DashScope)
    - DeepSeek
    - 智谱 AI
    - 本地部署的开源模型
    等
    """
    
    def __init__(
        self, 
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        supports_thinking: bool = False
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.supports_thinking = supports_thinking
        print(f"初始化自定义模型：{model} (端点：{base_url})")
    
    def _get_headers(self) -> dict:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _is_ollama_endpoint(self) -> bool:
        """检查是否使用 Ollama 端点"""
        return "ollama" in self.base_url.lower()
    
    async def chat(self, messages: list, **kwargs) -> str:
        """自定义 API 对话，支持重试机制和取消检查"""
        import asyncio
        import httpx
        from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError
        
        headers = self._get_headers()
        
        # 检查是否需要启用思维链
        enable_think = kwargs.pop('think', False)
        
        # Ollama 端点使用原生 API
        if self._is_ollama_endpoint():
            payload = {
                "model": self.model,
                "messages": self._convert_messages(messages),
                "stream": False,
                "think": enable_think if self.supports_thinking else False,
                **kwargs
            }
            endpoint = f"{self.base_url}/api/chat"
        else:
            # OpenAI 兼容格式
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                **kwargs
            }
            endpoint = f"{self.base_url}/chat/completions"
        
        # 重试机制配置
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            # 每次重试前检查取消
            await wait_if_cancelled()
            
            try:
                transport = httpx.AsyncHTTPTransport(proxy=None)
                async with httpx.AsyncClient(transport=transport) as client:
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        json=payload,
                        timeout=180.0  # 增加超时时间到180秒
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if self._is_ollama_endpoint():
                        return data.get("message", {}).get("content", "")
                    return data["choices"][0]["message"]["content"]
            except GenerationCancelledError:
                # 重新抛出取消异常
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                retry_count += 1
                last_error = e
                print(f"[CustomProvider] API请求失败 (尝试 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2)  # 等待2秒后重试
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                retry_count += 1
                last_error = e
                print(f"[CustomProvider] API响应错误 (尝试 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)
        
        # 所有重试都失败
        raise Exception(f"API请求失败，已重试{max_retries}次: {last_error}")
    
    def _convert_messages(self, messages: list) -> list:
        """转换消息格式以支持多模态"""
        converted = []
        for msg in messages:
            if isinstance(msg, dict):
                if 'images' in msg and msg['images']:
                    converted.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                        "images": msg["images"]
                    })
                else:
                    converted.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            else:
                converted.append(msg)
        return converted

    async def chat_stream(self, messages: list, **kwargs):
        """自定义 API 流式对话"""
        headers = self._get_headers()
        
        # 检查是否需要启用思维链
        enable_think = kwargs.pop('think', False)
        
        # Ollama 端点使用原生 API
        if self._is_ollama_endpoint():
            converted_messages = self._convert_messages(messages)
            payload = {
                "model": self.model,
                "messages": converted_messages,
                "stream": True,
                "think": enable_think if self.supports_thinking else False,
                **kwargs
            }
            endpoint = f"{self.base_url}/api/chat"
        else:
            # OpenAI 兼容格式
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                **kwargs
            }
            endpoint = f"{self.base_url}/chat/completions"
        
        transport = httpx.AsyncHTTPTransport(proxy=None)
        async with httpx.AsyncClient(transport=transport) as client:
            async with client.stream(
                "POST",
                endpoint,
                headers=headers,
                json=payload,
                timeout=120.0
            ) as response:
                response.raise_for_status()
                
                # Ollama 流式响应处理
                if self._is_ollama_endpoint():
                    thinking_ended = False
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if 'message' in data:
                                msg = data['message']
                                
                                # 处理思维链输出
                                if enable_think and self.supports_thinking and 'thinking' in msg:
                                    think_chunk = msg['thinking']
                                    if think_chunk:
                                        yield think_chunk
                                
                                # 处理内容输出
                                if 'content' in msg and msg['content']:
                                    if enable_think and self.supports_thinking and not thinking_ended:
                                        yield "\n---END_OF_THINKING---\n"
                                        thinking_ended = True
                                    yield msg['content']
                        except Exception as e:
                            print(f"解析错误：{e}")
                            pass
                else:
                    # OpenAI 兼容格式流式响应
                    async for chunk in response.aiter_lines():
                        if not chunk or not chunk.strip():
                            continue
                        if chunk.startswith("data: "):
                            data_str = chunk[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("choices") and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                pass
    
    async def chat_with_tools(self, messages: list, tools: list) -> dict:
        """
        支持工具调用的对话(OpenAI Function Calling)
        
        Args:
            messages: 消息列表
            tools: 工具定义列表(OpenAI格式)
            
        Returns:
            {"content": str, "tool_calls": list} 或 {"content": str}
        """
        import httpx
        
        headers = self._get_headers()
        
        # Ollama端点不支持Function Calling,降级到普通对话
        if self._is_ollama_endpoint():
            logger.warning("Ollama端点不支持Function Calling,使用普通对话")
            content = await self.chat(messages)
            return {"content": content}
        
        # OpenAI兼容格式
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto"  # 让模型自动决定是否调用工具
        }
        
        # 调试日志：打印请求关键信息
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"[DeepSeek] 请求URL: {self.base_url}/chat/completions")
        _logger.info(f"[DeepSeek] 模型: {self.model}")
        _logger.info(f"[DeepSeek] 消息数量: {len(messages)}")
        _logger.info(f"[DeepSeek] 工具数量: {len(tools) if tools else 0}")
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content_len = len(str(msg.get("content", "")))
            _logger.info(f"[DeepSeek] 消息[{i}] role={role}, content长度={content_len}")
        if tools:
            for t in tools:
                fname = t.get("function", {}).get("name", "unknown")
                _logger.info(f"[DeepSeek] 工具: {fname}")
        
        transport = httpx.AsyncHTTPTransport(proxy=None)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            # 先记录响应状态码和错误详情
            if response.status_code != 200:
                error_body = response.text
                _logger.error(f"[DeepSeek] API错误: status={response.status_code}, body={error_body[:1000]}")
            
            response.raise_for_status()
            data = response.json()
            
            choice = data["choices"][0]["message"]
            result = {"content": choice.get("content", "")}
            
            # 检查是否有工具调用
            if "tool_calls" in choice and choice["tool_calls"]:
                result["tool_calls"] = []
                for tc in choice["tool_calls"]:
                    result["tool_calls"].append({
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),  # 保留type字段（DeepSeek必需）
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"]
                        }
                    })
            
            return result
    
    async def chat_with_tools_stream(self, messages: list, tools: list):
        """
        支持工具调用的流式对话
        
        使用OpenAI流式API,同时支持工具调用检测和内容流式输出。
        
        Yields:
            {"type": "content", "content": str} - 文本内容块（实时流式输出）
            {"type": "tool_calls", "tool_calls": list} - 完整的工具调用列表（当模型决定调用工具时，所有chunk累积完成后一次性yield）
        """
        import httpx
        
        import logging
        _logger = logging.getLogger(__name__)
        
        headers = self._get_headers()
        
        # Ollama端点不支持Function Calling,降级到普通流式对话
        if self._is_ollama_endpoint():
            _logger.warning("Ollama端点不支持Function Calling流式,降级到普通流式对话")
            async for chunk in self.chat_stream(messages):
                if isinstance(chunk, str):
                    yield {"type": "content", "content": chunk}
                elif isinstance(chunk, dict):
                    yield {"type": "content", "content": chunk.get("content", "")}
            return
        
        # OpenAI兼容格式 - 流式请求
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": True  # 启用流式
        }
        
        _logger.info(f"[DeepSeek-Stream] 请求URL: {self.base_url}/chat/completions")
        _logger.info(f"[DeepSeek-Stream] 模型: {self.model}, 消息数: {len(messages)}, 工具数: {len(tools)}")
        
        transport = httpx.AsyncHTTPTransport(proxy=None)
        async with httpx.AsyncClient(transport=transport) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_text = error_body.decode('utf-8', errors='replace')
                    _logger.error(f"[DeepSeek-Stream] API错误: status={response.status_code}, body={error_text[:1000]}")
                    response.raise_for_status()
                
                # 累积工具调用的delta
                tool_calls_map = {}  # {index: {id, type, function: {name, arguments}}}
                has_tool_calls = False
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # SSE格式: "data: {...}" 或 "data: [DONE]"
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        
                        delta = choices[0].get("delta", {})
                        finish_reason = choices[0].get("finish_reason")
                        
                        # 处理内容块 - 直接流式输出
                        content = delta.get("content")
                        if content:
                            yield {"type": "content", "content": content}
                        
                        # 处理工具调用delta - 累积
                        if "tool_calls" in delta:
                            has_tool_calls = True
                            for tc_delta in delta["tool_calls"]:
                                idx = tc_delta.get("index", 0)
                                
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {
                                        "id": tc_delta.get("id", ""),
                                        "type": tc_delta.get("type", "function"),
                                        "function": {
                                            "name": "",
                                            "arguments": ""
                                        }
                                    }
                                
                                # 累积id
                                if tc_delta.get("id"):
                                    tool_calls_map[idx]["id"] = tc_delta["id"]
                                
                                # 累积type
                                if tc_delta.get("type"):
                                    tool_calls_map[idx]["type"] = tc_delta["type"]
                                
                                # 累积function name
                                func_delta = tc_delta.get("function", {})
                                if func_delta.get("name"):
                                    tool_calls_map[idx]["function"]["name"] += func_delta["name"]
                                
                                # 累积function arguments
                                if func_delta.get("arguments"):
                                    tool_calls_map[idx]["function"]["arguments"] += func_delta["arguments"]
                
                # 流式结束后，如果有工具调用，yield完整的tool_calls
                if has_tool_calls:
                    tool_calls_list = []
                    for idx in sorted(tool_calls_map.keys()):
                        tool_calls_list.append(tool_calls_map[idx])
                    _logger.info(f"[DeepSeek-Stream] 检测到 {len(tool_calls_list)} 个工具调用")
                    yield {"type": "tool_calls", "tool_calls": tool_calls_list}
    
    async def decompose_into_categories(self, topic: str, context: dict) -> dict:
        """
        将学习主题拆分为多个类别
        
        使用策略：
        1. 调用模型将主题拆分为6-12个类别
        2. 每个类别包含：id, name, description, scope（涵盖范围）
        """
        system_prompt = """你是知识架构师，擅长将复杂领域拆解为层次分明的知识体系。

## 你的任务
将给定的学习主题拆分为 6-12 个互不重叠、逻辑清晰的类别/模块。

## 输出要求
请严格按照以下 JSON 格式输出，只输出 categories 数组，不要输出其他内容：

```json
{
  "categories": [
    {
      "id": "唯一标识符（英文驼峰）",
      "name": "类别名称（简洁的中文名称）",
      "description": "该类别的简要描述（1-2句话）",
      "scope": "该类别涵盖的具体知识点范围（用中文描述）"
    }
  ]
}
```

## 设计原则
1. **互不重叠**：每个类别应聚焦于一个明确的子领域
2. **覆盖全面**：涵盖主题的所有重要方面
3. **层次清晰**：按逻辑顺序排列
4. **数量适中**：6-12个类别最佳"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}
- 学科：{context.get('subject', '')}
- 描述：{context.get('description', '')}

请将「{topic}」拆分为多个类别。

【重要】
1. 只生成与「{topic}」直接相关的专业类别
2. 不要生成「通用编程」「数据结构」等与主题无关的类别
3. 类别数量控制在 6-12 个"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        
        # 解析响应（失败时重试一次）
        import re
        max_retries = 2
        for attempt in range(max_retries):
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(response)
                break
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"[Provider] JSON解析失败（第{attempt+1}次），重新调用API...")
                    response = await self.chat(messages, temperature=0.7)
                else:
                    # 最后一次尝试，尝试查找JSON对象
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end > start:
                        result = json.loads(response[start:end])
                    else:
                        result = {"categories": []}
        
        # 验证结果
        categories = result.get("categories", [])
        if len(categories) < 6:
            print(f"警告：类别数量不足({len(categories)}个)，期望6-12个")
        if len(categories) > 12:
            print(f"警告：类别数量过多({len(categories)}个)，将截断到12个")
            result["categories"] = categories[:12]
        
        return result
    
    async def generate_sub_graph(self, category: dict, topic: str, context: dict, study_depth: str = "intermediate") -> dict:
        """
        为单个类别生成子知识图谱
        
        根据学习深度调整知识点数量：
        - basic(了解): 4-6 个知识点
        - intermediate(熟悉): 8-12 个知识点
        - advanced(深入): 13-18 个知识点
        """
        # 根据学习深度确定知识点数量范围
        depth_config = {
            "basic": {"min": 4, "max": 6, "target": 5, "desc": "4-6"},
            "intermediate": {"min": 8, "max": 12, "target": 10, "desc": "8-12"},
            "advanced": {"min": 13, "max": 18, "target": 15, "desc": "13-18"}
        }
        config = depth_config.get(study_depth, depth_config["intermediate"])
        
        system_prompt = f"""你是知识架构师，擅长为特定领域生成专业的知识图谱。

## 你的任务
为指定的类别生成结构完整的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{{
  "nodes": [
    {{
      "id": "唯一标识符（英文驼峰，格式：类别ID_序号，如 cat1_1）",
      "name": "知识点名称（中文）",
      "description": "详细描述该知识点（2-3句话）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时，浮点数）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别（使用传入的类别名称）",
      "importance": "重要程度（essential/important/optional）"
    }}
  ],
  "edges": [
    {{
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型"
    }}
  ]
}}
```

## 重要约束（必须遵守！）
1. **每个节点必须有边**：生成的每个知识点节点都必须与至少一个其他节点建立关系
2. **禁止孤立节点**：绝对不能生成没有任何边连接的孤立节点
3. **边数量要求**：如果生成 N 个节点，边数量必须 >= N-1，确保图谱连通
4. **节点上限**：420个，超过必须删除

## 知识点设计原则
1. **聚焦范围**：只生成属于该类别范围内的专业知识
2. **数量要求**：{config['min']}-{config['max']} 个知识点
3. **层次递进**：从基础到进阶
4. **依赖清晰**：建立合理的前置依赖关系
5. **关系丰富**：使用前置依赖、组成关系、进阶关系等多种关系

## 难度级别说明
- foundation（基础）：0.1-0.5小时
- intermediate（中等）：0.3-1小时
- advanced（进阶）：0.5-2小时
- expert（专家）：1-3小时

## 边关系类型（8种）
1. 前置依赖：A是B的前置知识
2. 组成关系：A是B的组成部分
3. 进阶关系：A是B的基础
4. 对立关系：A与B是相反概念
5. 对比关系：A与B可类比学习
6. 应用关系：A是B的具体应用
7. 等价关系：A和B本质相同
8. 关联关系：A与B存在某种联系"""
        
        user_prompt = f"""## 学习主题
- 主题：{topic}

## 当前类别
- 类别ID：{category.get('id', '')}
- 类别名称：{category.get('name', '')}
- 类别描述：{category.get('description', '')}
- 涵盖范围：{category.get('scope', '')}

请为该类别生成 {config['desc']} 个知识点，形成完整的知识图谱。

【重要】
1. 只生成属于「{category.get('name', '')}」范围内的专业知识
2. 知识点ID必须以「{category.get('id', '')}_」为前缀
3. 不要生成其他类别的知识点
4. 确保知识点之间有清晰的学习路径

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        
        # 解析响应（失败时重试一次）
        import re
        max_retries = 2
        for attempt in range(max_retries):
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    result = json.loads(response)
                if self._validate_graph_data(result):
                    break
                raise ValueError("Invalid graph data structure")
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    print(f"[Provider] JSON解析失败（第{attempt+1}次），重新调用API...")
                    response = await self.chat(messages, temperature=0.7)
                else:
                    print(f"JSON解析最终失败，使用空结果: {e}")
                    result = {"nodes": [], "edges": []}
        
        # 验证节点数量
        nodes = result.get("nodes", [])
        if len(nodes) < config["min"]:
            print(f"警告：类别「{category.get('name', '')}」的知识点数量较少({len(nodes)}个)，期望{config['desc']}个")
        
        return result
    
    async def decompose_topic(self, topic: str, context: dict) -> dict:
        """使用自定义 API 拆解学习主题"""
        system_prompt = """你是一位资深的知识架构师，擅长将复杂的学习领域拆解为层次分明、逻辑清晰、内容丰富的知识图谱。

## 你的任务
根据用户提供的学习目标信息，生成一个结构完整、专业且内容丰富的知识图谱。你需要尽可能全面地覆盖该领域的核心知识点。

## 输出要求
请严格按照以下 JSON 格式输出，包含 nodes（节点）和 edges（边）两个数组：

```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名，如 python_basics）",
      "name": "知识点名称（中文，简洁有力）",
      "description": "详细描述该知识点的核心内容、学习目标及应用场景（2-3句话）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时，浮点数）,
      "prerequisites": ["前置知识点ID列表，如无则为空数组"],
      "category": "所属类别（如：基础概念、核心理论、实践技能、进阶应用、工具框架、最佳实践等）",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种，请根据实际关系选择）"
    }
  ]
}
```

## 重要约束（必须遵守！）
1. **每个节点必须有边**：生成的每个知识点节点都必须与至少一个其他节点建立关系
2. **禁止孤立节点**：绝对不能生成没有任何边连接的孤立节点
3. **边数量要求**：如果生成 N 个节点，边数量必须 >= N-1，确保图谱连通
4. **节点上限**：420个，超过必须删除

## 知识点设计原则
1. **全面覆盖**：深入分析学习主题，生成 15-30 个知识点，确保覆盖该领域的核心概念、理论、技能和应用
2. **层次递进**：构建清晰的学习路径，从入门基础 → 核心概念 → 实践应用 → 高级进阶
3. **结构合理**：
   - foundation（基础）：入门级概念，5-30 分钟（0.1-0.5小时），占比约 25%
   - intermediate（中等）：核心技能，20-60 分钟（0.3-1小时），占比约 40%
   - advanced（进阶）：深入理解，30-120 分钟（0.5-2小时），占比约 25%
   - expert（专家）：精通掌握，60-180 分钟（1-3小时），占比约 10%
4. **依赖清晰**：每个进阶知识点应有明确的前置依赖，形成完整的学习链路
5. **分类精细**：使用 4-8 个类别对知识点进行分组，便于学习者理解知识结构
6. **关系丰富**：知识点之间不仅要有前置依赖，还应包含组成关系、进阶关系、关联关系等

## 边（Edges）关系类型（共8种，必须至少使用3种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分，B由多个A组成（如：傅里叶级数组成傅里叶变换）
3. **进阶关系**：A是B的基础，A掌握后才能学B（如：导数→积分）
4. **对立关系**：A与B是互斥的或相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可以类比学习，有助于理解差异（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的具体应用场景（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质上是相同的原理或方法（如：奈奎斯特采样定理⇔抽样定理）
8. **关联关系**：A与B存在某种联系，但不属于以上任何类型

## 类别设计建议
根据学科特点，可包含以下类别（灵活调整）：
- 基础概念：入门必备的基础理论和术语
- 核心理论：学科的核心原理和关键理论
- 实践技能：实际操作和应用能力
- 工具框架：相关的工具、框架和平台
- 进阶应用：高级应用场景和复杂案例
- 最佳实践：行业标准和经验总结
- 前沿拓展：新兴技术和发展趋势

## 难度级别说明
- foundation（基础）：入门级概念
- intermediate（中等）：需要一定基础
- advanced（进阶）：需要扎实基础
- expert（专家）：需要大量练习和深入理解

请生成一个内容丰富、结构完整、专业实用的知识图谱，确保知识点之间的逻辑连贯性和学习路径的合理性。**重要：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
        
        # 构建用户提示词
        subject = context.get("subject", "")
        description = context.get("description", "")
        student_level = context.get("student_level", "intermediate")
        
        user_prompt = f"""## 学习目标信息
- 学习主题：{topic}
- 学科领域：{subject}
- 目标描述：{description}
- 学生水平：{student_level}

## 请根据以上信息，生成该领域的知识图谱

【重要】只生成与「{topic}」直接相关的专业知识，不要生成任何通用编程知识或AI基础知识！

禁止生成的知识点类型：
- Python/Java/JavaScript等编程语言基础
- 大模型、LLM、Transformer、BERT、GPT等AI模型基础
- 类与对象、面向对象编程等通用编程概念
- Web开发、前端、后端等技术
- 数据结构、算法、计算机网络等计算机基础课程

应该生成的知识点类型（以「信号与系统」为例）：
- 信号分类（连续/离散、确定/随机）
- 傅里叶变换、拉普拉斯变换、Z变换
- 系统响应（冲激响应、频率响应）
- 滤波器设计（低通/高通/带通）
- 卷积运算

要求：
1. **知识点数量**：生成 30-50 个知识点
2. **层次分明**：从基础到进阶
3. **分类精细**：合理分组
4. **时长合理**：根据难度分配
5. **关系丰富**：边的关系类型要多样化，不能只有前置依赖"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        # 使用新的解析方法
        result = self._parse_json_response(response)
        if not self._validate_graph_data(result):
            # 如果解析失败，尝试直接使用结果（可能是空字典）
            return result
        return result
    
    async def extract_knowledge_from_images(
        self,
        images: List[str],
        context: dict,
        image_processor=None,
        batch_size: int = 5,
        progress_callback=None,
        chunk_offset: int = 0,
        total_chunks: int = None
    ) -> dict:
        """
        从图片中提取知识（用于处理扫描版PDF）
        
        Args:
            images: 图片路径列表
            context: 上下文信息
            image_processor: 图片处理器
            batch_size: 每批处理的图片数量
            progress_callback: 进度回调函数
            chunk_offset: 全局分块偏移量
            total_chunks: 总分块数
            
        Returns:
            提取的知识图谱数据
        """
        if not images:
            return {"nodes": [], "edges": []}
        
        # 计算总分块数
        if total_chunks is None:
            total_chunks = (len(images) + batch_size - 1) // batch_size
        
        # 分批处理图片
        all_nodes = []
        all_edges = []
        
        for i in range(0, len(images), batch_size):
            batch_images = images[i:i + batch_size]
            batch_num = i // batch_size + 1
            global_chunk_num = chunk_offset + batch_num
            total_batches = (len(images) + batch_size - 1) // batch_size
            
            print(f"处理图片批次 {batch_num}/{total_batches}，共 {len(batch_images)} 张图片")
            
            # 计算进度：生成图谱阶段从 25% 到 85%，每个分块均匀分配
            # 公式：25 + (global_chunk_num - 1) / total_chunks * 60
            # 注意：处理 total_chunks 为 0 的情况
            if total_chunks > 0:
                progress_before = int(25 + (global_chunk_num - 1) / total_chunks * 60)
                progress_after = int(25 + global_chunk_num / total_chunks * 60)
            else:
                # total_chunks 为 0 时，使用固定的进度值
                progress_before = 50
                progress_after = 60
            
            # 5. 每个分块处理前（在调用 AI 模型前）
            if progress_callback:
                await progress_callback({
                    "status": "generating_graph",
                    "progress": progress_before,
                    "message": f"正在处理第 {global_chunk_num}/{total_chunks} 个分块...",
                    "total_chunks": total_chunks,
                    "chunk": global_chunk_num
                })
            
            # 将图片转换为base64
            image_batches = []
            for img_path in batch_images:
                try:
                    if image_processor:
                        img_base64 = image_processor.image_to_base64(img_path)
                        image_batches.append(img_base64)
                    else:
                        import base64
                        with open(img_path, 'rb') as f:
                            image_batches.append(base64.b64encode(f.read()).decode('utf-8'))
                except Exception as e:
                    print(f"读取图片失败: {img_path}, 错误: {e}")
                    continue
            
            if not image_batches:
                continue
            
            topic = context.get("topic", "")
            subject = context.get("subject", "")
            description = context.get("description", "")
            
            # 获取之前批次的知识图谱数据（如果有）
            previous_context = context.get("previous_graph", {}) if context else {}
            prev_nodes = previous_context.get("nodes", [])
            prev_edges = previous_context.get("edges", [])
            
            system_prompt = """你是一位资深的知识架构师，擅长从教材、课件等学习资料中提取结构化的知识图谱。

## 你的任务
从提供的学习资料图片中，提取知识点和它们之间的关系，生成一个结构化的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出：
```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名）",
      "name": "知识点名称（中文）",
      "description": "知识点描述（必须详细，50字以上）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种）"
    }
  ]
}
```

## 边（Edges）关系类型（共8种，必须至少使用2种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分（如：傅里叶级数→傅里叶变换）
3. **进阶关系**：A是B的基础（如：导数→积分）
4. **对立关系**：A与B是相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可类比学习（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的应用（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质相同（如：抽样定理=奈奎斯特采样定理）
8. **关联关系**：A与B存在某种联系

## 知识点发现要求（重要！）
1. **仔细阅读图片**：逐行分析图片中的标题、定义、定理、公式、图表
2. **提取所有关键术语**：包括专业名词、概念名称、方法名称
3. **发现隐含知识点**：不仅提取明显的内容，还要挖掘图片中暗示的概念
4. **建立关系**：分析知识点之间的逻辑关系，不能只有前置依赖
5. **数量要求**：每个批次应提取 5-20 个知识点，宁多勿少
6. **质量要求**：每个知识点的描述必须详细，不能过于简略"""
            
            user_prompt = f"""## 当前批次信息
这是第 {batch_num}/{total_batches} 批次的内容。
{"请注意与之前批次的内容保持衔接，构建完整的知识体系。" if batch_num > 1 else ""}

## 学习主题
- 主题：{topic}
- 学科：{subject}
- 描述：{description}

{f"## 之前批次的知识图谱（供参考）\n以下是前几个批次已经发现的知识点，请确保新知识点与这些知识点建立关系，并检查是否有遗漏的重要概念。\n```json\n{{\"nodes\": {prev_nodes[:20] if prev_nodes else []}, \"edges\": {prev_edges[:20] if prev_edges else []}}}\n```" if batch_num > 1 and prev_nodes else ""}

## 请分析这批图片内容，提取知识点和依赖关系

【重要】请仔细阅读图片中的所有内容，包括：
- 标题和章节名称
- 定义和概念
- 定理和公式
- 示例和图表
- 术语解释

请提取尽可能多的知识点，并建立丰富的语义关系。

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": user_prompt,
                    "images": image_batches
                }
            ]
            
            try:
                response = await self.chat(messages, temperature=0.7)
                result = self._parse_json_response(response)
                
                if "nodes" in result:
                    all_nodes.extend(result["nodes"])
                if "edges" in result:
                    all_edges.extend(result["edges"])
                
                # 6. 每个分块处理后（AI模型返回结果后）
                if progress_callback:
                    await progress_callback({
                        "status": "generating_graph",
                        "progress": progress_after,
                        "message": f"已完成第 {global_chunk_num}/{total_chunks} 个分块",
                        "total_chunks": total_chunks,
                        "chunk": global_chunk_num
                    })
                    
            except Exception as e:
                print(f"批次 {batch_num} 处理失败: {e}")
                continue
        
        # 合并去重
        merged_result = self._merge_knowledge_results(
            [{"nodes": all_nodes, "edges": all_edges}],
            context
        )
        
        return merged_result
    
    async def extract_knowledge_from_text(
        self,
        text_chunks: List[str],
        context: dict,
        progress_callback=None,
        chunk_offset: int = 0,
        total_chunks: int = None
    ) -> dict:
        """
        从文本中提取知识（用于处理文字版PDF、Word、PPT等）
        
        Args:
            text_chunks: 分好批的文本块列表
            context: 上下文信息
            progress_callback: 进度回调函数
            chunk_offset: 全局分块偏移量
            total_chunks: 总分块数
            
        Returns:
            提取的知识图谱数据
        """
        if not text_chunks:
            return {"nodes": [], "edges": []}
        
        # 计算总分块数
        if total_chunks is None:
            total_chunks = len(text_chunks)
        
        all_nodes = []
        all_edges = []
        
        for i, chunk in enumerate(text_chunks):
            chunk_num = i + 1
            global_chunk_num = chunk_offset + i + 1
            
            print(f"处理文本批次 {chunk_num}/{len(text_chunks)} (全局: {global_chunk_num}/{total_chunks})")
            
            # 计算进度：生成图谱阶段从 25% 到 85%，每个分块均匀分配
            # 公式：25 + (global_chunk_num - 1) / total_chunks * 60
            # 注意：处理 total_chunks 为 0 的情况
            if total_chunks > 0:
                progress_before = int(25 + (global_chunk_num - 1) / total_chunks * 60)
                progress_after = int(25 + global_chunk_num / total_chunks * 60)
            else:
                # total_chunks 为 0 时，使用固定的进度值
                progress_before = 50
                progress_after = 60
            
            # 5. 每个分块处理前（在调用 AI 模型前）
            if progress_callback:
                await progress_callback({
                    "status": "generating_graph",
                    "progress": progress_before,
                    "message": f"正在处理第 {global_chunk_num}/{total_chunks} 个分块...",
                    "total_chunks": total_chunks,
                    "chunk": global_chunk_num
                })
            
            topic = context.get("topic", "")
            subject = context.get("subject", "")
            description = context.get("description", "")
            
            # 获取之前批次的知识图谱数据（如果有）
            previous_context = context.get("previous_graph", {}) if context else {}
            prev_nodes = previous_context.get("nodes", [])
            prev_edges = previous_context.get("edges", [])
            
            system_prompt = """你是一位资深的知识架构师，擅长从教材、文档等学习资料中提取结构化的知识图谱。

## 你的任务
从提供的学习资料文本中，提取知识点和它们之间的关系，生成一个结构化的知识图谱。

## 输出要求
请严格按照以下 JSON 格式输出：
```json
{
  "nodes": [
    {
      "id": "唯一标识符（英文，驼峰命名）",
      "name": "知识点名称（中文）",
      "description": "知识点描述（必须详细，50字以上）",
      "difficulty": "难度级别（foundation/intermediate/advanced/expert）",
      "estimated_hours": 预计学习时长（小时）,
      "prerequisites": ["前置知识点ID列表"],
      "category": "所属类别",
      "importance": "重要程度（essential/important/optional）"
    }
  ],
  "edges": [
    {
      "source": "起始节点ID",
      "target": "目标节点ID",
      "relation": "关系类型（共8种）"
    }
  ]
}
```

## 边（Edges）关系类型（共8种，必须至少使用2种以上）
1. **前置依赖**：A是B的前置知识，学B之前必须先学A
2. **组成关系**：A是B的组成部分（如：傅里叶级数→傅里叶变换）
3. **进阶关系**：A是B的基础（如：导数→积分）
4. **对立关系**：A与B是相反的概念（如：收敛vs发散）
5. **对比关系**：A与B可类比学习（如：拉普拉斯vs傅里叶）
6. **应用关系**：A是B的应用（如：傅里叶变换→信号滤波）
7. **等价关系**：A和B本质相同（如：抽样定理=奈奎斯特采样定理）
8. **关联关系**：A与B存在某种联系

## 知识点发现要求（重要！）
1. **仔细阅读文本**：逐句分析文本中的标题、定义、定理、公式
2. **提取所有关键术语**：包括专业名词、概念名称、方法名称
3. **发现隐含知识点**：不仅提取明显的内容，还要挖掘文本中暗示的概念
4. **建立关系**：分析知识点之间的逻辑关系，不能只有前置依赖
5. **数量要求**：每个批次应提取 5-20 个知识点，宁多勿少
6. **质量要求**：每个知识点的描述必须详细，不能过于简略"""
            
            user_prompt = f"""## 当前批次信息
这是第 {chunk_num}/{len(text_chunks)} 批次的内容。
{"请注意与之前批次的内容保持衔接，构建完整的知识体系。" if chunk_num > 1 else "这是第一批内容，请尽可能全面地覆盖核心概念。"}

## 学习主题
- 主题：{topic}
- 学科：{subject}
- 描述：{description}

{f"## 之前批次的知识图谱（供参考）\n以下是前几个批次已经发现的知识点，请确保新知识点与这些知识点建立关系，并检查是否有遗漏的重要概念。\n```json\n{{\"nodes\": {prev_nodes[:20] if prev_nodes else []}, \"edges\": {prev_edges[:20] if prev_edges else []}}}\n```" if chunk_num > 1 and prev_nodes else ""}

## 学习资料内容（第 {chunk_num} 部分）
---
{chunk}
---

【重要】请仔细阅读文本中的所有内容，包括：
- 标题和章节名称
- 定义和概念
- 定理和公式
- 示例和图表
- 术语解释

请提取尽可能多的知识点，并建立丰富的语义关系。

**重要约束：确保每个节点都至少有一条边，绝不能出现孤立节点！**"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            try:
                response = await self.chat(messages, temperature=0.7)
                result = self._parse_json_response(response)
                
                if "nodes" in result:
                    all_nodes.extend(result["nodes"])
                if "edges" in result:
                    all_edges.extend(result["edges"])
                
                # 6. 每个分块处理后（AI模型返回结果后）
                if progress_callback:
                    await progress_callback({
                        "status": "generating_graph",
                        "progress": progress_after,
                        "message": f"已完成第 {global_chunk_num}/{total_chunks} 个分块",
                        "total_chunks": total_chunks,
                        "chunk": global_chunk_num
                    })
                    
            except Exception as e:
                print(f"文本批次 {chunk_num} 处理失败: {e}")
                continue
        
        # 合并去重
        merged_result = self._merge_knowledge_results(
            [{"nodes": all_nodes, "edges": all_edges}],
            context
        )
        
        return merged_result
    
    def _merge_knowledge_results(self, results: List[dict], context: dict) -> dict:
        """
        合并多次提取的知识图谱结果
        """
        all_nodes = []
        all_edges = []
        
        for result in results:
            if "nodes" in result:
                all_nodes.extend(result["nodes"])
            if "edges" in result:
                all_edges.extend(result["edges"])
        
        # 去重节点
        unique_nodes = {}
        for node in all_nodes:
            node_id = node.get("id", "")
            if node_id and node_id not in unique_nodes:
                unique_nodes[node_id] = node
        
        # 处理边
        valid_node_ids = set(unique_nodes.keys())
        valid_edges = []
        seen_edges = set()
        
        for edge in all_edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            
            if source in valid_node_ids and target in valid_node_ids:
                edge_key = f"{source}->{target}"
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    valid_edges.append(edge)
        
        # 合并相似节点
        merged_nodes = self._merge_similar_nodes(list(unique_nodes.values()))
        
        return {
            "nodes": merged_nodes,
            "edges": valid_edges
        }
    
    def _merge_similar_nodes(self, nodes: List[dict], similarity_threshold: float = 0.8) -> List[dict]:
        """
        合并相似的节点
        """
        if not nodes:
            return []
        
        unique_nodes = []
        node_names = []
        
        for node in nodes:
            name = node.get("name", "")
            if name not in node_names:
                node_names.append(name)
                unique_nodes.append(node)
        
        return unique_nodes


class AIModelProvider:
    """AI 模型统一接口"""
    
    def __init__(self, provider_name: str, config: dict):
        """
        初始化模型提供商
        
        Args:
            provider_name: 提供商名称（openai/ollama/custom）
            config: 配置参数
        """
        self.provider_name = provider_name  # 保存提供商名称
        
        if provider_name == "openai":
            self.provider = OpenAIProvider(
                api_key=config.get("OPENAI_API_KEY", ""),
                model=config.get("OPENAI_MODEL", "gpt-3.5-turbo")
            )
        elif provider_name == "ollama":
            self.provider = OllamaProvider(
                base_url=config.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=config.get("OLLAMA_MODEL", "qwen3.5:9B")
            )
        elif provider_name == "custom":
            self.provider = CustomProvider(
                api_key=config.get("CUSTOM_API_KEY", ""),
                base_url=config.get("CUSTOM_API_BASE_URL", "https://api.openai.com/v1"),
                model=config.get("CUSTOM_MODEL", "gpt-3.5-turbo"),
                supports_thinking=config.get("CUSTOM_SUPPORTS_THINKING", False)
            )
        elif provider_name == "qwen":
            self.provider = QwenProvider(
                model_path=config.get("QWEN_MODEL_PATH", ""),
                device=config.get("QWEN_DEVICE", "cuda")
            )
        else:
            raise ValueError(f"不支持的模型提供商：{provider_name}")
    
    def is_ollama(self) -> bool:
        """
        检查是否使用 Ollama 模型
        
        Returns:
            bool: 是否是 Ollama 模型
        """
        return self.provider_name == "ollama"
    
    async def chat(self, messages: list, **kwargs) -> str:
        """发送对话请求"""
        return await self.provider.chat(messages, **kwargs)
    
    async def chat_with_tools(self, messages: list, tools: list) -> dict:
        """发送带工具调用的对话请求"""
        if hasattr(self.provider, "chat_with_tools"):
            return await self.provider.chat_with_tools(messages, tools)
        else:
            # 降级到普通对话
            content = await self.provider.chat(messages)
            return {"content": content}
    
    async def chat_with_tools_stream(self, messages: list, tools: list):
        """发送带工具调用的流式对话请求"""
        if hasattr(self.provider, "chat_with_tools_stream"):
            async for event in self.provider.chat_with_tools_stream(messages, tools):
                yield event
        elif hasattr(self.provider, "chat_stream"):
            # 降级到普通流式对话
            async for chunk in self.provider.chat_stream(messages):
                if isinstance(chunk, str):
                    yield {"type": "content", "content": chunk}
                elif isinstance(chunk, dict):
                    yield {"type": "content", "content": chunk.get("content", "")}
        else:
            # 最终降级：非流式 + 假流式
            result = await self.chat_with_tools(messages, tools)
            if result.get("tool_calls"):
                yield {"type": "tool_calls", "tool_calls": result["tool_calls"]}
            else:
                yield {"type": "content", "content": result.get("content", "")}
    
    async def chat_stream(self, messages: list, **kwargs):
        """发送对话请求（流式输出）"""
        async for chunk in self.provider.chat_stream(messages, **kwargs):
            yield chunk
    
    async def decompose_topic(self, topic: str, context: dict) -> dict:
        """拆解学习主题"""
        return await self.provider.decompose_topic(topic, context)
    
    async def decompose_into_categories(self, topic: str, context: dict) -> dict:
        """将学习主题拆分为多个类别"""
        return await self.provider.decompose_into_categories(topic, context)
    
    async def generate_sub_graph(self, category: dict, topic: str, context: dict, study_depth: str = "intermediate") -> dict:
        """为单个类别生成子知识图谱"""
        return await self.provider.generate_sub_graph(category, topic, context, study_depth)
    
    async def generate_lesson_content(
        self, 
        knowledge_point: dict, 
        student_level: str,
        study_goal_title: str = None,
        study_goal_description: str = None,
        student_preferences: dict = None
    ) -> dict:
        """
        生成课时内容 - PPT幻灯片形式
        
        Args:
            knowledge_point: 知识点信息
            student_level: 学生水平
            study_goal_title: 学习目标标题（用于上下文关联）
            study_goal_description: 学习目标描述（用于上下文关联）
            student_preferences: 学生偏好信息（包含学习风格、背景等）
        """
        # 构建学生偏好上下文（用于个性化内容生成）
        preference_context = ""
        if student_preferences:
            # 学习风格偏好
            learning_style = student_preferences.get("learning_style", {})
            primary_style = learning_style.get("primary_style", "visual")
            style_scores = learning_style.get("style_scores", {})
            
            # 背景信息
            background = student_preferences.get("background", {})
            nickname = student_preferences.get("nickname", "")
            grade = student_preferences.get("grade", "")
            
            # 构建偏好描述
            style_desc = {
                "visual": "视觉型（偏好图表、图像、颜色对比）",
                "auditory": "听觉型（偏好听讲、讨论、口头解释）",
                "reading": "阅读型（偏好文字、表格、书面材料）",
                "kinesthetic": "动觉型（偏好动手实践、案例演练）"
            }.get(primary_style, "视觉型")
            
            preference_context = f"""
【学习者画像】
- 学生昵称：{nickname or "学习者"}
- 年级/背景：{grade or "未知"}
- 学习风格：{style_desc}
- 风格得分：视觉{int(style_scores.get('visual', 50))} | 听觉{int(style_scores.get('auditory', 50))} | 阅读{int(style_scores.get('reading', 50))} | 动觉{int(style_scores.get('kinesthetic', 50))}

【个性化教学要求】
根据上述学习者画像，请调整教学内容：
1. **表达方式**：根据学习风格调整讲解方式
   - 视觉型：多用图表、流程图、颜色标记、空间结构
   - 听觉型：多用类比讲解、口头叙述、问答互动
   - 阅读型：提供清晰的文字归纳、表格对比、步骤列表
   - 动觉型：增加实际案例、应用场景、动手练习环节
2. **案例选择**：根据学生背景选择合适的难度和领域的案例
3. **难度梯度**：根据学生水平调整内容深度
   - beginner（初学者）：从基础概念讲起，避免专业术语
   - intermediate（进阶）：在基础上深入，适当引入专业概念
   - advanced（高级）：深入原理和高级应用
4. **节奏控制**：根据学习风格调整信息密度
"""
        
        # 构建学习目标上下文
        goal_context = ""
        topic_focus = ""
        if study_goal_title:
            goal_context = f"""
【学习目标背景】
你正在帮助学生完成学习目标："{study_goal_title}"
"""
            if study_goal_description:
                goal_context += f"目标描述：{study_goal_description}\n"
        
        # 强调知识点的专业性和独立性，防止AI混入无关内容
        topic_name = knowledge_point.get('name', '未知知识点')
        topic_description = knowledge_point.get('description', '')
        topic_difficulty = knowledge_point.get('difficulty', 'intermediate')
        topic_hours = knowledge_point.get('estimated_hours', 1.0)
        
        topic_focus = f"""
【关键约束 - 严格遵守】
1. 你正在教授的知识点是：「{topic_name}」
2. 这个知识点属于学习目标「{study_goal_title or '当前学习主题'}」
3. 你的所有教学内容必须100%围绕「{topic_name}」展开
4. 绝对禁止引入任何与「{topic_name}」无关的内容（如其他学科、编程语言、通用AI知识等）
5. 封面标题必须是「{topic_name}」，不能使用其他标题
6. 示例和练习题必须与「{topic_name}」直接相关

【{topic_name}知识点详情】
知识点名称：{topic_name}
知识点描述：{topic_description}
难度级别：{topic_difficulty}
预计学习时长：{topic_hours}小时
"""
        
        system_prompt = f"""你是一位资深教育专家，擅长将复杂知识点转化为生动有趣的PPT式教学内容。
{topic_focus}
{preference_context}

请根据上述知识点信息生成PPT幻灯片形式的教学内容。

【内容生成要求】

你不需要按照固定模板组织内容，而是根据知识点的特点，自由设计最适合的讲解结构。关键是：
1. 把知识讲清楚、讲透彻
2. 内容要有逻辑性和连贯性
3. 使用生动的例子和类比
4. 可以包含代码、公式、图表等

每页幻灯片应该：
- 聚焦一个核心概念或观点
- 内容充实（200-500字）
- 使用Markdown格式，支持代码块、列表、表格等
- 语言通俗易懂，避免过于学术化

【幻灯片结构建议】（仅供参考，你可以自由调整）：
- 封面：课时标题、学习目标
- 引入：为什么学这个？生活化场景
- 核心内容：2-5页，根据知识点复杂度决定
  * 概念讲解
  * 原理说明
  * 示例演示
  * 注意事项/常见误区
- 实战案例：具体应用场景
- 练习题：2-3道题目（包含题干、选项、答案、解析）
- 总结：核心要点回顾

【输出格式】
请以JSON格式返回，slides是一个数组，每个元素代表一页幻灯片。

JSON结构：
{{
    "slides": [
        {{
            "type": "cover",
            "title": "幻灯片标题",
            "content": "幻灯片内容（支持Markdown）"
        }},
        {{
            "type": "content",
            "title": "核心概念",
            "content": "详细讲解内容..."
        }},
        {{
            "type": "code",
            "title": "代码示例",
            "content": "```python\\n代码内容\\n```"
        }},
        {{
            "type": "exercise",
            "title": "课堂练习",
            "content": "题目内容",
            "questions": [
                {{
                    "difficulty": "easy",
                    "question": "题目",
                    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
                    "answer": "A",
                    "explanation": "解析"
                }}
            ]
        }},
        {{
            "type": "summary",
            "title": "课程总结",
            "content": "总结内容..."
        }}
    ]
}}

幻灯片类型说明：
- cover: 封面
- content: 普通内容页
- code: 代码示例页
- example: 案例演示页
- exercise: 练习题页
- summary: 总结页"""
        
        user_prompt = f"""请生成「{topic_name}」的PPT幻灯片教学内容。

学生水平：{student_level}

要求：
1. 封面标题必须是「{topic_name}」
2. 所有内容必须100%围绕「{topic_name}」展开
3. 生成至少5页幻灯片（封面+课程引入+核心讲解+练习+总结）"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.7)
        import json
        import re
        try:
            # 去掉 markdown 代码块标记
            json_text = response.strip()
            # 去掉 ```json 和 ``` 标记
            json_text = re.sub(r'^```json\s*', '', json_text, flags=re.MULTILINE)
            json_text = re.sub(r'^```\s*$', '', json_text, flags=re.MULTILINE)
            result = json.loads(json_text)
            # 验证内容质量
            result = self._validate_lesson_slides(result, knowledge_point)
            return result
        except Exception as e:
            print(f"[generate_lesson_content] 解析失败: {e}, 响应: {response[:200]}")
            return {"slides": []}
    
    def _validate_lesson_slides(self, content: dict, knowledge_point: dict) -> dict:
        """
        验证PPT幻灯片内容质量
        """
        if 'slides' not in content or not content['slides']:
            print(f"[validate_lesson_slides] 警告: slides 字段缺失或为空")
            content['slides'] = []
        
        slides = content['slides']
        
        # 检查幻灯片数量
        if len(slides) < 3:
            print(f"[validate_lesson_slides] 警告: 幻灯片数量不足 ({len(slides)} 页)")
        
        # 检查每页幻灯片的内容
        for idx, slide in enumerate(slides):
            if 'type' not in slide:
                slide['type'] = 'content'
            if 'title' not in slide or not slide['title']:
                slide['title'] = f"第{idx+1}页"
            if 'content' not in slide or not slide['content']:
                slide['content'] = "（内容待补充）"
            
            # 检查内容长度
            if len(str(slide['content'])) < 50:
                print(f"[validate_lesson_slides] 警告: 第{idx+1}页内容过短")
        
        return content
    
    async def generate_questions(self, knowledge_point: str, difficulty: str, count: int = 3) -> list:
        """生成练习题"""
        system_prompt = """你是一个专业的出题老师，请根据知识点生成高质量的练习题。

每道题包含：
- question: 题干（**必须填写**，清晰完整的中文问题，不能为空）
- options: 选项（选择题，4个选项）或 null（非选择题）
- answer: 正确答案
- explanation: 答案解析
- error_analysis: 常见错误分析

## 重要约束
1. question 字段**绝对不能为空**，必须是完整的中文问题句
2. 题目内容必须与知识点相关
3. 选项必须有区分度

请以 JSON 数组格式返回。"""
        
        user_prompt = f"""请为以下知识点生成{count}道{difficulty}难度的题目：
知识点：{knowledge_point}

题目类型以选择题为主。**注意：每道题的题干（question）必须填写完整的中文问题，不能为空。**"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat(messages, temperature=0.8)
        import json
        try:
            return json.loads(response)
        except:
            return []
    
    async def extract_knowledge_from_images(
        self,
        images: List[str],
        context: dict,
        image_processor=None,
        batch_size: int = 5,
        progress_callback=None,
        chunk_offset: int = 0,
        total_chunks: int = None
    ) -> dict:
        """
        从图片中提取知识（用于处理扫描版PDF）
        
        Args:
            images: 图片路径列表
            context: 上下文信息
            image_processor: 图片处理器
            batch_size: 每批处理的图片数量
            progress_callback: 进度回调函数
            chunk_offset: 全局分块偏移量
            total_chunks: 总分块数
            
        Returns:
            提取的知识图谱数据
        """
        if hasattr(self.provider, 'extract_knowledge_from_images'):
            return await self.provider.extract_knowledge_from_images(
                images=images,
                context=context,
                image_processor=image_processor,
                batch_size=batch_size,
                progress_callback=progress_callback,
                chunk_offset=chunk_offset,
                total_chunks=total_chunks
            )
        else:
            # 如果provider不支持，返回空结果
            print(f"警告: 当前模型提供商不支持图片知识提取")
            return {"nodes": [], "edges": []}
    
    async def extract_knowledge_from_text(
        self,
        text_chunks: List[str],
        context: dict,
        progress_callback=None,
        chunk_offset: int = 0,
        total_chunks: int = None
    ) -> dict:
        """
        从文本中提取知识（用于处理文字版PDF、Word、PPT等）

        Args:
            text_chunks: 分好批的文本块列表
            context: 上下文信息
            progress_callback: 进度回调函数
            chunk_offset: 全局分块偏移量
            total_chunks: 总分块数

        Returns:
            提取的知识图谱数据
        """
        if hasattr(self.provider, 'extract_knowledge_from_text'):
            return await self.provider.extract_knowledge_from_text(
                text_chunks=text_chunks,
                context=context,
                progress_callback=progress_callback,
                chunk_offset=chunk_offset,
                total_chunks=total_chunks
            )
        else:
            # 如果provider不支持，返回空结果
            print(f"警告: 当前模型提供商不支持文本知识提取")
            return {"nodes": [], "edges": []}

    # ==================== 学习计划章-节结构生成方法 ====================

    async def generate_plan_structure(
        self,
        nodes: List[dict],
        edges: List[dict],
        constraints: dict,
        graph_title: str = "",
        graph_description: str = "",
        progress_callback=None
    ) -> dict:
        """
        根据知识图谱生成章-节结构

        Args:
            nodes: 知识点节点列表
            edges: 知识点依赖边列表
            constraints: 约束条件（max_chapters, max_sections_per_chapter）
            graph_title: 图谱标题
            graph_description: 图谱描述
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            dict: 章节结构数据，包含chapters数组
        """
        # 构建节点列表字符串
        nodes_str = "\n".join([
            f"- [{n['id']}] {n['name']}: {n.get('description', '')} (难度:{n.get('difficulty', 'intermediate')}, 预计:{n.get('estimated_hours', 1.0)}小时)"
            for n in nodes
        ])

        # 构建边信息字符串
        edges_str = "\n".join([
            f"- [{e['source']}] -> [{e['target']}] ({e.get('relation', '依赖')})"
            for e in edges
        ])

        # 构建系统提示词
        from app.engines.prompts.learning_plan_prompts import PLAN_STRUCTURE_PROMPT

        system_prompt = PLAN_STRUCTURE_PROMPT.format(
            graph_title=graph_title,
            graph_description=graph_description,
            total_nodes=len(nodes),
            all_nodes=nodes_str,
            edges_info=edges_str if edges_str else "（无明确依赖关系，请根据知识点自然顺序组织）",
            max_chapters=constraints.get("max_chapters", 12),
            max_sections_per_chapter=constraints.get("max_sections_per_chapter", 6)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据以上知识图谱，生成符合认知规律的章节结构学习计划。确保：\n1. 每个知识点都被分配到某个节中\n2. 遵循知识依赖关系\n3. 章节结构均衡合理\n4. 输出有效的JSON格式"}
        ]

        # 添加重试机制（最多重试3次）
        import re
        import asyncio
        max_retries = 3
        last_error = None
        
        async def send_progress_heartbeat():
            """发送进度心跳，让用户知道AI正在工作"""
            for i in range(5):  # 最多发送5次心跳
                await asyncio.sleep(3)  # 每3秒发送一次
                if progress_callback:
                    await progress_callback(25 + i * 3, f"AI正在分析知识点，请稍候...")
        
        for attempt in range(max_retries):
            try:
                # 报告进度：正在调用AI生成章节结构
                if progress_callback:
                    await progress_callback(20 + attempt * 15, f"正在请求AI生成章节结构（第{attempt + 1}/{max_retries}次尝试）...")
                
                # 发送中间进度，表示正在等待AI响应
                if progress_callback and attempt == 0:
                    await progress_callback(25, "AI正在分析知识图谱，这可能需要一些时间...")
                
                # 同时运行心跳和AI调用
                heartbeat_task = asyncio.create_task(send_progress_heartbeat())
                response = await self.chat(messages, temperature=0.7)
                heartbeat_task.cancel()  # 取消心跳任务
                
                # 报告进度：正在解析AI响应
                if progress_callback:
                    await progress_callback(60, "AI响应已收到，正在解析结果...")
                
                # 解析响应
                # 尝试从markdown代码块中提取JSON
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    result = json.loads(json_str)
                    if "chapters" in result and result["chapters"]:
                        print(f"[generate_plan_structure] 成功解析章节结构（第{attempt + 1}次尝试）")
                        if progress_callback:
                            await progress_callback(100, "章节结构生成完成！")
                        return result

                # 尝试直接解析
                result = json.loads(response)
                if "chapters" in result and result["chapters"]:
                    print(f"[generate_plan_structure] 成功解析章节结构（第{attempt + 1}次尝试）")
                    if progress_callback:
                        await progress_callback(100, "章节结构生成完成！")
                    return result

                # 如果解析失败但有响应，记录错误继续重试
                last_error = f"响应中无有效chapters数据，响应前200字符: {response[:200]}"
                print(f"[generate_plan_structure] 解析失败（第{attempt + 1}次尝试）: {last_error}")
                
            except json.JSONDecodeError as e:
                last_error = f"JSON解析错误: {e}"
                print(f"[generate_plan_structure] JSON解析错误（第{attempt + 1}次尝试）: {e}")
            except Exception as e:
                last_error = f"调用异常: {e}"
                print(f"[generate_plan_structure] 调用异常（第{attempt + 1}次尝试）: {e}")
        
        # 所有重试都失败，返回错误信息以便上层处理
        print(f"[generate_plan_structure] 所有重试均失败，最后错误: {last_error}")
        raise ValueError(f"生成学习计划章节结构失败: {last_error}")

    # ==================== 两阶段学习计划生成方法 ====================

    async def generate_chapters_structure(
        self,
        nodes: List[dict],
        edges: List[dict],
        constraints: dict,
        graph_title: str = "",
        graph_description: str = "",
        progress_callback=None
    ) -> dict:
        """
        第一阶段：生成章节结构（仅生成章-知识点分配）

        Args:
            nodes: 知识点节点列表
            edges: 知识点依赖边列表
            constraints: 约束条件（max_chapters, max_sections_per_chapter）
            graph_title: 图谱标题
            graph_description: 图谱描述
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            dict: 章节结构数据，包含chapters数组，每章包含knowledge_point_ids
        """
        # 构建节点列表字符串
        nodes_str = "\n".join([
            f"- [{n['id']}] {n['name']}: {n.get('description', '')} (难度:{n.get('difficulty', 'intermediate')}, 预计:{n.get('estimated_hours', 1.0)}小时)"
            for n in nodes
        ])

        # 构建边信息字符串
        edges_str = "\n".join([
            f"- [{e['source']}] -> [{e['target']}] ({e.get('relation', '依赖')})"
            for e in edges
        ])

        # 构建系统提示词（使用第一阶段提示词）
        from app.engines.prompts.learning_plan_prompts import PLAN_CHAPTERS_PROMPT
        system_prompt = PLAN_CHAPTERS_PROMPT.format(
            graph_title=graph_title,
            graph_description=graph_description,
            total_nodes=len(nodes),
            all_nodes=nodes_str,
            edges_info=edges_str if edges_str else "（无明确依赖关系，请根据知识点自然顺序组织）",
            max_chapters=constraints.get("max_chapters", 14)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据以上知识图谱，生成符合认知规律的章节结构。确保：\n1. 每个知识点都被分配到某个章节中\n2. 遵循知识依赖关系\n3. 章节结构均衡合理\n4. 输出有效的JSON格式（只包含chapters，每章只需knowledge_point_ids）"}
        ]

        # 添加重试机制（最多重试3次）
        import re
        import asyncio
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 报告进度：正在调用AI生成章节结构
                if progress_callback:
                    await progress_callback(10 + attempt * 5, f"【生成章】正在请求AI生成章节结构（第{attempt + 1}/{max_retries}次尝试）...")
                
                # 发送中间进度，表示正在等待AI响应
                if progress_callback and attempt == 0:
                    await progress_callback(15, "【生成章】AI正在分析知识图谱，这可能需要一些时间...")
                
                # 同时运行心跳和AI调用
                async def send_progress_heartbeat():
                    """发送进度心跳"""
                    for i in range(5):
                        await asyncio.sleep(3)
                        if progress_callback:
                            await progress_callback(20 + i * 2, f"【生成章】AI正在分析知识点，请稍候...")
                
                heartbeat_task = asyncio.create_task(send_progress_heartbeat())
                response = await self.chat(messages, temperature=0.7)
                heartbeat_task.cancel()
                
                # 报告进度：正在解析AI响应
                if progress_callback:
                    await progress_callback(40, "【生成章】AI响应已收到，正在解析结果...")
                
                # 解析响应
                # 尝试从markdown代码块中提取JSON
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    result = json.loads(json_str)
                    if "chapters" in result and result["chapters"]:
                        # 验证知识点覆盖率（超过85%即可）
                        chapters = result["chapters"]
                        assigned_count = sum(len(ch.get("knowledge_point_ids", [])) for ch in chapters)
                        coverage_rate = assigned_count / len(nodes) if len(nodes) > 0 else 0
                        if coverage_rate >= 0.85:
                            print(f"[generate_chapters_structure] 成功解析章节结构（第{attempt + 1}次尝试），知识点覆盖率: {coverage_rate*100:.1f}%")
                            if progress_callback:
                                await progress_callback(50, f"【生成章】章节结构生成完成！覆盖率{coverage_rate*100:.1f}%")
                            return result
                        else:
                            last_error = f"知识点分配不足：分配了{assigned_count}个，覆盖率{coverage_rate*100:.1f}%（需要≥85%）"
                            print(f"[generate_chapters_structure] 知识点覆盖率不足（第{attempt + 1}次尝试）: {last_error}")
                            continue
                # 尝试直接解析
                result = json.loads(response)
                if "chapters" in result and result["chapters"]:
                    chapters = result["chapters"]
                    assigned_count = sum(len(ch.get("knowledge_point_ids", [])) for ch in chapters)
                    coverage_rate = assigned_count / len(nodes) if len(nodes) > 0 else 0
                    print(f"[generate_chapters_structure] 成功解析章节结构（第{attempt + 1}次尝试），知识点覆盖率: {coverage_rate*100:.1f}%")
                    if progress_callback:
                        await progress_callback(50, f"【生成章】章节结构生成完成！覆盖率{coverage_rate*100:.1f}%")
                    return result

                # 如果解析失败但有响应，记录错误继续重试
                last_error = f"响应中无有效chapters数据，响应前200字符: {response[:200]}"
                print(f"[generate_chapters_structure] 解析失败（第{attempt + 1}次尝试）: {last_error}")
                
            except json.JSONDecodeError as e:
                last_error = f"JSON解析错误: {e}"
                print(f"[generate_chapters_structure] JSON解析错误（第{attempt + 1}次尝试）: {e}")
            except Exception as e:
                last_error = f"调用异常: {e}"
                print(f"[generate_chapters_structure] 调用异常（第{attempt + 1}次尝试）: {e}")
        
        # 所有重试都失败，返回错误信息以便上层处理
        print(f"[generate_chapters_structure] 所有重试均失败，最后错误: {last_error}")
        raise ValueError(f"生成章节结构失败: {last_error}")

    async def generate_sections_for_chapter(
        self,
        chapter_data: dict,
        nodes_map: dict,
        max_sections_per_chapter: int = 8,
        progress_callback=None
    ) -> dict:
        """
        第二阶段：为单个章节生成节结构

        Args:
            chapter_data: 章节数据，包含chapter_number, title, description, knowledge_point_ids
            nodes_map: 节点ID到节点详情的映射
            max_sections_per_chapter: 每章最大节数
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            dict: 包含sections数组的字典
        """
        import re
        import asyncio
        
        # 构建本章知识点详情字符串
        kp_ids = chapter_data.get("knowledge_point_ids", [])
        chapter_kps = []
        for kp_id in kp_ids:
            node = nodes_map.get(kp_id)
            if node:
                chapter_kps.append(f"- [{node['id']}] {node['name']}: {node.get('description', '')} (难度:{node.get('difficulty', 'intermediate')})")
        
        if not chapter_kps:
            # 如果没有找到知识点，返回默认节结构
            return {"sections": []}
        
        kp_str = "\n".join(chapter_kps)
        
        # 构建系统提示词
        from app.engines.prompts.learning_plan_prompts import PLAN_SECTIONS_FOR_CHAPTER_PROMPT
        system_prompt = PLAN_SECTIONS_FOR_CHAPTER_PROMPT.format(
            chapter_title=chapter_data.get("title", ""),
            chapter_number=chapter_data.get("chapter_number", 1),
            chapter_description=chapter_data.get("description", ""),
            chapter_knowledge_points=kp_str,
            max_sections_per_chapter=max_sections_per_chapter
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为第{chapter_data.get('chapter_number', 1)}章「{chapter_data.get('title', '')}」设计节结构。确保：\n1. 所有知识点都被分配到某个节中\n2. 节之间逻辑递进\n3. 输出有效的JSON格式"}
        ]

        # 添加重试机制（最多重试3次）
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = await self.chat(messages, temperature=0.7)
                
                # 解析响应
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    result = json.loads(json_str)
                    if "sections" in result and result["sections"]:
                        print(f"[generate_sections_for_chapter] 第{chapter_data.get('chapter_number', 1)}章节结构生成成功（第{attempt + 1}次尝试）")
                        return result

                # 尝试直接解析
                result = json.loads(response)
                if "sections" in result and result["sections"]:
                    print(f"[generate_sections_for_chapter] 第{chapter_data.get('chapter_number', 1)}章节结构生成成功（第{attempt + 1}次尝试）")
                    return result

                last_error = f"响应中无有效sections数据"
                print(f"[generate_sections_for_chapter] 第{chapter_data.get('chapter_number', 1)}章解析失败: {last_error}")
                
            except json.JSONDecodeError as e:
                last_error = f"JSON解析错误: {e}"
                print(f"[generate_sections_for_chapter] JSON解析错误: {e}")
            except Exception as e:
                last_error = f"调用异常: {e}"
                print(f"[generate_sections_for_chapter] 调用异常: {e}")
        
        # 如果所有重试都失败，返回默认节结构
        print(f"[generate_sections_for_chapter] 第{chapter_data.get('chapter_number', 1)}章所有重试均失败，返回默认节结构")
        # 创建默认节：每个知识点一个节
        default_sections = []
        for i, kp_id in enumerate(kp_ids[:max_sections_per_chapter]):
            node = nodes_map.get(kp_id)
            if node:
                default_sections.append({
                    "section_number": i + 1,
                    "title": node.get("name", f"节{i + 1}"),
                    "description": node.get("description", "")[:50],
                    "knowledge_point_ids": [kp_id],
                    "key_concepts": [node.get("name", "")],
                    "learning_objectives": [f"掌握{node.get('name', '')}"]
                })
        return {"sections": default_sections}

    async def generate_all_sections_parallel(
        self,
        chapters_data: List[dict],
        nodes_map: dict,
        max_sections_per_chapter: int = 8,
        progress_callback=None
    ) -> List[dict]:
        """
        并行生成所有章节的节结构

        Args:
            chapters_data: 章节列表（包含knowledge_point_ids）
            nodes_map: 节点ID到节点详情的映射
            max_sections_per_chapter: 每章最大节数
            progress_callback: 进度回调函数

        Returns:
            List[dict]: 更新后的章节列表（包含sections）
        """
        import asyncio
        from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError
        
        if progress_callback:
            await progress_callback(55, f"【生成节】开始为{len(chapters_data)}章并行生成节结构...")
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(5)
        
        async def generate_with_semaphore(chapter_data: dict, index: int) -> tuple:
            """带并发控制的生成函数"""
            async with semaphore:
                # 检查是否已取消
                await wait_if_cancelled()
                
                chapter_num = chapter_data.get("chapter_number", index + 1)
                if progress_callback:
                    await progress_callback(
                        55 + (index * 40 // len(chapters_data)),
                        f"【生成节】正在生成第{chapter_num}章的节结构..."
                    )
                
                sections_result = await self.generate_sections_for_chapter(
                    chapter_data=chapter_data,
                    nodes_map=nodes_map,
                    max_sections_per_chapter=max_sections_per_chapter
                )
                
                return (index, sections_result.get("sections", []))
        
        # 并行生成所有章节的节结构
        tasks = [
            generate_with_semaphore(chapter, i)
            for i, chapter in enumerate(chapters_data)
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except GenerationCancelledError:
            print("[generate_all_sections_parallel] 检测到取消请求")
            raise
        
        # 更新章节数据
        updated_chapters = list(chapters_data)
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                index, sections = result
                updated_chapters[index]["sections"] = sections
            else:
                print(f"[generate_all_sections_parallel] 生成失败: {result}")
        
        if progress_callback:
            await progress_callback(95, "【生成节】所有章节的节结构生成完成！")
        
        return updated_chapters

    async def generate_chapter_ppt_content(
        self,
        chapter_data: dict,
        prompt: str = None
    ) -> dict:
        """
        生成章节PPT内容

        Args:
            chapter_data: 章节数据
            prompt: 自定义提示词（可选）

        Returns:
            dict: PPT内容，包含slides数组
        """
        if not prompt:
            from app.engines.prompts.learning_plan_prompts import CHAPTER_PPT_PROMPT
            prompt = CHAPTER_PPT_PROMPT.format(
                chapter_title=chapter_data.get("title", ""),
                chapter_number=chapter_data.get("chapter_number", 1),
                chapter_description=chapter_data.get("description", ""),
                section_count=len(chapter_data.get("sections", [])),
                learning_objectives=", ".join(chapter_data.get("learning_objectives", [])),
                sections_detail="\n".join([
                    f"- 第{s['section_number']}节：{s['title']}"
                    for s in chapter_data.get("sections", [])
                ]),
                knowledge_points_detail=""
            )

        messages = [
            {"role": "system", "content": "你是一位专业的PPT设计师，请严格按照指定的JSON格式输出PPT内容。"},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat(messages, temperature=0.7)

        try:
            import re
            # 尝试从markdown代码块中提取JSON
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                result = json.loads(json_str)
                if "slides" in result:
                    return result

            # 尝试直接解析
            result = json.loads(response)
            if "slides" in result:
                return result

            return {"slides": [], "error": "解析失败"}

        except json.JSONDecodeError as e:
            print(f"[generate_chapter_ppt_content] JSON解析错误: {e}")
            return {"slides": [], "error": str(e)}

    async def generate_ppt_plan(
        self,
        plan_type: str,
        context: dict,
        progress_callback=None
    ) -> dict:
        """
        生成PPT结构规划（第一步：规划页数和每页类型/标题）

        Args:
            plan_type: "section" 或 "chapter"
            context: 包含节/章节基本信息的字典
            progress_callback: 进度回调函数

        Returns:
            dict: PPT结构规划，包含total_slides和slides_plan
        """
        import asyncio
        import re
        from app.services.cancel_manager import GenerationCancelledError
        
        if plan_type == "section":
            from app.engines.prompts.learning_plan_prompts import SECTION_PPT_PLAN_PROMPT
            
            # 构建知识点详情
            kp_detail = "\n".join([
                f"- {kp['name']}：{kp.get('description', '')}"
                for kp in context.get("knowledge_points", [])
            ])
            
            prompt = SECTION_PPT_PLAN_PROMPT.format(
                section_title=context.get("title", ""),
                chapter_title=context.get("chapter_title", ""),
                section_number=context.get("section_number", 1),
                key_concepts=", ".join(context.get("key_concepts", [])),
                learning_objectives=", ".join(context.get("learning_objectives", [])),
                knowledge_points_detail=kp_detail
            )
        else:  # chapter
            from app.engines.prompts.learning_plan_prompts import CHAPTER_PPT_PLAN_PROMPT
            
            sections_detail = "\n".join([
                f"- 第{s['section_number']}节：{s['title']}"
                for s in context.get("sections", [])
            ])
            
            prompt = CHAPTER_PPT_PLAN_PROMPT.format(
                chapter_title=context.get("title", ""),
                chapter_number=context.get("chapter_number", 1),
                chapter_description=context.get("description", ""),
                section_count=len(context.get("sections", [])),
                learning_objectives=", ".join(context.get("learning_objectives", [])),
                sections_detail=sections_detail
            )

        messages = [
            {"role": "system", "content": "你是一位专业的课程设计师，请严格按照指定的JSON格式输出PPT结构规划。只输出结构规划，不输出具体内容。"},
            {"role": "user", "content": prompt}
        ]

        # 重试机制
        max_retries = 2
        last_error = None
        
        # 方法开始时检查取消状态
        from app.services.cancel_manager import is_cancelled, GenerationCancelledError
        if is_cancelled():
            print("[generate_ppt_plan] 方法开始时检测到取消状态，取消生成")
            raise GenerationCancelledError("用户取消了生成")
        
        async def send_progress_heartbeat():
            """发送进度心跳，同时检查取消状态"""
            from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError
            # Ollama 超时是 180 秒，心跳间隔 1 秒，需要足够多的次数
            for i in range(200):  # 200 次心跳 = 200 秒
                await asyncio.sleep(1)
                if progress_callback:
                    await progress_callback(5 + i, f"AI正在规划PPT结构，请稍候...")
                # 检查是否已取消
                try:
                    await wait_if_cancelled()
                except GenerationCancelledError:
                    print(f"[generate_ppt_plan] 检测到取消请求")
                    raise
        
        for attempt in range(max_retries):
            try:
                if progress_callback:
                    await progress_callback(0, f"正在请求AI规划PPT结构（第{attempt + 1}/{max_retries}次尝试）...")
                
                # 同时运行心跳和AI调用
                heartbeat_task = asyncio.create_task(send_progress_heartbeat())
                ai_task = asyncio.create_task(self.chat(messages, temperature=0.7))
                
                # 等待任一任务完成（AI完成或检测到取消）
                done, pending = await asyncio.wait(
                    [ai_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 取消未完成的任务
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # 检查AI任务的结果
                if ai_task in done:
                    try:
                        response = ai_task.result()
                    except Exception as e:
                        # AI调用出错了（超时、网络错误等），不是取消
                        last_error = f"AI调用失败: {str(e)}"
                        print(f"[generate_ppt_plan] AI调用失败: {last_error}")
                        continue  # 重试
                else:
                    # heartbeat_task 完成了，检查是否因为取消
                    from app.services.cancel_manager import is_cancelled
                    if is_cancelled():
                        raise GenerationCancelledError("用户取消了生成")
                    else:
                        # 心跳正常完成但AI任务未完成，可能是超时
                        last_error = "AI调用超时"
                        print(f"[generate_ppt_plan] {last_error}")
                        continue  # 重试
                
                if progress_callback:
                    await progress_callback(25, "AI响应已收到，正在解析规划...")
                
                # 1. 尝试从markdown代码块中提取JSON
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    try:
                        result = json.loads(json_str)
                        if "slides_plan" in result and "total_slides" in result:
                            if progress_callback:
                                await progress_callback(30, f"规划完成，共{result['total_slides']}页")
                            return result
                    except json.JSONDecodeError:
                        pass
                
                # 2. 尝试直接解析
                result = json.loads(response)
                if "slides_plan" in result and "total_slides" in result:
                    if progress_callback:
                        await progress_callback(30, f"规划完成，共{result['total_slides']}页")
                    return result
                
                last_error = f"响应中无有效规划数据: {response[:200]}..."
                print(f"[generate_ppt_plan] 解析失败: {last_error}")
                
            except GenerationCancelledError:
                # 用户取消，抛出异常
                raise
            except Exception as e:
                last_error = str(e)
                print(f"[generate_ppt_plan] 调用异常: {e}")
        
        # 返回默认规划（如果AI生成失败）
        return {
            "total_slides": 10,
            "slides_plan": [
                {"index": i, "type": "content", "title": f"第{i+1}页", "key_points": ["待生成"]}
                for i in range(10)
            ]
        }

    async def generate_single_slide_content(
        self,
        slide_plan: dict,
        context: dict,
        previous_slides: list = None
    ) -> dict:
        """
        生成单页PPT内容（第二步：并行生成每页内容）

        Args:
            slide_plan: 单页规划（index, type, title, key_points）
            context: 完整上下文信息
            previous_slides: 前面已生成的幻灯片（用于保持一致性）

        Returns:
            dict: 单页完整内容
        """
        import re
        from app.services.cancel_manager import GenerationCancelledError
        
        from app.engines.prompts.learning_plan_prompts import SINGLE_SLIDE_CONTENT_PROMPT
        
        # 构建知识点详情
        if "knowledge_points" in context:
            kp_detail = "\n".join([
                f"- {kp['name']}：{kp.get('description', '')}"
                for kp in context.get("knowledge_points", [])
            ])
        else:
            kp_detail = context.get("knowledge_points_detail", "")
        
        # 构建前面页面的摘要（帮助保持一致性）
        prev_summary = ""
        if previous_slides and len(previous_slides) > 0:
            prev_titles = [s.get("title", "") for s in previous_slides[:5]]
            prev_summary = f"已生成的页面：{', '.join(prev_titles)}"
        
        prompt = SINGLE_SLIDE_CONTENT_PROMPT.format(
            slide_index=slide_plan.get("index", 0),
            total_slides=context.get("total_slides", 10),
            slide_type=slide_plan.get("type", "content"),
            slide_layout=slide_plan.get("layout", "focus"),
            slide_title=slide_plan.get("title", ""),
            key_points="、".join(slide_plan.get("key_points", [])),
            section_title=context.get("section_title", context.get("title", "")),
            chapter_title=context.get("chapter_title", ""),
            knowledge_points_detail=kp_detail
        )

        if prev_summary:
            prompt += f"\n\n【前面页面参考】\n{prev_summary}"

        messages = [
            {"role": "system", "content": "你是一位专业的教学课件设计师。请根据页面规划生成单页PPT的结构化内容。content字段必须是JSON对象而非纯文本字符串，严格按照幻灯片类型对应的格式输出。"},
            {"role": "user", "content": prompt}
        ]

        # 生成内容，最多重试2次（平衡速度和稳定性）
        max_retries = 2
        
        async def send_heartbeat():
            """发送进度心跳，同时检查取消状态"""
            from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError
            # Ollama 超时是 180 秒，心跳间隔 1 秒，需要足够多的次数
            for i in range(200):  # 200 次心跳 = 200 秒
                await asyncio.sleep(1)
                print(f"[generate_single_slide_content] 幻灯片 {slide_plan.get('index', 0)} 生成中... ({i+1}/200)")
                # 检查是否已取消
                try:
                    await wait_if_cancelled()
                except GenerationCancelledError:
                    print(f"[generate_single_slide_content] 幻灯片 {slide_plan.get('index', 0)} 检测到取消")
                    raise
        
        for attempt in range(max_retries + 1):
            try:
                # 同时运行心跳和AI调用
                heartbeat_task = asyncio.create_task(send_heartbeat())
                ai_task = asyncio.create_task(self.chat(messages, temperature=0.7))
                
                # 等待任一任务完成（AI完成或检测到取消）
                done, pending = await asyncio.wait(
                    [ai_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 取消未完成的任务
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # 检查AI任务的结果
                if ai_task in done:
                    try:
                        response = ai_task.result()
                    except Exception as e:
                        # AI调用出错了（超时、网络错误等），不是取消
                        print(f"[generate_single_slide_content] AI调用失败: {e}")
                        raise
                else:
                    # heartbeat_task 完成了，检查是否因为取消
                    from app.services.cancel_manager import is_cancelled
                    if is_cancelled():
                        raise GenerationCancelledError("用户取消了生成")
                    else:
                        # 心跳正常完成但AI任务未完成，可能是超时
                        raise Exception("AI调用超时")
                
                # 解析JSON响应
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    result = json.loads(json_str)
                    return result
                
                # 尝试直接解析
                result = json.loads(response)
                return result
                
            except GenerationCancelledError:
                # 用户取消，直接抛出异常
                print(f"[generate_single_slide_content] 幻灯片 {slide_plan.get('index', 0)} 被取消")
                raise
            except Exception as e:
                print(f"[generate_single_slide_content] 第{attempt + 1}次尝试失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # 减少等待时间
        
        # 返回默认内容
        return {
            "index": slide_plan.get("index", 0),
            "type": slide_plan.get("type", "content"),
            "title": slide_plan.get("title", ""),
            "content": f"【{slide_plan.get('title', '')}】\n\n" + "、".join(slide_plan.get("key_points", [])),
            "notes": ""
        }

    async def generate_batch_slides_content(
        self,
        slides_plan: list,
        context: dict,
        previous_slides: list = None
    ) -> list:
        """
        一次调用生成一批幻灯片内容（最多3页）

        Args:
            slides_plan: 一批幻灯片规划列表（最多3个）
            context: 完整上下文信息
            previous_slides: 前面已生成的幻灯片（用于保持一致性）

        Returns:
            list: 这批幻灯片的完整内容列表
        """
        import re
        from app.services.cancel_manager import GenerationCancelledError
        from app.engines.prompts.learning_plan_prompts import SINGLE_SLIDE_CONTENT_PROMPT
        
        # 构建知识点详情
        if "knowledge_points" in context:
            kp_detail = "\n".join([
                f"- {kp['name']}：{kp.get('description', '')}"
                for kp in context.get("knowledge_points", [])
            ])
        else:
            kp_detail = context.get("knowledge_points_detail", "")
        
        # 构建前面页面的摘要
        prev_summary = ""
        if previous_slides and len(previous_slides) > 0:
            prev_titles = [s.get("title", "") for s in previous_slides[:5]]
            prev_summary = f"已生成的页面：{', '.join(prev_titles)}"
        
        # 为批次中的每个幻灯片构建提示词
        slides_prompts = []
        for idx, slide_plan in enumerate(slides_plan):
            prompt = SINGLE_SLIDE_CONTENT_PROMPT.format(
                slide_index=slide_plan.get("index", 0),
                total_slides=context.get("total_slides", 10),
                slide_type=slide_plan.get("type", "content"),
                slide_layout=slide_plan.get("layout", "focus"),
                slide_title=slide_plan.get("title", ""),
                key_points="、".join(slide_plan.get("key_points", [])),
                section_title=context.get("section_title", context.get("title", "")),
                chapter_title=context.get("chapter_title", ""),
                knowledge_points_detail=kp_detail
            )
            slides_prompts.append(prompt)
        
        # 构建批次提示词（简化格式说明，避免嵌套JSON导致解析错误）
        batch_prompt = f"""请为以下{len(slides_plan)}页PPT生成完整内容。

{chr(10).join([f'第{idx+1}页：{prompt}' for idx, prompt in enumerate(slides_prompts)])}

请按以下格式返回JSON数组（不要包含```标记）：
[{"index":0,"type":"类型","title":"标题","content":CONTENT_JSON,"notes":"讲解稿"},...]

【各类型content格式】：

★ exercise类型（练习）- 必须包含questions数组：
content应该是: {"questions":[{"type":"choice","question":"题干","options":["A.","B.","C.","D."],"answer":"答案","analysis":"解析"}]}

★ 其他类型：
cover: {"title":"标题","subtitle":"副标题"}
intro: {"scene":"场景","question":"问题"}
concept: {"definition":"定义","key_attributes":[{"label":"属性","value":"值"}]}
content: {"main_idea":"核心","points":[{"title":"要点","detail":"说明"}]}
comparison: {"items":[{"name":"名称","features":["特点"],"example":"示例"}],"key_difference":"区别"}
example: {"case_title":"案例","background":"背景","steps":[{"label":"步骤","content":"内容"}]}
summary: {"key_takeaways":[{"point":"要点","keyword":"关键词"}]}
ending: {"message":"寄语","next_topic":"预告"}

【要求】：
1. content必须是JSON对象，不是字符串
2. exercise类型必须有questions数组，包含2-4道题
3. 抽象练习需转换为具体练习题
4. 直接输出JSON，不要```标记"""

        if prev_summary:
            batch_prompt += f"\n\n【前面页面参考】\n{prev_summary}"

        system_prompt = (
            "你是一位专业的教学课件设计师。请根据页面规划，生成每页的完整结构化内容。\n\n重要规则：\n"
            "1. content字段必须是JSON对象而非纯文本字符串\n"
            "2. 严格按照各幻灯片类型对应的格式输出\n"
            "3. exercise类型的content必须包含questions数组，每道题包含type、question、answer、analysis字段\n"
            "4. 当key_points是抽象活动（如'格局描述、功能判断'）时，将每个抽象活动转换为对应类型的练习题\n"
            "5. 所有文字必须简洁，避免冗长描述"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": batch_prompt}
        ]

        print(f"[generate_batch_slides_content] 批次开始：索引 {[s.get('index', 0) for s in slides_plan]}")

        # 生成内容，最多重试2次
        max_retries = 2
        
        async def send_heartbeat():
            """发送进度心跳，同时检查取消状态"""
            from app.services.cancel_manager import wait_if_cancelled, GenerationCancelledError
            for i in range(200):
                await asyncio.sleep(1)
                print(f"[generate_batch_slides_content] 批次 {[s.get('index', 0) for s in slides_plan]} 生成中... ({i+1}/200)")
                try:
                    await wait_if_cancelled()
                except GenerationCancelledError:
                    print(f"[generate_batch_slides_content] 批次检测到取消")
                    raise
        
        for attempt in range(max_retries + 1):
            try:
                heartbeat_task = asyncio.create_task(send_heartbeat())
                ai_task = asyncio.create_task(self.chat(messages, temperature=0.7))
                
                done, pending = await asyncio.wait(
                    [ai_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                if ai_task in done:
                    try:
                        response = ai_task.result()
                    except Exception as e:
                        print(f"[generate_batch_slides_content] AI调用失败: {e}")
                        raise
                else:
                    from app.services.cancel_manager import is_cancelled
                    if is_cancelled():
                        raise GenerationCancelledError("用户取消了生成")
                    else:
                        raise Exception("AI调用超时")
                
                # 解析JSON响应
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    results = json.loads(json_str)
                    if isinstance(results, list):
                        print(f"[generate_batch_slides_content] 批次成功：生成了 {len(results)} 页")
                        return results
                
                # 尝试直接解析
                results = json.loads(response)
                if isinstance(results, list):
                    print(f"[generate_batch_slides_content] 批次成功：生成了 {len(results)} 页")
                    return results
                
                raise Exception("响应格式不正确")
                
            except GenerationCancelledError:
                print(f"[generate_batch_slides_content] 批次被取消")
                raise
            except Exception as e:
                print(f"[generate_batch_slides_content] 第{attempt + 1}次尝试失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
        
        # 返回默认内容
        print(f"[generate_batch_slides_content] 批次失败，返回默认内容")
        default_slides = []
        for slide_plan in slides_plan:
            slide_type = slide_plan.get("type", "content")
            slide_title = slide_plan.get("title", "")
            key_points = slide_plan.get("key_points", [])
            
            # 为exercise类型生成结构化的默认questions
            if slide_type == "exercise":
                default_questions = []
                for idx, kp in enumerate(key_points[:3]):
                    # 根据key_points的类型生成不同的问题
                    if "判断" in kp or "选择" in kp:
                        default_questions.append({
                            "type": "choice",
                            "question": f"关于{slide_title}的练习题{idx + 1}",
                            "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
                            "answer": "A",
                            "analysis": "请参考相关知识点"
                        })
                    elif "填空" in kp:
                        default_questions.append({
                            "type": "blank",
                            "question": f"请填写：{kp}",
                            "answer": "答案",
                            "analysis": "请参考相关知识点"
                        })
                    else:
                        default_questions.append({
                            "type": "choice",
                            "question": f"{kp}（练习题{idx + 1}）",
                            "options": ["A. 正确", "B. 错误", "C. 不确定", "D. 以上都不对"],
                            "answer": "A",
                            "analysis": "请参考相关知识点"
                        })
                
                default_slides.append({
                    "index": slide_plan.get("index", 0),
                    "type": slide_type,
                    "title": slide_title,
                    "content": {"questions": default_questions} if default_questions else {"questions": []},
                    "notes": ""
                })
            else:
                # 其他类型保持原有格式
                default_slides.append({
                    "index": slide_plan.get("index", 0),
                    "type": slide_type,
                    "title": slide_title,
                    "content": f"【{slide_title}】\n\n" + "、".join(key_points),
                    "notes": ""
                })
        return default_slides

    async def generate_section_ppt_content(
        self,
        section_data: dict,
        prompt: str = None,
        progress_callback=None
    ) -> dict:
        """
        生成节PPT内容，支持重试机制和增强的JSON解析

        Args:
            section_data: 节数据
            prompt: 自定义提示词（可选）
            progress_callback: 进度回调函数 callback(progress: int, message: str)

        Returns:
            dict: PPT内容，包含slides数组
        """
        import asyncio
        
        if not prompt:
            from app.engines.prompts.learning_plan_prompts import SECTION_PPT_PROMPT

            # 构建知识点详情
            kp_detail = "\n".join([
                f"- {kp['name']}：{kp.get('description', '')}"
                for kp in section_data.get("knowledge_points", [])
            ])

            prompt = SECTION_PPT_PROMPT.format(
                section_title=section_data.get("title", ""),
                chapter_title=section_data.get("chapter_title", ""),
                section_number=section_data.get("section_number", 1),
                key_concepts=", ".join(section_data.get("key_concepts", [])),
                learning_objectives=", ".join(section_data.get("learning_objectives", [])),
                knowledge_points_detail=kp_detail
            )

        messages = [
            {"role": "system", "content": "你是一位专业的教学内容设计师，请严格按照指定的JSON格式输出PPT内容。输出格式必须是: ```json\\n{\"slides\":[...]}\\n```"},
            {"role": "user", "content": prompt}
        ]

        # 重试机制
        max_retries = 2
        last_error = None
        
        async def send_progress_heartbeat():
            """发送进度心跳"""
            for i in range(8):  # 最多发送8次心跳（约24秒）
                await asyncio.sleep(3)
                if progress_callback:
                    await progress_callback(15 + i * 5, f"AI正在生成PPT内容，请稍候...")
        
        for attempt in range(max_retries):
            try:
                if progress_callback:
                    await progress_callback(10, f"正在请求AI生成PPT内容（第{attempt + 1}/{max_retries}次尝试）...")
                
                # 同时运行心跳和AI调用
                heartbeat_task = asyncio.create_task(send_progress_heartbeat())
                response = await self.chat(messages, temperature=0.7)
                heartbeat_task.cancel()  # 取消心跳任务
                
                if progress_callback:
                    await progress_callback(60, "AI响应已收到，正在解析PPT内容...")
                
                # 增强的JSON解析逻辑
                import re
                
                # 1. 尝试从markdown代码块中提取JSON
                match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    try:
                        result = json.loads(json_str)
                        if "slides" in result and isinstance(result["slides"], list):
                            if progress_callback:
                                await progress_callback(100, "PPT内容生成成功！")
                            return result
                    except json.JSONDecodeError:
                        # 尝试修复常见的JSON错误
                        fixed_json = self._fix_json_string(json_str)
                        try:
                            result = json.loads(fixed_json)
                            if "slides" in result and isinstance(result["slides"], list):
                                return result
                        except json.JSONDecodeError:
                            pass
                
                # 2. 尝试直接解析响应
                try:
                    result = json.loads(response)
                    if "slides" in result and isinstance(result["slides"], list):
                        if progress_callback:
                            await progress_callback(100, "PPT内容生成成功！")
                        return result
                except json.JSONDecodeError:
                    pass
                
                # 3. 尝试提取任何包含slides数组的内容
                match = re.search(r'\{[\s\S]*?"slides"\s*:\s*\[[\s\S]*?\]\s*\}', response)
                if match:
                    try:
                        result = json.loads(match.group(0))
                        if "slides" in result and isinstance(result["slides"], list):
                            if progress_callback:
                                await progress_callback(100, "PPT内容生成成功！")
                            return result
                    except json.JSONDecodeError:
                        pass
                
                # 4. 尝试修复并解析（处理常见的AI输出问题）
                cleaned = re.sub(r'```json\s*', '', response)
                cleaned = re.sub(r'```\s*$', '', cleaned)
                cleaned = cleaned.strip()
                
                # 处理没有用引号包裹的键名
                cleaned = re.sub(r'(\w+):', r'"\1":', cleaned)
                # 处理单引号
                cleaned = cleaned.replace("'", '"')
                
                try:
                    result = json.loads(cleaned)
                    if "slides" in result and isinstance(result["slides"], list):
                        if progress_callback:
                            await progress_callback(100, "PPT内容生成成功！")
                        return result
                except json.JSONDecodeError:
                    pass
                
                # 所有解析方法都失败
                last_error = f"无法解析AI响应为有效JSON: {response[:200]}..."
                print(f"[generate_section_ppt_content] 解析尝试 {attempt + 1}/{max_retries} 失败: {last_error}")
                
            except Exception as e:
                last_error = str(e)
                print(f"[generate_section_ppt_content] AI调用错误 {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # 等待后重试
                    # 在重试时简化提示词，降低生成难度
                    if attempt == 0:
                        messages[1]["content"] = prompt[:2000]  # 截断过长内容
        
        # 返回部分内容而不是空数组，便于调试
        return {"slides": [], "error": last_error or "解析失败"}
    
    def _fix_json_string(self, json_str: str) -> str:
        """修复常见的JSON格式错误"""
        import re
        
        # 移除尾部逗号
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 移除注释
        json_str = re.sub(r'//.*?\n', '', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # 修复没有引号的键
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        
        # 修复单引号为双引号（不在转义字符串中）
        result = []
        in_string = False
        for i, char in enumerate(json_str):
            if char == '"' and (i == 0 or json_str[i-1] != '\\'):
                in_string = not in_string
            if char == "'" and not in_string:
                result.append('"')
            else:
                result.append(char)
        json_str = ''.join(result)
        
        return json_str
