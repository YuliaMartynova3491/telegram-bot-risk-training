"""
Модуль для работы с LangGraph и агентами.

Этот модуль содержит компоненты для адаптивного обучения с использованием LangGraph:
- agents.py: Определение агентов для различных задач
- graph.py: Построение графа для LangGraph
- prompts.py: Промпты для агентов
"""

from app.langchain.agents import (
    init_llm,
    KnowledgeAssessmentAgent,
    QuestionGenerationAgent,
    ExplanationAgent,
    QueryResponseAgent,
    PersonalizationAgent
)

from app.langchain.graph import (
    LearningState,
    create_learning_graph,
    create_learning_session
)

from app.langchain.prompts import (
    KNOWLEDGE_ASSESSMENT_PROMPT,
    QUESTION_GENERATION_PROMPT,
    EXPLANATION_PROMPT,
    QUERY_RESPONSE_PROMPT,
    PERSONALIZATION_PROMPT
)

__all__ = [
    # Агенты
    'init_llm',
    'KnowledgeAssessmentAgent',
    'QuestionGenerationAgent',
    'ExplanationAgent',
    'QueryResponseAgent',
    'PersonalizationAgent',
    
    # Граф
    'LearningState',
    'create_learning_graph',
    'create_learning_session',
    
    # Промпты
    'KNOWLEDGE_ASSESSMENT_PROMPT',
    'QUESTION_GENERATION_PROMPT',
    'EXPLANATION_PROMPT',
    'QUERY_RESPONSE_PROMPT',
    'PERSONALIZATION_PROMPT'
]