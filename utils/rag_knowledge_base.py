# -*- coding: utf-8 -*-
"""
utils/rag_knowledge_base.py

RAG (Retrieval-Augmented Generation) 知识库实现
使用 Chroma 向量数据库 + sentence-transformers 本地嵌入模型
支持持久化存储和语义检索
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入依赖
try:
    # 使用新的推荐导入路径
    try:
        from langchain_chroma import Chroma
    except ImportError:
        # 回退到旧版本
        from langchain_community.vectorstores import Chroma
    
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        # 回退到旧版本
        from langchain_community.embeddings import HuggingFaceEmbeddings
    
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG 依赖未安装: {e}")
    RAG_AVAILABLE = False
    Chroma = None
    HuggingFaceEmbeddings = None
    RecursiveCharacterTextSplitter = None
    Document = None


class RAGKnowledgeBase:
    """
    RAG 知识库管理器
    
    功能：
    1. 从 JSON 知识库加载数据并向量化
    2. 提供语义检索接口
    3. 支持持久化存储到本地
    4. 自动更新和增量索引
    """
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "infosynapse_kb",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化 RAG 知识库
        
        Args:
            persist_directory: 持久化存储路径
            collection_name: 集合名称
            embedding_model: 嵌入模型（支持中文的多语言模型）
            chunk_size: 文本分块大小
            chunk_overlap: 分块重叠大小
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if not RAG_AVAILABLE:
            logger.warning("RAG 功能不可用，请安装依赖: pip install chromadb sentence-transformers")
            self.available = False
            self.vectorstore = None
            self.embeddings = None
            return
        
        try:
            # 初始化嵌入模型（本地模型，无需API Key）
            logger.info(f"正在加载嵌入模型: {embedding_model}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={'device': 'cpu'},  # 使用 CPU，可改为 'cuda'
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # 初始化文本分割器
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]
            )
            
            # 确保持久化目录存在
            os.makedirs(persist_directory, exist_ok=True)
            
            # 加载或创建向量存储
            if os.path.exists(os.path.join(persist_directory, "chroma.sqlite3")):
                logger.info(f"加载现有向量数据库: {persist_directory}")
                self.vectorstore = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=persist_directory
                )
            else:
                logger.info(f"创建新向量数据库: {persist_directory}")
                self.vectorstore = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=persist_directory
                )
            
            self.available = True
            logger.info("✅ RAG 知识库初始化成功")
            
        except Exception as e:
            logger.error(f"RAG 知识库初始化失败: {e}")
            self.available = False
            self.vectorstore = None
            self.embeddings = None
    
    def load_from_json(self, kb_path: str) -> int:
        """
        从 JSON 知识库文件加载数据并向量化
        
        Args:
            kb_path: 知识库 JSON 文件路径
            
        Returns:
            加载的文档数量
        """
        if not self.available:
            logger.warning("RAG 功能不可用，跳过加载")
            return 0
        
        try:
            with open(kb_path, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
            return self.load_from_dict(kb_data)
        except Exception as e:
            logger.error(f"从 JSON 加载知识库失败: {e}")
            return 0
    
    def load_from_dict(self, kb_data: Dict[str, Any]) -> int:
        """
        从知识库字典加载数据并向量化（支持数据库或JSON来源）
        
        Args:
            kb_data: 知识库数据字典
            
        Returns:
            加载的文档数量
        """
        if not self.available:
            logger.warning("RAG 功能不可用，跳过加载")
            return 0
        
        try:
            documents = []
            
            # 1. 加载课程信息
            for major, courses in kb_data.get('courses', {}).items():
                for course in courses:
                    content = f"专业：{major}\n"
                    content += f"课程：{course.get('name', '')}\n"
                    content += f"描述：{course.get('description', '')}\n"
                    content += f"难度：{course.get('difficulty', '')}\n"
                    
                    # 添加评价
                    reviews = course.get('reviews', [])
                    if reviews:
                        content += "学生评价：\n"
                        for review in reviews[:3]:  # 只取前3条评价
                            content += f"- {review.get('text', '')}\n"
                    
                    metadata = {
                        'type': 'course',
                        'major': major,
                        'name': course.get('name', ''),
                        'difficulty': course.get('difficulty', ''),
                        'credits': course.get('credits', 0)
                    }
                    
                    documents.append(Document(page_content=content, metadata=metadata))
            
            # 2. 加载导师信息
            for advisor in kb_data.get('advisors', []):
                content = f"导师：{advisor.get('name', '')}\n"
                # 支持多种字段名称（兼容不同数据源）
                research = advisor.get('research', '') or advisor.get('research_area', '')
                content += f"研究方向：{research}\n"
                department = advisor.get('department', '') or advisor.get('major', '')
                content += f"院系：{department}\n"
                homepage = advisor.get('homepage', '')
                if homepage:
                    content += f"主页：{homepage}\n"
                bio = advisor.get('bio', '')
                if bio:
                    content += f"简介：{bio}\n"
                # 添加国家项目信息
                if advisor.get('national_projects'):
                    content += "参与国家项目：是\n"
                    projects_info = advisor.get('national_projects_info', '')
                    if projects_info:
                        content += f"项目信息：{projects_info}\n"
                
                # 添加评价
                reviews = advisor.get('reviews', [])
                if reviews:
                    content += "学生评价：\n"
                    for review in reviews[:3]:
                        content += f"- {review.get('text', '')}\n"
                
                metadata = {
                    'type': 'advisor',
                    'name': advisor.get('name', ''),
                    'research_area': research,
                    'department': department
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
            
            # 3. 加载实践资源
            for practice in kb_data.get('practice', []):
                # 支持多种字段名称（兼容不同数据源）
                title = practice.get('name', '') or practice.get('title', '')
                content = f"实践项目：{title}\n"
                content += f"类型：{practice.get('type', '')}\n"
                desc = practice.get('desc', '') or practice.get('description', '')
                content += f"描述：{desc}\n"
                skills = practice.get('skills', [])
                if skills:
                    content += f"技能要求：{', '.join(skills)}\n"
                link = practice.get('link', '')
                if link:
                    content += f"链接：{link}\n"
                
                metadata = {
                    'type': 'practice',
                    'title': title,
                    'practice_type': practice.get('type', ''),
                    'difficulty': practice.get('difficulty', '')
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
            
            # 4. 加载职位描述
            for jd in kb_data.get('jds', []):
                # 支持多种字段名称（兼容不同数据源）
                title = jd.get('position', '') or jd.get('title', '')
                content = f"职位：{title}\n"
                content += f"公司：{jd.get('company', '')}\n"
                jd_desc = jd.get('jd', '') or jd.get('requirements', '')
                content += f"要求：{jd_desc}\n"
                responsibilities = jd.get('responsibilities', '')
                if responsibilities:
                    content += f"职责：{responsibilities}\n"
                skills = jd.get('skills', [])
                if skills:
                    content += f"技能要求：{', '.join(skills)}\n"
                link = jd.get('link', '')
                if link:
                    content += f"链接：{link}\n"
                
                metadata = {
                    'type': 'job',
                    'title': title,
                    'company': jd.get('company', ''),
                    'location': jd.get('location', '')
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
            
            # 5. 加载校友经验
            for alumni in kb_data.get('alumni', []):
                content = f"校友：{alumni.get('name', '')}\n"
                content += f"专业：{alumni.get('major', '')}\n"
                content += f"毕业年份：{alumni.get('graduation_year', '')}\n"
                content += f"当前职位：{alumni.get('current_position', '')}\n"
                content += f"经验分享：{alumni.get('experience', '')}\n"
                
                metadata = {
                    'type': 'alumni',
                    'name': alumni.get('name', ''),
                    'major': alumni.get('major', ''),
                    'company': alumni.get('company', '')
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
            
            # 分块处理长文档
            split_docs = []
            for doc in documents:
                if len(doc.page_content) > self.chunk_size:
                    chunks = self.text_splitter.split_documents([doc])
                    split_docs.extend(chunks)
                else:
                    split_docs.append(doc)
            
            # 添加到向量存储
            if split_docs:
                logger.info(f"正在向量化 {len(split_docs)} 个文档...")
                self.vectorstore.add_documents(split_docs)
                # persist() 在 Chroma 0.4.x+ 中已自动处理，无需手动调用
                logger.info(f"✅ 成功加载并向量化 {len(split_docs)} 个文档")
                return len(split_docs)
            else:
                logger.warning("没有找到可加载的文档")
                return 0
                
        except Exception as e:
            logger.error(f"从 JSON 加载知识库失败: {e}")
            return 0
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        语义检索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 元数据过滤条件，例如 {'type': 'course'}
            
        Returns:
            检索结果列表，每个结果包含 content, metadata, score
        """
        if not self.available or not self.vectorstore:
            logger.warning("RAG 功能不可用")
            return []
        
        try:
            # 使用相似度搜索
            if filter_dict:
                results = self.vectorstore.similarity_search_with_score(
                    query, k=k, filter=filter_dict
                )
            else:
                results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            # 格式化结果
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': float(score)
                })
            
            logger.info(f"检索到 {len(formatted_results)} 个相关文档")
            return formatted_results
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def get_context_for_query(self, query: str, k: int = 3) -> str:
        """
        获取查询的上下文文本（用于 RAG）
        
        Args:
            query: 查询文本
            k: 检索文档数量
            
        Returns:
            合并的上下文文本
        """
        results = self.search(query, k=k)
        
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[参考资料 {i}]\n{result['content']}\n")
        
        return "\n".join(context_parts)
    
    def clear(self):
        """清空向量数据库"""
        if not self.available:
            return
        
        try:
            # 删除集合
            self.vectorstore.delete_collection()
            
            # 重新创建
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            logger.info("✅ 向量数据库已清空")
        except Exception as e:
            logger.error(f"清空向量数据库失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if not self.available or not self.vectorstore:
            return {'available': False}
        
        try:
            # 获取集合中的文档数量
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                'available': True,
                'total_documents': count,
                'persist_directory': self.persist_directory,
                'collection_name': self.collection_name,
                'embedding_model': self.embeddings.model_name if self.embeddings else None
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'available': False, 'error': str(e)}


# 全局单例实例
_rag_kb_instance: Optional[RAGKnowledgeBase] = None


def get_rag_knowledge_base() -> RAGKnowledgeBase:
    """获取 RAG 知识库单例实例"""
    global _rag_kb_instance
    if _rag_kb_instance is None:
        _rag_kb_instance = RAGKnowledgeBase()
    return _rag_kb_instance


def init_rag_from_json(kb_path: str = "./data/hdu_knowledge_base.json") -> int:
    """
    从 JSON 文件初始化 RAG 知识库
    
    Args:
        kb_path: 知识库 JSON 文件路径
        
    Returns:
        加载的文档数量
    """
    rag_kb = get_rag_knowledge_base()
    return rag_kb.load_from_json(kb_path)
