"""
Улучшенная система агентов с многоуровневой логикой.
app/langchain/enhanced_agents.py
"""
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import requests

from app.config import LLM_MODEL_PATH
from app.knowledge.rag_advanced import rag_system, SearchResult
from app.database.models import get_db
from app.database.operations import (
    get_user_answers_by_lesson,
    get_question_by_id,
    get_lesson_by_id
)

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Типы агентов в системе."""
    KNOWLEDGE_ASSESSOR = "knowledge_assessor"
    ADAPTIVE_TUTOR = "adaptive_tutor"
    QUESTION_ANALYZER = "question_analyzer"
    LEARNING_COORDINATOR = "learning_coordinator"

@dataclass
class LearningContext:
    """Контекст обучения для агентов."""
    user_id: int
    lesson_id: int
    topic: str
    current_question_id: Optional[int] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    question_text: Optional[str] = None
    user_knowledge_level: float = 0.5
    misconceptions: List[str] = None
    learning_objectives: List[str] = None
    
    def __post_init__(self):
        if self.misconceptions is None:
            self.misconceptions = []
        if self.learning_objectives is None:
            self.learning_objectives = []

@dataclass
class AgentResponse:
    """Ответ агента."""
    agent_type: AgentType
    success: bool
    data: Dict[str, Any]
    confidence: float
    reasoning: str
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []

class BaseAgent:
    """Базовый класс для всех агентов."""
    
    def __init__(self, agent_type: AgentType):
        """Инициализация агента."""
        self.agent_type = agent_type
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Получение системного промпта для агента."""
        prompts = {
            AgentType.KNOWLEDGE_ASSESSOR: """Ты - эксперт по оценке знаний в области рисков непрерывности деятельности банков. 
            Твоя задача - анализировать ответы студентов и оценивать уровень их понимания концепций, выявлять пробелы в знаниях и заблуждения.""",
            
            AgentType.ADAPTIVE_TUTOR: """Ты - адаптивный преподаватель по рискам непрерывности деятельности. 
            Твоя задача - объяснять сложные концепции простым языком, адаптируя объяснения под уровень знаний студента.""",
            
            AgentType.QUESTION_ANALYZER: """Ты - аналитик вопросов и ответов в образовательной системе. 
            Твоя задача - анализировать качество вопросов, их сложность и релевантность учебным целям.""",
            
            AgentType.LEARNING_COORDINATOR: """Ты - координатор обучения, который планирует образовательную траекторию. 
            Твоя задача - определять следующие шаги в обучении на основе текущего прогресса студента."""
        }
        return prompts.get(self.agent_type, "Ты - помощник в образовательной системе.")
    
    async def _call_llm(self, prompt: str, temperature: float = 0.5) -> Optional[str]:
        """Вызов LLM для генерации ответа."""
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": 1500
            }
            
            response = requests.post(
                f"{LLM_MODEL_PATH}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка вызова LLM для {self.agent_type}: {e}")
            return None
    
    async def process(self, context: LearningContext) -> AgentResponse:
        """Основной метод обработки контекста."""
        raise NotImplementedError("Метод должен быть реализован в наследниках")

