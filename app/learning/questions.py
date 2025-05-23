"""
Модуль для генерации вопросов и работы с ними.
Исправленная версия с правильной обработкой ошибок.
"""
import json
import random
import logging
from typing import List, Dict, Any
from app.database.models import get_db
from app.database.operations import (
    create_question, 
    get_questions_by_lesson, 
    get_question_by_id,
    save_user_answer,
    get_user_answers_for_lesson,
    calculate_lesson_success_percentage,
    update_user_progress
)
from app.config import QUESTIONS_PER_LESSON, MIN_SUCCESS_PERCENTAGE, RISK_KNOWLEDGE_PATH

logger = logging.getLogger(__name__)

def load_knowledge_base(path: str = RISK_KNOWLEDGE_PATH) -> List[Dict[str, Any]]:
    """Загружает базу знаний из JSONL файла."""
    knowledge_base = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Проверяем, что строка не пустая
                    knowledge_base.append(json.loads(line))
        logger.info(f"Загружено {len(knowledge_base)} записей из базы знаний")
        return knowledge_base
    except FileNotFoundError:
        logger.warning(f"Файл базы знаний не найден: {path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в файле {path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке базы знаний: {e}")
        return []

def generate_questions_for_lesson(lesson_id: int, topic: str, difficulty: str = "средний") -> List[Dict[str, Any]]:
    """Генерирует вопросы для урока."""
    db = get_db()
    
    try:
        # Проверяем, есть ли уже вопросы для этого урока
        existing_questions = get_questions_by_lesson(db, lesson_id)
        
        if existing_questions:
            logger.info(f"Для урока {lesson_id} уже существует {len(existing_questions)} вопросов")
            return existing_questions
        
        # Загружаем базу знаний
        knowledge_base = load_knowledge_base()
        if not knowledge_base:
            logger.warning("База знаний пуста, создаем дефолтные вопросы")
            return create_default_questions(db, lesson_id)
        
        # Фильтруем базу знаний по теме и сложности
        filtered_kb = [
            item for item in knowledge_base 
            if (
                item.get('metadata', {}).get('topic', '').startswith(topic.split('_')[0]) and 
                item.get('metadata', {}).get('difficulty', '') == difficulty
            )
        ]
        
        # Если не нашли подходящих элементов, используем все элементы базы
        if not filtered_kb:
            logger.info(f"Не найдено записей для темы {topic} и сложности {difficulty}, используем все записи")
            filtered_kb = knowledge_base
        
        # Выбираем случайные элементы для вопросов
        selected_items = []
        
        if len(filtered_kb) >= QUESTIONS_PER_LESSON:
            selected_items = random.sample(filtered_kb, QUESTIONS_PER_LESSON)
        else:
            # Если не хватает элементов, используем все доступные и добавляем случайные из оставшихся
            selected_items = filtered_kb.copy()
            remaining = [item for item in knowledge_base if item not in selected_items]
            if remaining:
                additional_items = random.sample(remaining, min(QUESTIONS_PER_LESSON - len(selected_items), len(remaining)))
                selected_items.extend(additional_items)
        
        # Создаем вопросы на основе выбранных элементов
        created_questions = []
        for item in selected_items:
            try:
                question_text = item['prompt']
                correct_answer = item['response']
                
                # Формируем краткий ответ (первое предложение)
                short_answer = correct_answer.split('.')[0] + '.'
                
                # Генерируем неправильные варианты, используя другие ответы из базы
                other_answers = [
                    kb_item['response'].split('.')[0] + '.' 
                    for kb_item in knowledge_base 
                    if kb_item['response'] != correct_answer
                ]
                
                # Выбираем случайные неправильные ответы
                wrong_answers = random.sample(other_answers, min(3, len(other_answers)))
                while len(wrong_answers) < 3:
                    wrong_answers.append("Недостаточно информации для ответа")
                
                # Формируем варианты ответов
                options = [short_answer] + wrong_answers
                random.shuffle(options)
                
                # Определяем правильный ответ
                correct_index = options.index(short_answer)
                correct_letter = chr(65 + correct_index)  # A, B, C или D
                
                # Сохраняем вопрос в базе данных
                question = create_question(
                    db,
                    lesson_id=lesson_id,
                    text=question_text,
                    options=json.dumps(options, ensure_ascii=False),
                    correct_answer=correct_letter,
                    explanation=correct_answer
                )
                created_questions.append(question)
                logger.info(f"Создан вопрос: {question_text[:50]}...")
                
            except Exception as e:
                logger.error(f"Ошибка при создании вопроса из элемента {item.get('prompt', 'unknown')}: {e}")
                continue
        
        # Если не удалось создать достаточно вопросов, добавляем дефолтные
        if len(created_questions) < QUESTIONS_PER_LESSON:
            logger.info(f"Создано только {len(created_questions)} вопросов, добавляем дефолтные")
            default_questions = create_default_questions(db, lesson_id, QUESTIONS_PER_LESSON - len(created_questions))
            created_questions.extend(default_questions)
        
        # Получаем созданные вопросы
        final_questions = get_questions_by_lesson(db, lesson_id)
        logger.info(f"Итого создано {len(final_questions)} вопросов для урока {lesson_id}")
        return final_questions
        
    except Exception as e:
        logger.error(f"Ошибка при генерации вопросов для урока {lesson_id}: {e}")
        return create_default_questions(db, lesson_id)

