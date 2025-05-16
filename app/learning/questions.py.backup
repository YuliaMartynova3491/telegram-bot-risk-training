"""
Модуль для генерации вопросов и работы с ними.
"""
import json
from typing import List, Dict, Any
from app.database.models import get_db
from app.database.operations import (
    create_question, 
    get_questions_by_lesson, 
    get_question,
    create_user_answer,
    get_user_answers_by_lesson,
    calculate_lesson_success_percentage,
    update_user_progress
)
from app.knowledge.rag import generate_questions as rag_generate_questions, convert_questions_for_db
from app.config import QUESTIONS_PER_LESSON, MIN_SUCCESS_PERCENTAGE

def generate_questions_for_lesson(lesson_id: int, topic: str, difficulty: str = "средний") -> List[Dict[str, Any]]:
    """Генерирует вопросы для урока."""
    db = get_db()
    
    # Проверяем, есть ли уже вопросы для этого урока
    existing_questions = get_questions_by_lesson(db, lesson_id)
    
    if existing_questions:
        return existing_questions
    
    # Генерируем новые вопросы с помощью RAG
    questions = rag_generate_questions(topic, difficulty, QUESTIONS_PER_LESSON)
    
    # Преобразуем вопросы в формат для базы данных
    db_questions = convert_questions_for_db(questions, lesson_id)
    
    # Сохраняем вопросы в базе данных
    for question_data in db_questions:
        create_question(
            db,
            lesson_id=question_data["lesson_id"],
            text=question_data["text"],
            options=question_data["options"],
            correct_answer=question_data["correct_answer"],
            explanation=question_data["explanation"]
        )
    
    # Получаем созданные вопросы
    return get_questions_by_lesson(db, lesson_id)

def get_options_for_question(question_id: int) -> List[str]:
    """Получает варианты ответов для вопроса."""
    db = get_db()
    question = get_question(db, question_id)
    
    if not question:
        return []
    
    try:
        return json.loads(question.options)
    except json.JSONDecodeError:
        return []

def check_answer(question_id: int, user_id: int, answer: str) -> bool:
    """Проверяет правильность ответа пользователя."""
    db = get_db()
    question = get_question(db, question_id)
    
    if not question:
        return False
    
    is_correct = (answer == question.correct_answer)
    
    # Сохраняем ответ пользователя
    create_user_answer(db, user_id, question_id, answer, is_correct)
    
    return is_correct

def get_explanation(question_id: int) -> str:
    """Получает объяснение правильного ответа."""
    db = get_db()
    question = get_question(db, question_id)
    
    if not question:
        return ""
    
    return question.explanation

def check_lesson_completion(user_id: int, lesson_id: int) -> Dict[str, Any]:
    """Проверяет завершение урока пользователем."""
    db = get_db()
    
    # Получаем все вопросы урока
    questions = get_questions_by_lesson(db, lesson_id)
    
    if not questions:
        return {
            "is_completed": False,
            "success_percentage": 0.0,
            "is_successful": False
        }
    
    # Получаем ответы пользователя
    user_answers = get_user_answers_by_lesson(db, user_id, lesson_id)
    
    # Если пользователь не ответил на все вопросы, урок не завершен
    if len(user_answers) < len(questions):
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
    update_user_progress(db, user_id, lesson_id, True, success_percentage)
    
    return {
        "is_completed": True,
        "success_percentage": success_percentage,
        "is_successful": is_successful
    }

def get_correct_answers_count(user_id: int, lesson_id: int) -> Dict[str, Any]:
    """Получает количество правильных ответов пользователя по уроку."""
    db = get_db()
    
    # Получаем все вопросы урока
    questions = get_questions_by_lesson(db, lesson_id)
    
    if not questions:
        return {
            "total": 0,
            "correct": 0,
            "percentage": 0.0
        }
    
    # Получаем ответы пользователя
    user_answers = get_user_answers_by_lesson(db, user_id, lesson_id)
    
    # Считаем правильные ответы
    correct_answers = sum(1 for answer in user_answers if answer.is_correct)
    
    return {
        "total": len(questions),
        "correct": correct_answers,
        "percentage": (correct_answers / len(questions)) * 100.0
    }