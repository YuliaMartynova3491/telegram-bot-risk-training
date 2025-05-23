"""
Улучшенная интеграция всех систем бота.
app/core/enhanced_integration.py
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.knowledge.rag_advanced import rag_system, RAGResponse
from app.learning.question_generator import question_generator, UserProfile
from app.langchain.enhanced_agents import (
    enhanced_agent_system, 
    LearningContext,
    assess_user_knowledge,
    generate_adaptive_explanation,
    coordinate_user_learning
)
from app.database.models import get_db
from app.database.operations import (
    get_or_create_user,
    get_lesson_by_id,
    get_course,
    update_user_progress,
    get_user_progress
)

logger = logging.getLogger(__name__)

class LearningMode(Enum):
    """Режимы обучения."""
    STANDARD = "standard"
    ADAPTIVE = "adaptive"
    ACCELERATED = "accelerated"
    REMEDIAL = "remedial"

@dataclass
class LearningSession:
    """Сессия обучения."""
    user_id: int
    lesson_id: int
    topic: str
    mode: LearningMode
    user_profile: UserProfile
    current_question_index: int = 0
    questions: List[Dict[str, Any]] = None
    answers: List[Dict[str, Any]] = None
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.questions is None:
            self.questions = []
        if self.answers is None:
            self.answers = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

class EnhancedLearningSystem:
    """Улучшенная система обучения."""
    
    def __init__(self):
        """Инициализация системы."""
        self.active_sessions: Dict[int, LearningSession] = {}
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Инициализация всех подсистем."""
        try:
            logger.info("Инициализация улучшенной системы обучения...")
            
            # Инициализируем RAG систему
            rag_initialized = await rag_system.initialize()
            if not rag_initialized:
                logger.warning("RAG система не инициализирована")
            
            # Проверяем доступность агентов
            agent_available = enhanced_agent_system.is_available
            if not agent_available:
                logger.warning("Система агентов недоступна")
            
            self.is_initialized = True
            logger.info("Система обучения инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации системы обучения: {e}")
            return False
    
    async def start_learning_session(
        self,
        user_id: int,
        lesson_id: int,
        telegram_user_data: Dict[str, Any] = None
    ) -> LearningSession:
        """Запуск сессии обучения."""
        try:
            db = get_db()
            
            # Получаем пользователя
            user = get_or_create_user(
                db,
                telegram_id=telegram_user_data.get('id', user_id),
                username=telegram_user_data.get('username'),
                first_name=telegram_user_data.get('first_name'),
                last_name=telegram_user_data.get('last_name')
            )
            
            # Получаем урок и тему
            lesson = get_lesson_by_id(db, lesson_id)
            if not lesson:
                raise ValueError(f"Урок {lesson_id} не найден")
            
            course = get_course(db, lesson.course_id)
            topic = course.name.lower().replace(" ", "_") if course else "general"
            
            # Создаем профиль пользователя
            user_profile = await question_generator.generate_user_profile(user.id)
            
            # Определяем режим обучения
            learning_mode = self._determine_learning_mode(user_profile)
            
            # Создаем сессию
            session = LearningSession(
                user_id=user.id,
                lesson_id=lesson_id,
                topic=topic,
                mode=learning_mode,
                user_profile=user_profile
            )
            
            # Генерируем вопросы для сессии
            await self._generate_session_questions(session)
            
            # Сохраняем активную сессию
            self.active_sessions[user.id] = session
            
            logger.info(f"Запущена сессия обучения для пользователя {user.id}, урок {lesson_id}")
            return session
            
        except Exception as e:
            logger.error(f"Ошибка запуска сессии обучения: {e}")
            raise
    
    def _determine_learning_mode(self, user_profile: UserProfile) -> LearningMode:
        """Определение режима обучения на основе профиля пользователя."""
        if user_profile.knowledge_level < 0.3:
            return LearningMode.REMEDIAL
        elif user_profile.knowledge_level > 0.8:
            return LearningMode.ACCELERATED
        elif len(user_profile.weak_topics) > len(user_profile.strong_topics):
            return LearningMode.ADAPTIVE
        else:
            return LearningMode.STANDARD
    
    async def _generate_session_questions(self, session: LearningSession):
        """Генерация вопросов для сессии."""
        try:
            # Определяем количество вопросов в зависимости от режима
            question_counts = {
                LearningMode.STANDARD: 3,
                LearningMode.ADAPTIVE: 4,
                LearningMode.ACCELERATED: 2,
                LearningMode.REMEDIAL: 5
            }
            
            num_questions = question_counts.get(session.mode, 3)
            
            # Генерируем адаптивные вопросы
            questions = await question_generator.generate_adaptive_questions(
                topic=session.topic,
                lesson_id=session.lesson_id,
                user_profile=session.user_profile,
                num_questions=num_questions
            )
            
            # Преобразуем в формат сессии
            session.questions = [
                {
                    "text": q.text,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty.value,
                    "type": q.question_type.value,
                    "confidence": q.confidence
                }
                for q in questions
            ]
            
            logger.info(f"Сгенерировано {len(session.questions)} вопросов для сессии")
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов для сессии: {e}")
            # Fallback: используем базовые вопросы
            session.questions = [
                {
                    "text": "Что такое риск нарушения непрерывности деятельности?",
                    "options": [
                        "Риск нарушения способности организации поддерживать операционную устойчивость",
                        "Риск финансовых потерь",
                        "Риск репутационных потерь",
                        "Риск кибератак"
                    ],
                    "correct_answer": "A",
                    "explanation": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость.",
                    "difficulty": "beginner",
                    "type": "multiple_choice",
                    "confidence": 0.6
                }
            ]
    
    async def process_answer(
        self,
        user_id: int,
        answer: str
    ) -> Dict[str, Any]:
        """Обработка ответа пользователя."""
        try:
            session = self.active_sessions.get(user_id)
            if not session:
                raise ValueError("Активная сессия не найдена")
            
            if session.current_question_index >= len(session.questions):
                raise ValueError("Все вопросы уже отвечены")
            
            current_question = session.questions[session.current_question_index]
            is_correct = answer.upper() == current_question["correct_answer"].upper()
            
            # Сохраняем ответ
            answer_data = {
                "question_index": session.current_question_index,
                "user_answer": answer,
                "is_correct": is_correct,
                "question_data": current_question
            }
            session.answers.append(answer_data)
            
            # Оценка знаний с помощью агентов
            assessment_result = None
            if enhanced_agent_system.is_available:
                try:
                    assessment_result = await assess_user_knowledge(
                        user_id=session.user_id,
                        lesson_id=session.lesson_id,
                        topic=session.topic,
                        question_text=current_question["text"],
                        user_answer=answer,
                        correct_answer=current_question["correct_answer"],
                        user_knowledge_level=session.user_profile.knowledge_level
                    )
                except Exception as e:
                    logger.warning(f"Ошибка оценки знаний агентом: {e}")
            
            # Генерация объяснения
            explanation_result = None
            if not is_correct and enhanced_agent_system.is_available:
                try:
                    explanation_result = await generate_adaptive_explanation(
                        user_id=session.user_id,
                        lesson_id=session.lesson_id,
                        topic=session.topic,
                        question_text=current_question["text"],
                        user_answer=answer,
                        user_knowledge_level=session.user_profile.knowledge_level
                    )
                except Exception as e:
                    logger.warning(f"Ошибка генерации объяснения агентом: {e}")
            
            # Обновляем метрики производительности
            self._update_performance_metrics(session)
            
            # Переходим к следующему вопросу
            session.current_question_index += 1
            
            # Проверяем завершение сессии
            is_completed = session.current_question_index >= len(session.questions)
            
            result = {
                "is_correct": is_correct,
                "explanation": current_question["explanation"],
                "is_completed": is_completed,
                "current_question_index": session.current_question_index,
                "total_questions": len(session.questions),
                "performance_metrics": session.performance_metrics
            }
            
            # Добавляем результаты агентов, если доступны
            if assessment_result and assessment_result.success:
                result["agent_assessment"] = assessment_result.data
            
            if explanation_result and explanation_result.success:
                result["adaptive_explanation"] = explanation_result.data
            
            # Если сессия завершена, обрабатываем результаты
            if is_completed:
                await self._complete_session(session)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки ответа: {e}")
            raise
    
    def _update_performance_metrics(self, session: LearningSession):
        """Обновление метрик производительности."""
        try:
            total_answers = len(session.answers)
            correct_answers = sum(1 for answer in session.answers if answer["is_correct"])
            
            session.performance_metrics = {
                "accuracy": correct_answers / total_answers if total_answers > 0 else 0,
                "progress": session.current_question_index / len(session.questions),
                "total_questions_answered": total_answers,
                "correct_answers": correct_answers,
                "difficulty_distribution": self._calculate_difficulty_distribution(session),
                "learning_mode": session.mode.value
            }
            
        except Exception as e:
            logger.error(f"Ошибка обновления метрик: {e}")
    
    def _calculate_difficulty_distribution(self, session: LearningSession) -> Dict[str, int]:
        """Расчет распределения по сложности."""
        distribution = {"beginner": 0, "intermediate": 0, "advanced": 0}
        
        for answer in session.answers:
            difficulty = answer["question_data"].get("difficulty", "intermediate")
            if difficulty in distribution:
                distribution[difficulty] += 1
        
        return distribution
    
    async def _complete_session(self, session: LearningSession):
        """Завершение сессии обучения."""
        try:
            # Расчет финальных метрик
            accuracy = session.performance_metrics.get("accuracy", 0)
            is_successful = accuracy >= 0.8  # 80% для успешного прохождения
            
            # Обновляем прогресс в БД
            db = get_db()
            update_user_progress(
                db=db,
                user_id=session.user_id,
                lesson_id=session.lesson_id,
                is_completed=True,
                success_percentage=accuracy * 100,
                questions_answered=len(session.answers),
                correct_answers=session.performance_metrics.get("correct_answers", 0)
            )
            
            # Координация дальнейшего обучения с помощью агентов
            if enhanced_agent_system.is_available:
                try:
                    coordination_result = await coordinate_user_learning(
                        user_id=session.user_id,
                        lesson_id=session.lesson_id,
                        topic=session.topic,
                        user_knowledge_level=accuracy
                    )
                    
                    if coordination_result.success:
                        session.performance_metrics["learning_plan"] = coordination_result.data
                        
                except Exception as e:
                    logger.warning(f"Ошибка координации обучения: {e}")
            
            # Удаляем активную сессию
            if session.user_id in self.active_sessions:
                del self.active_sessions[session.user_id]
            
            logger.info(f"Сессия завершена для пользователя {session.user_id}, точность: {accuracy:.1%}")
            
        except Exception as e:
            logger.error(f"Ошибка завершения сессии: {e}")
    
    async def handle_user_question(
        self,
        user_id: int,
        question_text: str,
        lesson_id: Optional[int] = None
    ) -> RAGResponse:
        """Обработка вопроса пользователя."""
        try:
            if not rag_system.is_initialized:
                return RAGResponse(
                    answer="Система ответов на вопросы временно недоступна.",
                    sources=[],
                    confidence=0.0,
                    context_used=""
                )
            
            # Получаем контекст урока, если указан
            context_info = ""
            if lesson_id:
                db = get_db()
                lesson = get_lesson_by_id(db, lesson_id)
                if lesson:
                    course = get_course(db, lesson.course_id)
                    context_info = f"Контекст: {course.name if course else 'Урок'} - {lesson.title}"
            
            # Дополняем запрос контекстом
            enhanced_query = f"{context_info}\n{question_text}" if context_info else question_text
            
            # Получаем ответ от RAG системы
            rag_response = await rag_system.generate_answer(enhanced_query)
            
            return rag_response
            
        except Exception as e:
            logger.error(f"Ошибка обработки вопроса пользователя: {e}")
            return RAGResponse(
                answer=f"Произошла ошибка при обработке вопроса: {str(e)}",
                sources=[],
                confidence=0.0,
                context_used=""
            )
    
    def get_session_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение статуса сессии."""
        session = self.active_sessions.get(user_id)
        if not session:
            return None
        
        return {
            "lesson_id": session.lesson_id,
            "topic": session.topic,
            "mode": session.mode.value,
            "current_question_index": session.current_question_index,
            "total_questions": len(session.questions),
            "performance_metrics": session.performance_metrics,
            "user_profile": {
                "knowledge_level": session.user_profile.knowledge_level,
                "strong_topics": session.user_profile.strong_topics,
                "weak_topics": session.user_profile.weak_topics
            }
        }
    
    async def get_learning_analytics(self, user_id: int) -> Dict[str, Any]:
        """Получение аналитики обучения пользователя."""
        try:
            db = get_db()
            
            # Получаем все прогрессы пользователя
            user_progresses = []
            for lesson_id in range(1, 20):  # Проверяем уроки 1-19
                progress = get_user_progress(db, user_id, lesson_id)
                if progress:
                    user_progresses.append({
                        "lesson_id": lesson_id,
                        "is_completed": progress.is_completed,
                        "success_percentage": getattr(progress, 'success_percentage', 0),
                        "questions_answered": getattr(progress, 'questions_answered', 0),
                        "correct_answers": getattr(progress, 'correct_answers', 0)
                    })
            
            # Расчет общей статистики
            total_lessons = len(user_progresses)
            completed_lessons = sum(1 for p in user_progresses if p["is_completed"])
            total_questions = sum(p["questions_answered"] for p in user_progresses)
            total_correct = sum(p["correct_answers"] for p in user_progresses)
            
            overall_accuracy = total_correct / total_questions if total_questions > 0 else 0
            completion_rate = completed_lessons / total_lessons if total_lessons > 0 else 0
            
            # Анализ сильных/слабых тем
            topic_performance = {}
            for progress in user_progresses:
                # Здесь бы нужно получить тему урока, но упростим
                topic = f"lesson_{progress['lesson_id']}"
                accuracy = progress["correct_answers"] / progress["questions_answered"] if progress["questions_answered"] > 0 else 0
                topic_performance[topic] = accuracy
            
            return {
                "overall_stats": {
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_lessons,
                    "completion_rate": completion_rate,
                    "total_questions_answered": total_questions,
                    "overall_accuracy": overall_accuracy
                },
                "topic_performance": topic_performance,
                "recent_activity": user_progresses[-5:] if user_progresses else [],
                "recommendations": self._generate_learning_recommendations(
                    overall_accuracy, completion_rate, topic_performance
                )
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики обучения: {e}")
            return {
                "overall_stats": {},
                "topic_performance": {},
                "recent_activity": [],
                "recommendations": []
            }
    
    def _generate_learning_recommendations(
        self, 
        accuracy: float, 
        completion_rate: float, 
        topic_performance: Dict[str, float]
    ) -> List[str]:
        """Генерация рекомендаций по обучению."""
        recommendations = []
        
        # Рекомендации на основе точности
        if accuracy < 0.6:
            recommendations.append("Рекомендуется больше времени уделить изучению основных концепций")
            recommendations.append("Попробуйте проходить уроки в более медленном темпе")
        elif accuracy > 0.9:
            recommendations.append("Отличные результаты! Можете переходить к более сложным темам")
            recommendations.append("Рассмотрите возможность изучения дополнительных материалов")
        
        # Рекомендации на основе прохождения
        if completion_rate < 0.5:
            recommendations.append("Постарайтесь завершить начатые уроки")
            recommendations.append("Установите регулярное расписание для обучения")
        
        # Рекомендации на основе производительности по темам
        weak_topics = [topic for topic, perf in topic_performance.items() if perf < 0.6]
        if weak_topics:
            recommendations.append(f"Обратите особое внимание на темы: {', '.join(weak_topics[:3])}")
        
        return recommendations if recommendations else ["Продолжайте в том же духе!"]

# Глобальный экземпляр системы
enhanced_learning_system = EnhancedLearningSystem()

# Функции для интеграции с основным ботом
async def initialize_enhanced_system() -> bool:
    """Инициализация улучшенной системы."""
    return await enhanced_learning_system.initialize()

async def start_enhanced_learning_session(
    user_id: int,
    lesson_id: int,
    telegram_user_data: Dict[str, Any] = None
) -> LearningSession:
    """Запуск улучшенной сессии обучения."""
    return await enhanced_learning_system.start_learning_session(
        user_id, lesson_id, telegram_user_data
    )

async def process_enhanced_answer(user_id: int, answer: str) -> Dict[str, Any]:
    """Обработка ответа в улучшенной системе."""
    return await enhanced_learning_system.process_answer(user_id, answer)

async def handle_enhanced_user_question(
    user_id: int,
    question_text: str,
    lesson_id: Optional[int] = None
) -> RAGResponse:
    """Обработка вопроса пользователя в улучшенной системе."""
    return await enhanced_learning_system.handle_user_question(
        user_id, question_text, lesson_id
    )

def get_enhanced_session_status(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение статуса сессии в улучшенной системе."""
    return enhanced_learning_system.get_session_status(user_id)

async def get_enhanced_learning_analytics(user_id: int) -> Dict[str, Any]:
    """Получение аналитики обучения в улучшенной системе."""
    return await enhanced_learning_system.get_learning_analytics(user_id)