def create_default_questions(db, lesson_id: int, count: int = QUESTIONS_PER_LESSON) -> List[Dict[str, Any]]:
    """Создает стандартные вопросы для урока, если база знаний недоступна."""
    default_questions = [
        {
            "text": "Что такое риск нарушения непрерывности деятельности?",
            "options": json.dumps([
                "Риск нарушения способности организации поддерживать операционную устойчивость.",
                "Риск потери денежных средств.",
                "Риск изменения курса валют.",
                "Риск увольнения сотрудников."
            ], ensure_ascii=False),
            "correct_answer": "A",
            "explanation": "Риск нарушения непрерывности деятельности - это риск нарушения способности организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций."
        },
        {
            "text": "Что такое угроза непрерывности?",
            "options": json.dumps([
                "Обстановка, сложившаяся в результате аварии или стихийного бедствия.",
                "Отключение электроэнергии в офисе.",
                "Увольнение директора организации.",
                "Снижение рейтинга организации."
            ], ensure_ascii=False),
            "correct_answer": "A",
            "explanation": "Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы и т.д."
        },
        {
            "text": "Какие типы угроз непрерывности существуют согласно методике?",
            "options": json.dumps([
                "Техногенные, природные, геополитические, социальные, биолого-социальные, экономические.",
                "Внутренние и внешние.",
                "Финансовые и нефинансовые.",
                "Локальные и глобальные."
            ], ensure_ascii=False),
            "correct_answer": "A",
            "explanation": "Угрозы непрерывности делятся на 6 типов: техногенные, природные, геополитические, социальные, биолого-социальные, экономические."
        },
        {
            "text": "Что такое RTO (время восстановления процесса)?",
            "options": json.dumps([
                "Период времени, установленный для возобновления работы процесса.",
                "Максимальный период простоя процесса.",
                "Время на создание резервной копии.",
                "Продолжительность чрезвычайной ситуации."
            ], ensure_ascii=False),
            "correct_answer": "A",
            "explanation": "RTO (Recovery Time Objective) - время восстановления процесса - это период времени, установленный для возобновления работы процесса после его прерывания."
        },
        {
            "text": "Что такое MTPD (максимально допустимый период простоя)?",
            "options": json.dumps([
                "Период времени, по истечении которого последствия становятся неприемлемыми.",
                "Время восстановления процесса.",
                "Продолжительность рабочего дня.",
                "Время создания плана восстановления."
            ], ensure_ascii=False),
            "correct_answer": "A",
            "explanation": "MTPD (Maximum Tolerable Period of Disruption) - период времени, по истечении которого неблагоприятные последствия становятся неприемлемыми."
        }
    ]
    
    # Создаем нужное количество вопросов в базе данных
    created_questions = []
    for i in range(min(count, len(default_questions))):
        try:
            q = default_questions[i]
            question = create_question(
                db,
                lesson_id=lesson_id,
                text=q["text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"]
            )
            created_questions.append(question)
            logger.info(f"Создан дефолтный вопрос: {q['text'][:50]}...")
        except Exception as e:
            logger.error(f"Ошибка при создании дефолтного вопроса: {e}")
            continue
    
    return created_questions

def get_options_for_question(question_id: int) -> List[str]:
    """Получает варианты ответов для вопроса."""
    try:
        db = get_db()
        question = get_question_by_id(db, question_id)
        
        if not question:
            logger.warning(f"Вопрос с ID {question_id} не найден")
            return []
        
        if isinstance(question.options, str):
            try:
                return json.loads(question.options)
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования опций вопроса {question_id}: {e}")
                return []
        else:
            return question.options if question.options else []
            
    except Exception as e:
        logger.error(f"Ошибка при получении опций для вопроса {question_id}: {e}")
        return []

