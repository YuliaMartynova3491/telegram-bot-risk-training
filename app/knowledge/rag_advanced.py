import json
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import KNOWLEDGE_DIR, LLM_MODEL_PATH

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Результат поиска в векторной базе."""
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str

@dataclass
class RAGResponse:
    """Ответ RAG-системы."""
    answer: str
    sources: List[SearchResult]
    confidence: float
    context_used: str

class EnhancedRAGSystem:
    """Улучшенная RAG-система с векторным поиском."""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """Инициализация RAG-системы."""
        self.model_name = model_name
        self.embedding_model = None
        self.vector_store = None
        self.documents = []
        self.document_embeddings = None
        self.is_initialized = False
        
        # Пути к файлам
        self.knowledge_base_path = KNOWLEDGE_DIR / "jsonl" / "risk_knowledge.jsonl"
        self.embeddings_cache_path = KNOWLEDGE_DIR / "embeddings_cache.npy"
        self.documents_cache_path = KNOWLEDGE_DIR / "documents_cache.json"
        
    async def initialize(self) -> bool:
        """Инициализация RAG-системы."""
        try:
            logger.info("Инициализация улучшенной RAG-системы...")
            
            # Загрузка модели эмбеддингов
            await self._load_embedding_model()
            
            # Загрузка документов
            await self._load_documents()
            
            # Создание векторного индекса
            await self._create_vector_index()
            
            self.is_initialized = True
            logger.info("RAG-система успешно инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации RAG-системы: {e}")
            return False
    
    async def _load_embedding_model(self):
        """Загрузка модели эмбеддингов."""
        try:
            logger.info(f"Загрузка модели эмбеддингов: {self.model_name}")
            
            # Загружаем модель в отдельном потоке, чтобы не блокировать
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(self.model_name)
            )
            
            logger.info("Модель эмбеддингов загружена")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки модели эмбеддингов: {e}")
            raise
    
    async def _load_documents(self):
        """Загрузка и обработка документов."""
        try:
            logger.info("Загрузка документов из базы знаний...")
            
            # Проверяем кэш документов
            if self.documents_cache_path.exists():
                logger.info("Загрузка документов из кэша...")
                with open(self.documents_cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    self.documents = [Document(**doc) for doc in cached_data]
            else:
                # Загружаем из исходных файлов
                await self._process_knowledge_base()
                
                # Сохраняем в кэш
                cache_data = [
                    {
                        "page_content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in self.documents
                ]
                with open(self.documents_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Загружено {len(self.documents)} документов")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки документов: {e}")
            raise
    
    async def _process_knowledge_base(self):
        """Обработка базы знаний в документы."""
        documents = []
        
        # Загружаем базовую базу знаний
        if self.knowledge_base_path.exists():
            with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            item = json.loads(line)
                            
                            # Создаем основной документ из вопроса и ответа
                            content = f"Вопрос: {item['prompt']}\nОтвет: {item['response']}"
                            metadata = item.get('metadata', {})
                            metadata.update({
                                'source': 'knowledge_base',
                                'line_number': line_num,
                                'type': 'qa_pair'
                            })
                            
                            documents.append(Document(
                                page_content=content,
                                metadata=metadata
                            ))
                            
                            # Создаем отдельные документы для вопроса и ответа
                            # Это поможет при поиске
                            question_doc = Document(
                                page_content=item['prompt'],
                                metadata={**metadata, 'type': 'question'}
                            )
                            documents.append(question_doc)
                            
                            answer_doc = Document(
                                page_content=item['response'],
                                metadata={**metadata, 'type': 'answer'}
                            )
                            documents.append(answer_doc)
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Ошибка парсинга JSON в строке {line_num}: {e}")
        
        # Разбиваем длинные документы на чанки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        self.documents = text_splitter.split_documents(documents)
    
    async def _create_vector_index(self):
        """Создание векторного индекса FAISS."""
        try:
            logger.info("Создание векторного индекса...")
            
            # Проверяем кэш эмбеддингов
            if self.embeddings_cache_path.exists():
                logger.info("Загрузка эмбеддингов из кэша...")
                self.document_embeddings = np.load(self.embeddings_cache_path)
            else:
                logger.info("Создание эмбеддингов для документов...")
                
                # Получаем тексты документов
                texts = [doc.page_content for doc in self.documents]
                
                # Создаем эмбеддинги в батчах для экономии памяти
                batch_size = 32
                embeddings = []
                
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_embeddings = self.embedding_model.encode(
                        batch_texts,
                        convert_to_numpy=True,
                        show_progress_bar=True
                    )
                    embeddings.append(batch_embeddings)
                
                self.document_embeddings = np.vstack(embeddings)
                
                # Сохраняем в кэш
                np.save(self.embeddings_cache_path, self.document_embeddings)
            
            # Создаем FAISS индекс
            dimension = self.document_embeddings.shape[1]
            self.vector_store = faiss.IndexFlatIP(dimension)  # Inner product для косинусной близости
            
            # Нормализуем эмбеддинги для корректного расчета косинусной близости
            faiss.normalize_L2(self.document_embeddings)
            self.vector_store.add(self.document_embeddings)
            
            logger.info(f"Векторный индекс создан для {len(self.documents)} документов")
            
        except Exception as e:
            logger.error(f"Ошибка создания векторного индекса: {e}")
            raise
    
    async def search(self, query: str, top_k: int = 5, score_threshold: float = 0.5) -> List[SearchResult]:
        """Поиск релевантных документов."""
        if not self.is_initialized:
            logger.warning("RAG-система не инициализирована")
            return []
        
        try:
            # Создаем эмбеддинг запроса
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)
            
            # Поиск в векторном индексе
            scores, indices = self.vector_store.search(query_embedding, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if score >= score_threshold:
                    doc = self.documents[idx]
                    result = SearchResult(
                        content=doc.page_content,
                        metadata=doc.metadata,
                        score=float(score),
                        source=doc.metadata.get('source', 'unknown')
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
    
    async def generate_answer(self, query: str, context_limit: int = 2000) -> RAGResponse:
        """Генерация ответа на основе найденного контекста."""
        if not self.is_initialized:
            return RAGResponse(
                answer="RAG-система не инициализирована",
                sources=[],
                confidence=0.0,
                context_used=""
            )
        
        try:
            # Поиск релевантных документов
            search_results = await self.search(query, top_k=10)
            
            if not search_results:
                return RAGResponse(
                    answer="Извините, не удалось найти релевантную информацию по вашему запросу.",
                    sources=[],
                    confidence=0.0,
                    context_used=""
                )
            
            # Формирование контекста
            context_parts = []
            context_length = 0
            used_sources = []
            
            for result in search_results:
                if context_length + len(result.content) <= context_limit:
                    context_parts.append(result.content)
                    context_length += len(result.content)
                    used_sources.append(result)
                else:
                    break
            
            context = "\n\n".join(context_parts)
            
            # Генерация ответа с помощью LLM
            answer = await self._generate_llm_response(query, context)
            
            # Расчет уверенности
            confidence = self._calculate_confidence(search_results, context)
            
            return RAGResponse(
                answer=answer,
                sources=used_sources,
                confidence=confidence,
                context_used=context
            )
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return RAGResponse(
                answer=f"Произошла ошибка при генерации ответа: {str(e)}",
                sources=[],
                confidence=0.0,
                context_used=""
            )
    
    async def _generate_llm_response(self, query: str, context: str) -> str:
        """Генерация ответа с помощью LLM."""
        try:
            headers = {"Content-Type": "application/json"}
            
            prompt = f"""На основе предоставленного контекста ответь на вопрос пользователя.

