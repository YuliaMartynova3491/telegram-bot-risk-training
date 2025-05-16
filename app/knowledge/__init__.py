"""
Модуль для работы с базой знаний.

Этот модуль содержит компоненты для работы с базой знаний и генерации вопросов:
- rag.py: Retrieval-Augmented Generation для генерации вопросов
- jsonl/risk_knowledge.jsonl: База знаний по рискам непрерывности деятельности
"""

from app.knowledge.rag import (
    load_knowledge_base,
    create_vector_store,
    prepare_documents,
    init_llm,
    generate_questions,
    convert_questions_for_db,
    fallback_generate_questions
)

__all__ = [
    'load_knowledge_base',
    'create_vector_store',
    'prepare_documents',
    'init_llm',
    'generate_questions',
    'convert_questions_for_db',
    'fallback_generate_questions'
]