def check_answer(question_id: int, user_id: int, answer: str) -> bool:
    """Проверяет правильность ответа пользователя."""
    try:
        db = get_db()
        question = get_question_by_id(db, question_id)
        
        if not question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            return False
        
        is_correct = (answer == question.correct_answer)
        
        # Сохраняем ответ пользователя
        try:
            save_user_answer(db, user_id, question_id, answer, is_correct, question.lesson_id)
            logger.info(f"Ответ пользователя {user_id} на вопрос {question_id}: {answer} ({'верно' if is_correct else 'неверно'})")
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа пользователя: {e}")
        
        return is_correct
        
    except Exception as e:
        logger.error(f"Ошибка при проверке ответа пользователя {user_id} на вопрос {question_id}: {e}")
        return False

def get_explanation(question_id: int) -> str:
    """Получает объяснение правильного ответа."""
    try:
        db = get_db()
        question = get_question_by_id(db, question_id)
        
        if not question:
            logger.warning(f"Вопрос с ID {question_id} не найден")
            return "Объяснение недоступно."
        
        return question.explanation if question.explanation else "Объяснение недоступно."
        
    except Exception as e:
        logger.error(f"Ошибка при получении объяснения для вопроса {question_id}: {e}")
        return "Объяснение недоступно."

def check_lesson_completion(user_id: int, lesson_id: int) -> Dict[str, Any]:
    """Проверяет завершение урока пользователем."""
    try:
        db = get_db()
        
        # Получаем все вопросы урока
        questions = get_questions_by_lesson(db, lesson_id)
        
        if not questions:
            logger.warning(f"Для урока {lesson_id} не найдено вопросов")
            return {
                "is_completed": False,
                "success_percentage": 0.0,
                "is_successful": False
            }
        
        # Получаем ответы пользователя
        user_answers = get_user_answers_for_lesson(db, user_id, lesson_id)
        
        # Если пользователь не ответил на все вопросы, урок не завершен
        if len(user_answers) < len(questions):
            logger.info(f"Пользователь {user_id} ответил на {len(user_answers)} из {len(questions)} вопросов урока {lesson_id}")
            return {
                "is_completed": False,
                "success_percentage": 0.0,
                "is_successful": False
            }
        
        # Вычисляем процент успешности
        success_percentage = calculate_lesson_success_percentage(db, user_id, lesson_id)
        
        # Определяем, успешно ли завершен урок
        is_successful = success_percentage >= MIN_SUCCESS_PERCENTAGE
        
        # Обновляем прогресс пользователя
        try:
            update_user_progress(db, user_id, lesson_id, is_successful, success_percentage)
            logger.info(f"Обновлен прогресс пользователя {user_id} по уроку {lesson_id}: {success_percentage:.1f}%")
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресса: {e}")
        
        return {
            "is_completed": True,
            "success_percentage": success_percentage,
            "is_successful": is_successful
        }
        
    except Exception as e:
        logger.error(f"Ошибка при проверке завершения урока {lesson_id} пользователем {user_id}: {e}")
        return {
            "is_completed": False,
            "success_percentage": 0.0,
            "is_successful": False
        }

def get_correct_answers_count(user_id: int, lesson_id: int) -> Dict[str, Any]:
    """Получает количество правильных ответов пользователя по уроку."""
    try:
        db = get_db()
        
        # Получаем все вопросы урока
        questions = get_questions_by_lesson(db, lesson_id)
        
        if not questions:
            logger.warning(f"Для урока {lesson_id} не найдено вопросов")
            return {
                "total": 0,
                "correct": 0,
                "percentage": 0.0
            }
        
        # Получаем ответы пользователя
        user_answers = get_user_answers_for_lesson(db, user_id, lesson_id)
        
        # Считаем правильные ответы
        correct_answers = sum(1 for answer in user_answers if answer.is_correct)
        
        percentage = (correct_answers / len(questions)) * 100.0 if questions else 0.0
        
        return {
            "total": len(questions),
            "correct": correct_answers,
            "percentage": percentage
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики ответов пользователя {user_id} по уроку {lesson_id}: {e}")
        return {
            "total": 0,
            "correct": 0,
            "percentage": 0.0
        }

def reset_lesson_progress(user_id: int, lesson_id: int) -> bool:
    """Сбрасывает прогресс пользователя по уроку (для повторного прохождения)."""
    try:
        db = get_db()
        
        # Удаляем старые ответы пользователя
        from sqlalchemy import delete
        from app.database.models import UserAnswer
        
        delete_stmt = delete(UserAnswer).where(
            UserAnswer.user_id == user_id,
            UserAnswer.lesson_id == lesson_id
        )
        db.execute(delete_stmt)
        
        # Сбрасываем прогресс
        update_user_progress(db, user_id, lesson_id, False, 0.0)
        
        logger.info(f"Сброшен прогресс пользователя {user_id} по уроку {lesson_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при сбросе прогресса пользователя {user_id} по уроку {lesson_id}: {e}")
        return False