Контекст:
{context}

Вопрос: {query}

Требования к ответу:
1. Отвечай только на основе предоставленного контекста
2. Если в контексте нет достаточной информации для ответа, так и скажи
3. Структурируй ответ, используй списки и абзацы для лучшей читаемости
4. Отвечай на русском языке
5. Будь точным и конкретным

Ответ:"""

            data = {
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                f"{LLM_MODEL_PATH}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                response_data = response.json()
                answer = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return answer.strip()
            else:
                logger.warning(f"LLM недоступен: {response.status_code}")
                return "Извините, не удалось сгенерировать ответ из-за недоступности AI-модели."
                
        except Exception as e:
            logger.error(f"Ошибка генерации ответа LLM: {e}")
            return "Извините, произошла ошибка при генерации ответа."
    
    def _calculate_confidence(self, search_results: List[SearchResult], context: str) -> float:
        """Расчет уверенности в ответе."""
        if not search_results:
            return 0.0
        
        # Берем среднюю оценку топ результатов
        top_scores = [r.score for r in search_results[:3]]
        avg_score = sum(top_scores) / len(top_scores)
        
        # Учитываем длину контекста
        context_factor = min(len(context) / 1000, 1.0)
        
        # Итоговая уверенность
        confidence = avg_score * 0.7 + context_factor * 0.3
        return min(confidence, 1.0)
    
    async def add_document(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Добавление нового документа в базу."""
        try:
            doc = Document(page_content=content, metadata=metadata)
            self.documents.append(doc)
            
            # Создаем эмбеддинг для нового документа
            embedding = self.embedding_model.encode([content], convert_to_numpy=True)
            faiss.normalize_L2(embedding)
            
            # Добавляем в индекс
            self.vector_store.add(embedding)
            
            # Обновляем кэш эмбеддингов
            if self.document_embeddings is not None:
                self.document_embeddings = np.vstack([self.document_embeddings, embedding])
                np.save(self.embeddings_cache_path, self.document_embeddings)
            
            logger.info(f"Добавлен новый документ: {metadata.get('title', 'без названия')}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа: {e}")
            return False
    
    async def clear_cache(self):
        """Очистка кэша."""
        try:
            if self.embeddings_cache_path.exists():
                self.embeddings_cache_path.unlink()
            if self.documents_cache_path.exists():
                self.documents_cache_path.unlink()
            
            logger.info("Кэш RAG-системы очищен")
            
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")

# Глобальный экземпляр RAG-системы
rag_system = EnhancedRAGSystem()

async def initialize_rag() -> bool:
    """Инициализация глобальной RAG-системы."""
    return await rag_system.initialize()

async def search_knowledge(query: str, top_k: int = 5) -> List[SearchResult]:
    """Поиск в базе знаний."""
    return await rag_system.search(query, top_k)

async def generate_rag_answer(query: str) -> RAGResponse:
    """Генерация ответа на основе RAG."""
    return await rag_system.generate_answer(query)