class KnowledgeAssessorAgent(BaseAgent):
    """Агент для оценки знаний пользователя."""
    
    def __init__(self):
        super().__init__(AgentType.KNOWLEDGE_ASSESSOR)
    
    async def process(self, context: LearningContext) -> AgentResponse:
        """Оценка знаний пользователя."""
        try:
            if not context.user_answer or not context.correct_answer:
                return AgentResponse(
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    confidence=0.0,
                    reasoning="Недостаточно данных для оценки"
                )
            
            # Получаем дополнительный контекст из RAG
            rag_context = await self._get_assessment_context(context)
            
            prompt = f"""Проанализируй ответ студента на вопрос по теме "{context.topic}".

Вопрос: {context.question_text}
Ответ студента: {context.user_answer}
Правильный ответ: {context.correct_answer}

Дополнительный контекст:
{rag_context}

Текущий уровень знаний студента: {context.user_knowledge_level:.1f} (от 0.0 до 1.0)

Выполни детальный анализ:
1. Оцени правильность ответа (0-100 баллов)
2. Определи уровень понимания концепции
3. Выяви возможные заблуждения или пробелы в знаниях
4. Оцени прогресс относительно предыдущих ответов
5. Дай рекомендации по дальнейшему обучению

Ответ должен быть в JSON формате:
{{
  "score": 85,
  "understanding_level": "хорошее понимание основ, но есть пробелы в деталях",
  "misconceptions": ["неправильное понимание термина X", "путаница между понятиями Y и Z"],
  "knowledge_gaps": ["не знает о методике расчета", "не понимает взаимосвязи процессов"],
  "confidence": 0.8,
  "recommendations": ["изучить дополнительно тему X", "пройти практические упражнения по Y"],
  "reasoning": "детальное объяснение оценки"
}}"""
            
            llm_response = await self._call_llm(prompt, temperature=0.3)
            
            if llm_response:
                try:
                    # Извлекаем JSON из ответа
                    json_start = llm_response.find("{")
                    json_end = llm_response.rfind("}") + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = llm_response[json_start:json_end]
                        assessment_data = json.loads(json_str)
                        
                        return AgentResponse(
                            agent_type=self.agent_type,
                            success=True,
                            data=assessment_data,
                            confidence=assessment_data.get('confidence', 0.7),
                            reasoning=assessment_data.get('reasoning', ''),
                            recommendations=assessment_data.get('recommendations', [])
                        )
                except json.JSONDecodeError:
                    logger.error("Ошибка парсинга JSON ответа от LLM")
            
            # Fallback: простая оценка
            is_correct = context.user_answer.strip().upper() == context.correct_answer.strip().upper()
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                data={
                    "score": 100 if is_correct else 0,
                    "understanding_level": "базовая оценка",
                    "misconceptions": [],
                    "knowledge_gaps": [] if is_correct else ["требует изучения материала"],
                    "confidence": 0.5
                },
                confidence=0.5,
                reasoning="Базовая оценка правильности ответа",
                recommendations=[] if is_correct else ["повторить материал урока"]
            )
            
        except Exception as e:
            logger.error(f"Ошибка в KnowledgeAssessorAgent: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Ошибка обработки: {str(e)}"
            )
    
    async def _get_assessment_context(self, context: LearningContext) -> str:
        """Получение контекста для оценки из RAG."""
        try:
            if context.question_text:
                search_results = await rag_system.search(context.question_text, top_k=2)
                if search_results:
                    return "\n".join([result.content for result in search_results])
            return ""
        except Exception:
            return ""

class AdaptiveTutorAgent(BaseAgent):
    """Агент для адаптивного объяснения материала."""
    
    def __init__(self):
        super().__init__(AgentType.ADAPTIVE_TUTOR)
    
    async def process(self, context: LearningContext) -> AgentResponse:
        """Генерация адаптивного объяснения."""
        try:
            # Получаем релевантный материал из RAG
            search_query = f"{context.topic} объяснение"
            if context.question_text:
                search_query += f" {context.question_text}"
            
            search_results = await rag_system.search(search_query, top_k=3)
            rag_context = "\n".join([result.content for result in search_results])
            
            # Определяем стиль объяснения на основе уровня знаний
            explanation_style = self._determine_explanation_style(context.user_knowledge_level)
            
            prompt = f"""Создай адаптивное объяснение для студента по теме "{context.topic}".

Контекст:
{rag_context}

Информация о студенте:
- Уровень знаний: {context.user_knowledge_level:.1f} (от 0.0 до 1.0)
- Стиль объяснения: {explanation_style}
- Выявленные заблуждения: {', '.join(context.misconceptions) if context.misconceptions else 'нет'}

{"Вопрос, который вызвал затруднения: " + context.question_text if context.question_text else ""}
{"Неправильный ответ студента: " + context.user_answer if context.user_answer else ""}

Создай объяснение, которое:
1. Соответствует уровню знаний студента
2. Использует подходящий стиль (простой/средний/продвинутый)
3. Адресует конкретные заблуждения, если они есть
4. Включает практические примеры из банковской сферы
5. Структурировано и легко для понимания

Ответ в JSON формате:
{{
  "explanation": "основное объяснение",
  "key_points": ["ключевой момент 1", "ключевой момент 2"],
  "examples": ["практический пример 1", "практический пример 2"],
  "analogies": ["аналогия для лучшего понимания"],
  "next_steps": ["что изучить дальше"],
  "confidence": 0.85
}}"""
            
            llm_response = await self._call_llm(prompt, temperature=0.6)
            
            if llm_response:
                try:
                    json_start = llm_response.find("{")
                    json_end = llm_response.rfind("}") + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = llm_response[json_start:json_end]
                        explanation_data = json.loads(json_str)
                        
                        return AgentResponse(
                            agent_type=self.agent_type,
                            success=True,
                            data=explanation_data,
                            confidence=explanation_data.get('confidence', 0.7),
                            reasoning="Адаптивное объяснение создано",
                            recommendations=explanation_data.get('next_steps', [])
                        )
                except json.JSONDecodeError:
                    logger.error("Ошибка парсинга JSON объяснения")
            
            # Fallback объяснение
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                data={
                    "explanation": "К сожалению, не удалось создать детальное объяснение. Рекомендуем обратиться к материалам урока.",
                    "key_points": [],
                    "examples": [],
                    "analogies": [],
                    "next_steps": ["повторить материал урока"],
                    "confidence": 0.3
                },
                confidence=0.3,
                reasoning="Fallback объяснение",
                recommendations=["повторить материал урока"]
            )
            
        except Exception as e:
            logger.error(f"Ошибка в AdaptiveTutorAgent: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Ошибка создания объяснения: {str(e)}"
            )
    
    def _determine_explanation_style(self, knowledge_level: float) -> str:
        """Определение стиля объяснения на основе уровня знаний."""
        if knowledge_level < 0.3:
            return "простой с базовыми определениями и аналогиями"
        elif knowledge_level < 0.7:
            return "средний с практическими примерами"
        else:
            return "продвинутый с техническими деталями и комплексными сценариями"

