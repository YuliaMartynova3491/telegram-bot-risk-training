"""
Улучшенная система генерации вопросов с адаптивной сложностью.
app/learning/question_generator.py
"""
import json
import random
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import requests
from app.config import LLM_MODEL_PATH, QUESTIONS_PER_LESSON
from app.database.models import get_db
from app.database.operations import (
    get_question_by_id,
    create_question,
    get_user_answers_by_lesson,
    get_user_by_telegram_id
)
from app.knowledge.rag_advanced import rag_system

logger = logging.getLogger(__name__)

class DifficultyLevel(Enum):
    """Уровни сложности вопросов."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class QuestionType(Enum):
    """Типы вопросов."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SCENARIO = "scenario"
    DEFINITION = "definition"

@dataclass
class UserProfile:
    """Профиль пользователя для адаптивной генерации."""
    user_id: int
    knowledge_level: float  # 0.0 - 1.0
    strong_topics: List[str]
    weak_topics: List[str]
    preferred_question_types: List[QuestionType]
    learning_style: str  # visual, auditory, kinesthetic

@dataclass
class QuestionTemplate:
    """Шаблон для генерации вопросов."""
    type: QuestionType
    difficulty: DifficultyLevel
    topic: str
    template: str
    example_context: str

@dataclass
class GeneratedQuestion:
    """Сгенерированный вопрос."""
    text: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: DifficultyLevel
    topic: str
    question_type: QuestionType
    confidence: float

