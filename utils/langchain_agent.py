# -*- coding: utf-8 -*-
"""
LangChain 集成模块
提供基于 LangChain 的 AI Agent 功能，支持：
- OpenAI 兼容 API（如 DeepSeek）
- 对话记忆管理
- 结构化提示模板
- 文档处理和检索
- RAG (Retrieval-Augmented Generation) 知识库检索
"""

import logging
from typing import List, Dict, Any, Optional
import json

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    import_error = str(e)

logger = logging.getLogger("langchain_agent")


class LangChainAgent:
    """
    使用 LangChain 框架的 AI Agent
    支持 OpenAI 兼容的 API（如 DeepSeek）
    支持 RAG 知识库检索增强
    """
    
    # 配置常量
    MAX_CONVERSATION_HISTORY = 10  # 保留的最大对话轮数

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        timeout: int = 120,
        enable_memory: bool = False,
        enable_rag: bool = False,
        rag_kb = None,
    ):
        """
        初始化 LangChain Agent

        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            model: 模型名称
            temperature: 温度参数
            timeout: 超时时间（秒）
            enable_memory: 是否启用对话记忆
            enable_rag: 是否启用 RAG 知识库检索
            rag_kb: RAG 知识库实例（可选）
        """
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.enable_memory = enable_memory
        self.enable_rag = enable_rag
        self.rag_kb = rag_kb
        self.available = LANGCHAIN_AVAILABLE and bool(api_key)
        self.conversation_history: List[Any] = []  # Simple list-based memory

        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain 未安装，将使用降级模式")
            return

        if not api_key:
            logger.warning("未配置 API Key，LangChain Agent 不可用")
            return

        try:
            # 初始化 LLM (注意: max_tokens 需要在每次调用时设置)
            self.llm = ChatOpenAI(
                openai_api_key=api_key,
                openai_api_base=api_base,
                model_name=model,
                temperature=temperature,
                timeout=timeout,
            )

            logger.info(f"LangChain Agent 初始化成功: {model}")
            
            # 检查 RAG 是否可用
            if self.enable_rag:
                if self.rag_kb and hasattr(self.rag_kb, 'available') and self.rag_kb.available:
                    logger.info("✅ RAG 知识库已启用")
                else:
                    logger.warning("RAG 已启用但知识库不可用")
                    self.enable_rag = False
                    
        except Exception as e:
            logger.error(f"LangChain Agent 初始化失败: {e}")
            self.available = False

    def call(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_tokens: int = 800,
        temperature: Optional[float] = None,
        use_rag: bool = True,
    ) -> str:
        """
        调用 AI 模型生成响应（支持 RAG 知识库检索）

        Args:
            prompt: 用户提示
            system_message: 系统消息（可选）
            max_tokens: 最大 token 数
            temperature: 温度参数（可选，覆盖初始化时的默认值）
            use_rag: 是否使用 RAG 检索（默认 True，仅在启用 RAG 时生效）

        Returns:
            AI 响应文本
        """
        if not self.available:
            return self._fallback_response(prompt)

        try:
            messages = []
            
            # 如果启用了记忆但没有提供系统消息，添加默认系统消息告知 AI 具有记忆能力
            if self.enable_memory and not system_message:
                system_message = (
                    "你是一个智能助手，具有对话记忆能力。"
                    "你可以记住并引用之前的对话内容。"
                    "当用户提到'之前'、'刚才'、'上次'等词语时，请回顾对话历史并给出相应回答。"
                )
            
            # RAG 知识库检索增强
            if self.enable_rag and use_rag and self.rag_kb:
                try:
                    rag_context = self.rag_kb.get_context_for_query(prompt, k=3)
                    if rag_context:
                        logger.info(f"✅ RAG 检索到相关知识")
                        # 将检索到的知识库内容添加到系统消息
                        rag_system_msg = f"\n\n[知识库参考资料]\n{rag_context}\n\n请基于以上参考资料回答用户的问题。如果参考资料不相关，可以根据你的知识回答。"
                        if system_message:
                            system_message += rag_system_msg
                        else:
                            system_message = "你是一个智能助手。" + rag_system_msg
                except Exception as e:
                    logger.warning(f"RAG 检索失败: {e}")
            
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            # 如果启用了记忆，添加历史对话
            if self.enable_memory and self.conversation_history:
                messages.extend(self.conversation_history[-self.MAX_CONVERSATION_HISTORY:])  # 保留最近N条
            
            messages.append(HumanMessage(content=prompt))

            # 使用 max_tokens 和 temperature 参数配置 LLM
            bind_params = {"max_tokens": max_tokens}
            if temperature is not None:
                bind_params["temperature"] = temperature
            llm_with_config = self.llm.bind(**bind_params)
            response = llm_with_config.invoke(messages)
            result = response.content

            # 保存对话到记忆
            if self.enable_memory:
                self.conversation_history.append(HumanMessage(content=prompt))
                self.conversation_history.append(AIMessage(content=result))

            return result

        except Exception as e:
            logger.error(f"LangChain Agent 调用失败: {e}")
            return self._fallback_response(prompt)

    def call_with_template(
        self,
        template: str,
        input_variables: Dict[str, Any],
        system_message: Optional[str] = None,
    ) -> str:
        """
        使用提示模板调用 AI 模型

        Args:
            template: 提示模板（支持 {variable} 格式）
            input_variables: 模板变量字典
            system_message: 系统消息（可选）

        Returns:
            AI 响应文本
        """
        if not self.available:
            return self._fallback_response(template)

        try:
            # 构建提示模板
            messages = []
            if system_message:
                messages.append(("system", system_message))
            messages.append(("human", template))

            prompt_template = ChatPromptTemplate.from_messages(messages)
            
            # 使用 LCEL (LangChain Expression Language) 创建链
            chain = prompt_template | self.llm | StrOutputParser()
            
            # 调用链
            response = chain.invoke(input_variables)
            return response

        except Exception as e:
            logger.error(f"LangChain 模板调用失败: {e}")
            return self._fallback_response(template)

    def recommend_projects(
        self,
        interests: List[str],
        skills: List[str],
        target_role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        使用 LangChain 推荐项目

        Args:
            interests: 兴趣列表
            skills: 技能列表
            target_role: 目标职业（可选）

        Returns:
            项目推荐列表
        """
        system_msg = """你是一个专业的学习路径规划助手。
请根据用户的兴趣、技能和目标职业，推荐合适的学习项目。
返回 JSON 格式的项目列表，每个项目包含：name, url, description, learning_value, difficulty, estimated_time, tech_stack。
difficulty 应该是 easy/medium/hard 之一。
estimated_time 是预计学习时间（周）。"""

        prompt = f"""用户信息：
- 兴趣：{', '.join(interests) if interests else '未指定'}
- 技能：{', '.join(skills) if skills else '未指定'}
- 目标职业：{target_role or '未指定'}

请推荐 3-5 个适合的 GitHub 开源项目供学习，注重实用性和学习价值。
返回格式：纯 JSON 数组，无其他文本。"""

        response = self.call(prompt, system_message=system_msg)

        # 尝试解析 JSON
        try:
            # 提取 JSON 部分（寻找第一个完整的 JSON 数组）
            json_start = response.find('[')
            if json_start >= 0:
                # 简单的括号匹配计数
                bracket_count = 0
                json_end = -1
                for i, char in enumerate(response[json_start:], start=json_start):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > json_start:
                    json_str = response[json_start:json_end]
                    projects = json.loads(json_str)
                    return projects
            
            logger.warning("无法从响应中提取 JSON")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return []

    def generate_learning_path(
        self,
        target_role: str,
        current_skills: List[str],
        timeframe: str = "6个月",
    ) -> str:
        """
        生成学习路径

        Args:
            target_role: 目标职业
            current_skills: 当前技能
            timeframe: 时间框架

        Returns:
            学习路径文本
        """
        system_msg = """你是一个专业的职业规划和学习路径设计专家。
请根据目标职业、当前技能和时间框架，制定详细的学习路径。
路径应该包括：
1. 技能差距分析
2. 分阶段学习计划（基础、进阶、实战）
3. 推荐学习资源
4. 实践项目建议"""

        prompt = f"""请为以下情况制定学习路径：
- 目标职业：{target_role}
- 当前技能：{', '.join(current_skills) if current_skills else '无'}
- 时间框架：{timeframe}

请提供结构化的学习路径规划。"""

        return self.call(prompt, system_message=system_msg)

    def analyze_career_fit(
        self,
        interests: List[str],
        skills: List[str],
        location: str = "全国",
    ) -> str:
        """
        分析职业匹配度

        Args:
            interests: 兴趣列表
            skills: 技能列表
            location: 工作地点

        Returns:
            职业分析文本
        """
        system_msg = """你是一个职业规划顾问。
请根据用户的兴趣和技能，分析适合的职业方向。
考虑：
1. 兴趣与职业的匹配度
2. 技能与职业要求的契合度
3. 职业发展前景
4. 地区就业机会"""

        prompt = f"""用户资料：
- 兴趣：{', '.join(interests) if interests else '未指定'}
- 技能：{', '.join(skills) if skills else '未指定'}
- 期望地区：{location}

请分析适合的职业方向，并给出理由。"""

        return self.call(prompt, system_message=system_msg)

    def clear_memory(self):
        """清除对话记忆"""
        if self.enable_memory:
            self.conversation_history = []
            logger.info("对话记忆已清除")

    def _fallback_response(self, prompt: str) -> str:
        """
        降级响应（当 LangChain 不可用时）

        Args:
            prompt: 原始提示

        Returns:
            默认响应
        """
        if "推荐" in prompt and "项目" in prompt:
            return """```json
[
  {
    "name": "Vue 3",
    "url": "https://github.com/vuejs/core",
    "description": "易学易用的渐进式 JavaScript 框架",
    "learning_value": "学习现代前端架构与响应式原理",
    "difficulty": "medium",
    "estimated_time": "8",
    "tech_stack": ["TypeScript", "Vue"]
  }
]
```"""
        if "职业" in prompt:
            return "【本地回退】请配置 API Key 以使用 LangChain AI 功能。建议职业：全栈开发、数据分析、AI工程师"
        if "学习路径" in prompt:
            return "【本地回退】请配置 API Key 以使用 LangChain AI 功能。建议分阶段学习：基础-进阶-实战"
        return "【本地回退】LangChain 功能不可用，请配置 API Key 或检查 LangChain 安装。"


# 全局单例实例
_langchain_agent_instance: Optional[LangChainAgent] = None


def get_langchain_agent(enable_memory: bool = True, enable_rag: bool = False) -> LangChainAgent:
    """
    获取 LangChain Agent 单例实例
    
    Args:
        enable_memory: 是否启用对话记忆
        enable_rag: 是否启用 RAG 知识库检索
        
    Returns:
        LangChainAgent 实例
    """
    global _langchain_agent_instance
    
    import os
    import streamlit as st
    
    # 获取 API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        except Exception:
            pass
    
    # 获取 RAG 知识库
    rag_kb = None
    if enable_rag:
        try:
            from utils.rag_knowledge_base import get_rag_knowledge_base
            rag_kb = get_rag_knowledge_base()
        except Exception as e:
            logger.warning(f"无法加载 RAG 知识库: {e}")
    
    if _langchain_agent_instance is None or _langchain_agent_instance.enable_memory != enable_memory:
        _langchain_agent_instance = LangChainAgent(
            api_key=api_key,
            enable_memory=enable_memory,
            enable_rag=enable_rag,
            rag_kb=rag_kb,
        )
    
    return _langchain_agent_instance
