"""
Тесты для модуля базы данных.
"""
import unittest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, User, Course, Lesson, Question, UserProgress, UserAnswer
from app.database.operations import (
    get_user_by_telegram_id,
    create_user,
    get_or_create_user,
    create_course,
    get_all_courses,
    get_course,
    create_lesson,
    get_lessons_by_course,
    get_lesson,
    create_question,
    get_questions_by_lesson
)

class TestDatabase(unittest.TestCase):
    """Тесты для базы данных."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        # Создаем временную базу данных SQLite в памяти
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def tearDown(self):
        """Очистка после каждого теста."""
        self.session.close()
    
    def test_user_operations(self):
        """Тестирование операций с пользователями."""
        # Создание пользователя
        user = create_user(
            self.session,
            telegram_id=123456,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        
        # Проверка создания пользователя
        self.assertIsNotNone(user)
        self.assertEqual(user.telegram_id, 123456)
        self.assertEqual(user.username, "test_user")
        
        # Получение пользователя по Telegram ID
        found_user = get_user_by_telegram_id(self.session, 123456)
        self.assertIsNotNone(found_user)
        self.assertEqual(found_user.id, user.id)
        
        # Получение несуществующего пользователя
        missing_user = get_user_by_telegram_id(self.session, 999999)
        self.assertIsNone(missing_user)
        
        # Получение или создание существующего пользователя
        existing_user = get_or_create_user(
            self.session,
            telegram_id=123456,
            username="updated_user",
            first_name="Updated",
            last_name="User"
        )
        self.assertEqual(existing_user.id, user.id)
        
        # Получение или создание нового пользователя
        new_user = get_or_create_user(
            self.session,
            telegram_id=654321,
            username="new_user",
            first_name="New",
            last_name="User"
        )
        self.assertNotEqual(new_user.id, user.id)
        self.assertEqual(new_user.telegram_id, 654321)
    
    def test_course_operations(self):
        """Тестирование операций с курсами."""
        # Создание курса
        course = create_course(
            self.session,
            name="Тестовый курс",
            description="Описание тестового курса",
            order=1
        )
        
        # Проверка создания курса
        self.assertIsNotNone(course)
        self.assertEqual(course.name, "Тестовый курс")
        
        # Получение всех курсов
        courses = get_all_courses(self.session)
        self.assertEqual(len(courses), 1)
        
        # Получение курса по ID
        found_course = get_course(self.session, course.id)
        self.assertIsNotNone(found_course)
        self.assertEqual(found_course.id, course.id)
    
    def test_lesson_operations(self):
        """Тестирование операций с уроками."""
        # Создание курса
        course = create_course(
            self.session,
            name="Тестовый курс",
            description="Описание тестового курса",
            order=1
        )
        
        # Создание урока
        lesson = create_lesson(
            self.session,
            course_id=course.id,
            title="Тестовый урок",
            content="Содержание тестового урока",
            order=1
        )
        
        # Проверка создания урока
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson.title, "Тестовый урок")
        
        # Получение уроков по курсу
        lessons = get_lessons_by_course(self.session, course.id)
        self.assertEqual(len(lessons), 1)
        
        # Получение урока по ID
        found_lesson = get_lesson(self.session, lesson.id)
        self.assertIsNotNone(found_lesson)
        self.assertEqual(found_lesson.id, lesson.id)
    
    def test_question_operations(self):
        """Тестирование операций с вопросами."""
        # Создание курса и урока
        course = create_course(
            self.session,
            name="Тестовый курс",
            description="Описание тестового курса",
            order=1
        )
        
        lesson = create_lesson(
            self.session,
            course_id=course.id,
            title="Тестовый урок",
            content="Содержание тестового урока",
            order=1
        )
        
        # Создание вопроса
        options = ["Вариант A", "Вариант B", "Вариант C", "Вариант D"]
        question = create_question(
            self.session,
            lesson_id=lesson.id,
            text="Тестовый вопрос?",
            options=options,
            correct_answer="A",
            explanation="Объяснение правильного ответа"
        )
        
        # Проверка создания вопроса
        self.assertIsNotNone(question)
        self.assertEqual(question.text, "Тестовый вопрос?")
        
        # Получение вопросов по уроку
        questions = get_questions_by_lesson(self.session, lesson.id)
        self.assertEqual(len(questions), 1)

if __name__ == '__main__':
    unittest.main()