class AdaptiveQuestionGenerator:
    """Адаптивный генератор вопросов."""
    
    def __init__(self):
        """Инициализация генератора."""
        self.question_templates = self._load_question_templates()
        self.topic_keywords = self._load_topic_keywords()
        
    def _load_question_templates(self) -> Dict[str, List[QuestionTemplate]]:
        """Загрузка шаблонов вопросов."""
        templates = {
            "риск_нарушения_непрерывности": [
                QuestionTemplate(
                    type=QuestionType.DEFINITION,
                    difficulty=DifficultyLevel.BEGINNER,
                    topic="риск_нарушения_непрерывности",
                    template="Что такое {concept}?",
                    example_context="определение и основные характеристики"
                ),
                QuestionTemplate(
                    type=QuestionType.MULTIPLE_CHOICE,
                    difficulty=DifficultyLevel.INTERMEDIATE,
                    topic="риск_нарушения_непрерывности",
                    template="Какие факторы влияют на {concept}?",
                    example_context="факторы и взаимосвязи"
                ),
                QuestionTemplate(
                    type=QuestionType.SCENARIO,
                    difficulty=DifficultyLevel.ADVANCED,
                    topic="риск_нарушения_непрерывности",
                    template="В ситуации {scenario}, как следует управлять {concept}?",
                    example_context="практические сценарии и решения"
                )
            ],
            "оценка_критичности": [
                QuestionTemplate(
                    type=QuestionType.DEFINITION,
                    difficulty=DifficultyLevel.BEGINNER,
                    topic="оценка_критичности",
                    template="Что означает {concept} в контексте оценки критичности?",
                    example_context="определения и классификации"
                ),
                QuestionTemplate(
                    type=QuestionType.MULTIPLE_CHOICE,
                    difficulty=DifficultyLevel.INTERMEDIATE,
                    topic="оценка_критичности",
                    template="Какие методы используются для {concept}?",
                    example_context="методологии и подходы"
                ),
                QuestionTemplate(
                    type=QuestionType.SCENARIO,
                    difficulty=DifficultyLevel.ADVANCED,
                    topic="оценка_критичности",
                    template="При проведении {concept} в банке, какие шаги необходимо предпринять в случае {scenario}?",
                    example_context="практические кейсы банковской деятельности"
                )
            ]
        }
        return templates
    
    def _load_topic_keywords(self) -> Dict[str, List[str]]:
        """Загрузка ключевых слов по темам."""
        keywords = {
            "риск_нарушения_непрерывности": [
                "риск нарушения непрерывности",
                "угроза непрерывности",
                "операционная устойчивость",
                "чрезвычайная ситуация",
                "план обеспечения непрерывности"
            ],
            "оценка_критичности": [
                "оценка критичности процессов",
                "категории критичности",
                "экономические потери",
                "репутационные последствия",
                "юридические последствия"
            ],
            "оценка_риска": [
                "оценка риска",
                "величина воздействия",
                "рейтинг риска",
                "целевое время восстановления",
                "максимально приемлемый период прерывания"
            ]
        }
        return keywords
    
    async def generate_user_profile(self, user_id: int) -> UserProfile:
        """Создание профиля пользователя на основе его истории."""
        try:
            db = get_db()
            
            # Получаем историю ответов пользователя
            user_answers = []
            for lesson_id in range(1, 10):  # Проверяем уроки 1-9
                lesson_answers = get_user_answers_by_lesson(db, user_id, lesson_id)
                user_answers.extend(lesson_answers)
            
            if not user_answers:
                # Новый пользователь - средний уровень
                return UserProfile(
                    user_id=user_id,
                    knowledge_level=0.5,
                    strong_topics=[],
                    weak_topics=[],
                    preferred_question_types=[QuestionType.MULTIPLE_CHOICE],
                    learning_style="visual"
                )
            
            # Анализ результатов
            total_answers = len(user_answers)
            correct_answers = sum(1 for answer in user_answers if answer.is_correct)
            knowledge_level = correct_answers / total_answers
            
            # Анализ сильных и слабых тем
            topic_performance = {}
            for answer in user_answers:
                question = get_question_by_id(db, answer.question_id)
                if question:
                    topic = question.metadata.get('topic', 'unknown')
                    if topic not in topic_performance:
                        topic_performance[topic] = {'correct': 0, 'total': 0}
                    topic_performance[topic]['total'] += 1
                    if answer.is_correct:
                        topic_performance[topic]['correct'] += 1
            
            # Определяем сильные и слабые темы
            strong_topics = []
            weak_topics = []
            
            for topic, performance in topic_performance.items():
                if performance['total'] >= 3:  # Минимум 3 вопроса по теме
                    success_rate = performance['correct'] / performance['total']
                    if success_rate >= 0.8:
                        strong_topics.append(topic)
                    elif success_rate <= 0.5:
                        weak_topics.append(topic)
            
            return UserProfile(
                user_id=user_id,
                knowledge_level=knowledge_level,
                strong_topics=strong_topics,
                weak_topics=weak_topics,
                preferred_question_types=[QuestionType.MULTIPLE_CHOICE],
                learning_style="visual"
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания профиля пользователя {user_id}: {e}")
            # Возвращаем базовый профиль
            return UserProfile(
                user_id=user_id,
                knowledge_level=0.5,
                strong_topics=[],
                weak_topics=[],
                preferred_question_types=[QuestionType.MULTIPLE_CHOICE],
                learning_style="visual"
            )
    
    async def generate_adaptive_questions(
        self,
        topic: str,
        lesson_id: int,
        user_profile: UserProfile,
        num_questions: int = QUESTIONS_PER_LESSON
    ) -> List[GeneratedQuestion]:
        """Генерация адаптивных вопросов."""
        try:
            questions = []
            
            # Определяем сложность на основе профиля пользователя
            if user_profile.knowledge_level < 0.4:
                difficulty_distribution = [
                    (DifficultyLevel.BEGINNER, 0.7),
                    (DifficultyLevel.INTERMEDIATE, 0.3),
                    (DifficultyLevel.ADVANCED, 0.0)
                ]
            elif user_profile.knowledge_level < 0.7:
                difficulty_distribution = [
                    (DifficultyLevel.BEGINNER, 0.3),
                    (DifficultyLevel.INTERMEDIATE, 0.5),
                    (DifficultyLevel.ADVANCED, 0.2)
                ]
            else:
                difficulty_distribution = [
                    (DifficultyLevel.BEGINNER, 0.1),
                    (DifficultyLevel.INTERMEDIATE, 0.4),
                    (DifficultyLevel.ADVANCED, 0.5)
                ]
            
            # Генерируем вопросы согласно распределению сложности
            for i in range(num_questions):
                # Выбираем уровень сложности
                difficulty = self._choose_difficulty(difficulty_distribution)
                
                # Выбираем тип вопроса
                question_type = random.choice(user_profile.preferred_question_types)
                
                # Генерируем вопрос
                question = await self._generate_single_question(
                    topic=topic,
                    difficulty=difficulty,
                    question_type=question_type,
                    user_profile=user_profile
                )
                
                if question:
                    questions.append(question)
            
            # Если не удалось сгенерировать достаточно вопросов, добавляем базовые
            while len(questions) < num_questions:
                basic_question = await self._generate_fallback_question(topic, lesson_id)
                if basic_question:
                    questions.append(basic_question)
                else:
                    break
            
            return questions
            
        except Exception as e:
            logger.error(f"Ошибка генерации адаптивных вопросов: {e}")
            return []
    
    def _choose_difficulty(self, difficulty_distribution: List[Tuple[DifficultyLevel, float]]) -> DifficultyLevel:
        """Выбор уровня сложности на основе распределения."""
        rand = random.random()
        cumulative = 0.0
        
        for difficulty, probability in difficulty_distribution:
            cumulative += probability
            if rand <= cumulative:
                return difficulty
        
        return DifficultyLevel.INTERMEDIATE  # Fallback
    
    async def _generate_single_question(
        self,
        topic: str,
        difficulty: DifficultyLevel,
        question_type: QuestionType,
        user_profile: UserProfile
    ) -> Optional[GeneratedQuestion]:
        """Генерация одного вопроса."""
        try:
            # Получаем релевантный контекст из RAG
            search_query = f"{topic} {difficulty.value}"
            search_results = await rag_system.search(search_query, top_k=3)
            
            if not search_results:
                return None
            
            # Формируем контекст
            context = "\n".join([result.content for result in search_results[:2]])
            
            # Генерируем вопрос с помощью LLM
            question_data = await self._generate_question_with_llm(
                topic=topic,
                difficulty=difficulty,
                question_type=question_type,
                context=context,
                user_profile=user_profile
            )
            
            if question_data:
                return GeneratedQuestion(
                    text=question_data["question"],
                    options=question_data["options"],
                    correct_answer=question_data["correct_answer"],
                    explanation=question_data["explanation"],
                    difficulty=difficulty,
                    topic=topic,
                    question_type=question_type,
                    confidence=question_data.get("confidence", 0.7)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопроса: {e}")
            return None
    
    async def _generate_question_with_llm(
        self,
        topic: str,
        difficulty: DifficultyLevel,
        question_type: QuestionType,
        context: str,
        user_profile: UserProfile
    ) -> Optional[Dict[str, Any]]:
        """Генерация вопроса с помощью LLM."""
        try:
            # Подготавливаем промпт
            difficulty_descriptions = {
                DifficultyLevel.BEGINNER: "базовый (проверка понимания основных определений)",
                DifficultyLevel.INTERMEDIATE: "средний (применение знаний в типичных ситуациях)",
                DifficultyLevel.ADVANCED: "продвинутый (анализ сложных сценариев и принятие решений)"
            }
            
            type_descriptions = {
                QuestionType.MULTIPLE_CHOICE: "множественный выбор с 4 вариантами ответов",
                QuestionType.TRUE_FALSE: "верно/неверно",
                QuestionType.SCENARIO: "анализ практического сценария",
                QuestionType.DEFINITION: "определение понятия"
            }
            
            prompt = f"""На основе предоставленного контекста создай образовательный вопрос.

Контекст:
{context}

Параметры вопроса:
- Тема: {topic}
- Уровень сложности: {difficulty_descriptions[difficulty]}
- Тип вопроса: {type_descriptions[question_type]}
- Уровень знаний учащегося: {user_profile.knowledge_level:.1f} (от 0.0 до 1.0)

Требования:
1. Вопрос должен быть основан на предоставленном контексте
2. Соответствовать указанному уровню сложности
3. Иметь 4 варианта ответа (A, B, C, D), только один правильный
4. Включать подробное объяснение правильного ответа
5. Быть практически применимым в банковской сфере

Ответ должен быть в JSON формате:
{{
  "question": "текст вопроса",
  "options": ["вариант A", "вариант B", "вариант C", "вариант D"],
  "correct_answer": "A",
  "explanation": "подробное объяснение правильного ответа",
  "confidence": 0.8
}}"""

            headers = {"Content-Type": "application/json"}
            data = {
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
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
                content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Извлекаем JSON из ответа
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = content[json_start:json_end]
                    return json.loads(json_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопроса с LLM: {e}")
            return None
    
    async def _generate_fallback_question(self, topic: str, lesson_id: int) -> Optional[GeneratedQuestion]:
        """Генерация резервного вопроса из шаблонов."""
        try:
            # Базовые вопросы по темам
            fallback_questions = {
                "риск_нарушения_непрерывности": [
                    {
                        "question": "Что такое риск нарушения непрерывности деятельности?",
                        "options": [
                            "Риск нарушения способности организации поддерживать операционную устойчивость",
                            "Риск потери финансовых средств",
                            "Риск изменения курса валют",
                            "Риск увольнения сотрудников"
                        ],
                        "correct_answer": "A",
                        "explanation": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций."
                    }
                ],
                "оценка_критичности": [
                    {
                        "question": "Какие категории критичности процессов существуют?",
                        "options": [
                            "Критически важный, основной, прочий",
                            "Высокий, средний, низкий",
                            "Красный, желтый, зеленый",
                            "Приоритетный, вторичный, третичный"
                        ],
                        "correct_answer": "A",
                        "explanation": "Существуют три категории критичности процессов: критически важный, основной и прочий. Риск нарушения непрерывности оценивается только для критически важных процессов."
                    }
                ]
            }
            
            topic_questions = fallback_questions.get(topic, [])
            if topic_questions:
                question_data = random.choice(topic_questions)
                
                return GeneratedQuestion(
                    text=question_data["question"],
                    options=question_data["options"],
                    correct_answer=question_data["correct_answer"],
                    explanation=question_data["explanation"],
                    difficulty=DifficultyLevel.BEGINNER,
                    topic=topic,
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    confidence=0.6
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации резервного вопроса: {e}")
            return None
    
    async def save_questions_to_db(self, questions: List[GeneratedQuestion], lesson_id: int) -> List[int]:
        """Сохранение вопросов в базу данных."""
        try:
            db = get_db()
            saved_question_ids = []
            
            for question in questions:
                db_question = create_question(
                    db=db,
                    lesson_id=lesson_id,
                    text=question.text,
                    options=json.dumps(question.options, ensure_ascii=False),
                    correct_answer=question.correct_answer,
                    explanation=question.explanation
                )
                
                if db_question:
                    saved_question_ids.append(db_question.id)
            
            logger.info(f"Сохранено {len(saved_question_ids)} вопросов для урока {lesson_id}")
            return saved_question_ids
            
        except Exception as e:
            logger.error(f"Ошибка сохранения вопросов в БД: {e}")
            return []

# Глобальный экземпляр генератора
question_generator = AdaptiveQuestionGenerator()

async def generate_adaptive_questions_for_lesson(
    lesson_id: int,
    topic: str,
    user_id: int,
    num_questions: int = QUESTIONS_PER_LESSON
) -> List[int]:
    """Основная функция для генерации адаптивных вопросов."""
    try:
        # Создаем профиль пользователя
        user_profile = await question_generator.generate_user_profile(user_id)
        
        # Генерируем вопросы
        questions = await question_generator.generate_adaptive_questions(
            topic=topic,
            lesson_id=lesson_id,
            user_profile=user_profile,
            num_questions=num_questions
        )
        
        if not questions:
            logger.warning(f"Не удалось сгенерировать вопросы для урока {lesson_id}")
            return []
        
        # Сохраняем в базу данных
        question_ids = await question_generator.save_questions_to_db(questions, lesson_id)
        
        return question_ids
        
    except Exception as e:
        logger.error(f"Ошибка генерации адаптивных вопросов для урока {lesson_id}: {e}")
        return []