class LearningCoordinatorAgent(BaseAgent):
    """Агент для координации обучения и планирования траектории."""
    
    def __init__(self):
        super().__init__(AgentType.LEARNING_COORDINATOR)
    
    async def process(self, context: LearningContext) -> AgentResponse:
        """Планирование дальнейшего обучения."""
        try:
            # Анализируем историю ответов пользователя
            learning_history = await self._analyze_learning_history(context)
            
            prompt = f"""Проанализируй прогресс студента и определи оптимальную траекторию обучения.

Текущий контекст:
- Тема: {context.topic}
- Уровень знаний: {context.user_knowledge_level:.1f}
- Урок: {context.lesson_id}

История обучения:
{learning_history}

Выявленные проблемы:
- Заблуждения: {', '.join(context.misconceptions) if context.misconceptions else 'нет'}
- Цели обучения: {', '.join(context.learning_objectives) if context.learning_objectives else 'не определены'}

Определи:
1. Готовность к переходу к следующему уроку/теме
2. Области, требующие дополнительного изучения
3. Рекомендуемые дополнительные материалы
4. Оптимальную сложность следующих вопросов
5. Персонализированный план обучения

Ответ в JSON формате:
{{
  "ready_for_next": true/false,
  "readiness_score": 0.85,
  "weak_areas": ["область 1", "область 2"],
  "strong_areas": ["область 1", "область 2"],
  "recommended_difficulty": "beginner/intermediate/advanced",
  "learning_plan": {{
    "immediate_actions": ["действие 1", "действие 2"],
    "short_term_goals": ["цель 1", "цель 2"],
    "long_term_objectives": ["объектив 1", "объектив 2"]
  }},
  "additional_resources": ["ресурс 1", "ресурс 2"],
  "estimated_time": "время в минутах для следующего этапа",
  "confidence": 0.8
}}"""
            
            llm_response = await self._call_llm(prompt, temperature=0.4)
            
            if llm_response:
                try:
                    json_start = llm_response.find("{")
                    json_end = llm_response.rfind("}") + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = llm_response[json_start:json_end]
                        coordination_data = json.loads(json_str)
                        
                        return AgentResponse(
                            agent_type=self.agent_type,
                            success=True,
                            data=coordination_data,
                            confidence=coordination_data.get('confidence', 0.7),
                            reasoning="План обучения создан на основе анализа прогресса",
                            recommendations=coordination_data.get('learning_plan', {}).get('immediate_actions', [])
                        )
                except json.JSONDecodeError:
                    logger.error("Ошибка парсинга JSON плана обучения")
            
            # Fallback планирование
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                data={
                    "ready_for_next": context.user_knowledge_level >= 0.6,
                    "readiness_score": context.user_knowledge_level,
                    "weak_areas": [],
                    "strong_areas": [],
                    "recommended_difficulty": "intermediate",
                    "learning_plan": {
                        "immediate_actions": ["продолжить текущий урок"],
                        "short_term_goals": ["завершить текущую тему"],
                        "long_term_objectives": ["освоить все темы курса"]
                    },
                    "additional_resources": [],
                    "estimated_time": "30",
                    "confidence": 0.5
                },
                confidence=0.5,
                reasoning="Базовое планирование на основе уровня знаний"
            )
            
        except Exception as e:
            logger.error(f"Ошибка в LearningCoordinatorAgent: {e}")
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                data={},
                confidence=0.0,
                reasoning=f"Ошибка планирования: {str(e)}"
            )
    
    async def _analyze_learning_history(self, context: LearningContext) -> str:
        """Анализ истории обучения пользователя."""
        try:
            db = get_db()
            
            # Получаем историю ответов по всем урокам
            all_answers = []
            for lesson_id in range(1, context.lesson_id + 1):
                answers = get_user_answers_by_lesson(db, context.user_id, lesson_id)
                all_answers.extend(answers)
            
            if not all_answers:
                return "История ответов отсутствует"
            
            # Анализируем результаты
            total_answers = len(all_answers)
            correct_answers = sum(1 for answer in all_answers if answer.is_correct)
            success_rate = correct_answers / total_answers if total_answers > 0 else 0
            
            # Анализ по урокам
            lesson_performance = {}
            for answer in all_answers:
                lesson_id = answer.lesson_id or context.lesson_id
                if lesson_id not in lesson_performance:
                    lesson_performance[lesson_id] = {'correct': 0, 'total': 0}
                lesson_performance[lesson_id]['total'] += 1
                if answer.is_correct:
                    lesson_performance[lesson_id]['correct'] += 1
            
            history_summary = f"""Общая статистика:
- Всего ответов: {total_answers}
- Правильных ответов: {correct_answers}
- Процент успеха: {success_rate:.1%}

Результаты по урокам:"""
            
            for lesson_id, performance in lesson_performance.items():
                lesson_success = performance['correct'] / performance['total']
                history_summary += f"\n- Урок {lesson_id}: {performance['correct']}/{performance['total']} ({lesson_success:.1%})"
            
            return history_summary
            
        except Exception as e:
            logger.error(f"Ошибка анализа истории обучения: {e}")
            return "Ошибка получения истории обучения"

