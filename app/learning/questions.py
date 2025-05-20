"""
Модуль для генерации вопросов и работы с ними.
"""
import json
import random
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
from app.config import QUESTIONS_PER_LESSON, MIN_SUCCESS_PERCENTAGE, RISK_KNOWLEDGE_PATH

def load_knowledge_base(path: str = RISK_KNOWLEDGE_PATH) -> List[Dict[str, Any]]:
    """Загружает базу знаний из JSONL файла."""
    knowledge_base = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Проверяем, что строка не пустая
                    knowledge_base.append(json.loads(line))
        return knowledge_base
    except FileNotFoundError:
        print(f"Файл базы знаний не найден: {path}")
        return []
    except json.JSONDecodeError:
        print(f"Ошибка декодирования JSON в файле: {path}")
        return []

def generate_questions_for_lesson(lesson_id: int, topic: str, difficulty: str = "средний") -> List[Dict[str, Any]]:
    """Генерирует вопросы для урока."""
    db = get_db()
    
    # Проверяем, есть ли уже вопросы для этого урока
    existing_questions = get_questions_by_lesson(db, lesson_id)
    
    if existing_questions:
        return existing_questions
    
    # Используем прямое создание вопросов из базы знаний
    # ИСПРАВЛЕНИЕ: Вместо использования RAG напрямую, используем локальную генерацию
    # из имеющейся базы знаний
    
    # Загружаем базу знаний
    knowledge_base = load_knowledge_base()
    if not knowledge_base:
        print("Ошибка: база знаний пуста")
        return []
    
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
    for item in selected_items:
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
        create_question(
            db,
            lesson_id=lesson_id,
            text=question_text,
            options=json.dumps(options, ensure_ascii=False),
            correct_answer=correct_letter,
            explanation=correct_answer
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