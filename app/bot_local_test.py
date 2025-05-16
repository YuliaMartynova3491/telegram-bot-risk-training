"""
Локальный тест бота без подключения к Telegram API.
"""
import sys
import os
import json
import random
from typing import List, Dict, Any

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import init_db, Base, User, Course, Lesson, Question, UserProgress, UserAnswer
from app.database.operations import get_or_create_user, create_course, create_lesson, create_question
from app.knowledge.rag_simple import generate_questions, convert_questions_for_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def setup_test_db():
    """Создает тестовую базу данных в памяти."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def create_test_data(session):
    """Создает тестовые данные."""
    # Создание пользователя
    user = get_or_create_user(session, telegram_id=123456, username="test_user", first_name="Test", last_name="User")
    
    # Создание курса
    course = create_course(session, name="Тестовый курс", description="Описание тестового курса", order=1)
    
    # Создание урока
    lesson = create_lesson(session, course_id=course.id, title="Тестовый урок", content="Содержание тестового урока", order=1)
    
    # Генерация вопросов
    questions_data = [
        {
            "question": "Что такое риск нарушения непрерывности деятельности?",
            "options": ["Риск нарушения способности поддерживать операционную устойчивость.", "Риск финансовых потерь.", "Риск утечки информации.", "Риск киберугроз."],
            "correct_answer": "A",
            "explanation": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость."
        },
        {
            "question": "Что такое угроза непрерывности?",
            "options": ["Обстановка, сложившаяся в результате аварии или стихийного бедствия.", "Нарушение графика работы.", "Отсутствие персонала.", "Недостаток финансирования."],
            "correct_answer": "A",
            "explanation": "Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы и т.д."
        },
        {
            "question": "Как связан риск нарушения непрерывности с операционным риском?",
            "options": ["Является его подвидом.", "Не связан.", "Является его причиной.", "Является его следствием."],
            "correct_answer": "A",
            "explanation": "Риск нарушения непрерывности является подвидом операционного риска."
        }
    ]
    
    # Преобразование вопросов для базы данных
    db_questions = convert_questions_for_db(questions_data, lesson.id)
    
    # Сохранение вопросов в базе данных
    for question_data in db_questions:
        create_question(
            session,
            lesson_id=question_data["lesson_id"],
            text=question_data["text"],
            options=question_data["options"],
            correct_answer=question_data["correct_answer"],
            explanation=question_data["explanation"]
        )
    
    return user, course, lesson

def test_rag_generation():
    """Тестирует генерацию вопросов с помощью RAG."""
    print("Тестирование генерации вопросов с помощью RAG...")
    
    questions = generate_questions(
        topic="риск_нарушения_непрерывности", 
        difficulty="средний", 
        num_questions=3
    )
    
    if questions:
        print(f"Успешно сгенерировано {len(questions)} вопросов.")
        for i, q in enumerate(questions, 1):
            print(f"\nВопрос {i}: {q['question']}")
            for j, option in enumerate(q['options']):
                print(f"  {chr(65 + j)}. {option}")
            print(f"Правильный ответ: {q['correct_answer']}")
    else:
        print("Ошибка: не удалось сгенерировать вопросы.")

def main():
    """Основная функция для тестирования бота."""
    print("Запуск локального тестирования бота...")
    
    # Настройка тестовой базы данных
    session = setup_test_db()
    
    # Создание тестовых данных
    user, course, lesson = create_test_data(session)
    
    print("\nСозданные тестовые данные:")
    print(f"Пользователь: {user.first_name} {user.last_name} (@{user.username})")
    print(f"Курс: {course.name}")
    print(f"Урок: {lesson.title}")
    
    # Тестирование генерации вопросов
    test_rag_generation()
    
    print("\nЛокальное тестирование завершено.")

if __name__ == "__main__":
    main()