class EnhancedAgentSystem:
    """Улучшенная система агентов."""
    
    def __init__(self):
        """Инициализация системы агентов."""
        self.agents = {
            AgentType.KNOWLEDGE_ASSESSOR: KnowledgeAssessorAgent(),
            AgentType.ADAPTIVE_TUTOR: AdaptiveTutorAgent(),
            AgentType.LEARNING_COORDINATOR: LearningCoordinatorAgent()
        }
        self.is_available = False
        self._check_availability()
    
    def _check_availability(self):
        """Проверка доступности системы агентов."""
        try:
            # Проверяем доступность LLM
            response = requests.get(f"{LLM_MODEL_PATH}/models", timeout=5)
            self.is_available = response.status_code == 200
        except Exception:
            self.is_available = False
    
    async def assess_knowledge(self, context: LearningContext) -> AgentResponse:
        """Оценка знаний пользователя."""
        if not self.is_available:
            return self._fallback_assessment(context)
        
        agent = self.agents[AgentType.KNOWLEDGE_ASSESSOR]
        return await agent.process(context)
    
    async def generate_explanation(self, context: LearningContext) -> AgentResponse:
        """Генерация адаптивного объяснения."""
        if not self.is_available:
            return self._fallback_explanation(context)
        
        agent = self.agents[AgentType.ADAPTIVE_TUTOR]
        return await agent.process(context)
    
    async def coordinate_learning(self, context: LearningContext) -> AgentResponse:
        """Координация обучения."""
        if not self.is_available:
            return self._fallback_coordination(context)
        
        agent = self.agents[AgentType.LEARNING_COORDINATOR]
        return await agent.process(context)
    
    async def comprehensive_analysis(self, context: LearningContext) -> Dict[str, AgentResponse]:
        """Комплексный анализ с использованием всех агентов."""
        results = {}
        
        # Параллельно запускаем всех агентов
        tasks = []
        agent_types = []
        
        for agent_type, agent in self.agents.items():
            tasks.append(agent.process(context))
            agent_types.append(agent_type)
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for agent_type, response in zip(agent_types, responses):
                if isinstance(response, Exception):
                    logger.error(f"Ошибка в агенте {agent_type}: {response}")
                    results[agent_type.value] = AgentResponse(
                        agent_type=agent_type,
                        success=False,
                        data={},
                        confidence=0.0,
                        reasoning=f"Ошибка выполнения: {str(response)}"
                    )
                else:
                    results[agent_type.value] = response
            
        except Exception as e:
            logger.error(f"Ошибка комплексного анализа: {e}")
        
        return results
    
    def _fallback_assessment(self, context: LearningContext) -> AgentResponse:
        """Fallback оценка знаний."""
        if not context.user_answer or not context.correct_answer:
            score = 0
        else:
            score = 100 if context.user_answer.strip().upper() == context.correct_answer.strip().upper() else 0
        
        return AgentResponse(
            agent_type=AgentType.KNOWLEDGE_ASSESSOR,
            success=True,
            data={
                "score": score,
                "understanding_level": "базовая оценка",
                "misconceptions": [],
                "knowledge_gaps": [] if score > 0 else ["требует изучения"],
                "confidence": 0.5
            },
            confidence=0.5,
            reasoning="Базовая оценка без использования LLM"
        )
    
    def _fallback_explanation(self, context: LearningContext) -> AgentResponse:
        """Fallback объяснение."""
        return AgentResponse(
            agent_type=AgentType.ADAPTIVE_TUTOR,
            success=True,
            data={
                "explanation": "Рекомендуем внимательно изучить материал урока и обратить внимание на ключевые определения.",
                "key_points": ["изучить основные понятия", "понять взаимосвязи"],
                "examples": [],
                "analogies": [],
                "next_steps": ["повторить материал"],
                "confidence": 0.3
            },
            confidence=0.3,
            reasoning="Базовое объяснение без использования LLM"
        )
    
    def _fallback_coordination(self, context: LearningContext) -> AgentResponse:
        """Fallback координация обучения."""
        return AgentResponse(
            agent_type=AgentType.LEARNING_COORDINATOR,
            success=True,
            data={
                "ready_for_next": context.user_knowledge_level >= 0.6,
                "readiness_score": context.user_knowledge_level,
                "weak_areas": [],
                "strong_areas": [],
                "recommended_difficulty": "intermediate",
                "learning_plan": {
                    "immediate_actions": ["продолжить обучение"],
                    "short_term_goals": ["завершить урок"],
                    "long_term_objectives": ["освоить тему"]
                },
                "additional_resources": [],
                "estimated_time": "20",
                "confidence": 0.4
            },
            confidence=0.4,
            reasoning="Базовое планирование без использования LLM"
        )

# Глобальный экземпляр системы агентов
enhanced_agent_system = EnhancedAgentSystem()

# Функции для интеграции с основным ботом
async def assess_user_knowledge(
    user_id: int,
    lesson_id: int,
    topic: str,
    question_text: str,
    user_answer: str,
    correct_answer: str,
    user_knowledge_level: float = 0.5
) -> AgentResponse:
    """Оценка знаний пользователя."""
    context = LearningContext(
        user_id=user_id,
        lesson_id=lesson_id,
        topic=topic,
        question_text=question_text,
        user_answer=user_answer,
        correct_answer=correct_answer,
        user_knowledge_level=user_knowledge_level
    )
    
    return await enhanced_agent_system.assess_knowledge(context)

async def generate_adaptive_explanation(
    user_id: int,
    lesson_id: int,
    topic: str,
    question_text: str = None,
    user_answer: str = None,
    misconceptions: List[str] = None,
    user_knowledge_level: float = 0.5
) -> AgentResponse:
    """Генерация адаптивного объяснения."""
    context = LearningContext(
        user_id=user_id,
        lesson_id=lesson_id,
        topic=topic,
        question_text=question_text,
        user_answer=user_answer,
        user_knowledge_level=user_knowledge_level,
        misconceptions=misconceptions or []
    )
    
    return await enhanced_agent_system.generate_explanation(context)

async def coordinate_user_learning(
    user_id: int,
    lesson_id: int,
    topic: str,
    user_knowledge_level: float = 0.5,
    learning_objectives: List[str] = None
) -> AgentResponse:
    """Координация обучения пользователя."""
    context = LearningContext(
        user_id=user_id,
        lesson_id=lesson_id,
        topic=topic,
        user_knowledge_level=user_knowledge_level,
        learning_objectives=learning_objectives or []
    )
    
    return await enhanced_agent_system.coordinate_learning(context)