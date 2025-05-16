"""
Тесты для модуля обучения.
"""
import unittest
import json
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, User, Course, Lesson, Question, UserProgress, UserAnswer
from app.learning.courses import COURSES, init_courses
from app.learning.lessons import LESSONS, init_lessons
from app.learning.questions import (
    check_answer,
    get_explanation,
    check_lesson_completion,
    get_correct_answers_count
)

# Моки для функций, которые требуют доступа к базе данных
def mock_get_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

class TestLearning(unittest.TestCase):
    """Тесты для модуля обучения."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        # Создаем БД в памяти
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Создаем тестовые данные
        self.create_test_data()
    
    def tearDown(self):
        """Очистка после каждого теста."""
        self.session.close()
    
    def create_test_data(self):
        """Создает тестовые данные в базе."""
        # Создаем пользователя
        self.user = User(
            telegram_id=123456,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        self.session.add(self.user)
        
        # Создаем курс
        self.course = Course(
            name="Тестовый курс",
            description="Описание тестового курса",
            order=1
        )
        self.session.add(self.course)
        
        # Создаем урок
        self.lesson = Lesson(
            course_id=1,  # ID будет 1 после добавления в сессию
            title="Тестовый урок",
            content="Содержание тестового урока",
            order=1
        )
        self.session.add(self.lesson)
        
        # Создаем вопросы
        options = json.dumps(["Вариант A", "Вариант B", "Вариант C", "Вариант D"])
        
        self.question1 = Question(
            lesson_id=1,  # ID будет 1 после добавления в сессию
            text="Тестовый вопрос 1?",
            options=options,
            correct_answer="A",
            explanation="Объяснение правильного ответа 1"
        )
        self.session.add(self.question1)
        
        self.question2 = Question(
            lesson_id=1,
            text="Тестовый вопрос 2?",
            options=options,
            correct_answer="B",
            explanation="Объяснение правильного ответа 2"
        )
        self.session.add(self.question2)
        
        self.question3 = Question(
            lesson_id=1,
            text="Тестовый вопрос 3?",
            options=options,
            correct_answer="C",
            explanation="Объяснение правильного ответа 3"
        )
        self.session.add(self.question3)
        
        # Создаем прогресс пользователя
        self.progress = UserProgress(
            user_id=1,
            lesson_id=1,
            is_completed=False,
            success_percentage=0.0
        )
        self.session.add(self.progress)
        
        # Добавляем ответы пользователя
        self.answer1 = UserAnswer(
            user_id=1,
            question_id=1,
            answer="A",
            is_correct=True
        )
        self.session.add(self.answer1)
        
        self.answer2 = UserAnswer(
            user_id=1,
            question_id=2,
            answer="C",
            is_correct=False
        )
        self.session.add(self.answer2)
        
        # Сохраняем все изменения
        self.session.commit()
    
    @patch('app.learning.questions.get_db', side_effect=mock_get_db)
    def test_check_answer(self, mock_get_db):
        """Тест функции проверки ответа."""
        # Для имитации проверки ответа
        # Тест с правильным ответом
        with patch('app.database.operations.create_user_answer') as mock_create_answer:
            mock_create_answer.return_value = self.answer1
            
            with patch('app.learning.questions.get_question') as mock_get_question:
                mock_get_question.return_value = self.question1
                
                result = check_answer(1, 1, "A")
                self.assertTrue(result)
                
                mock_get_question.assert_called_once_with(mock_get_db(), 1)
                mock_create_answer.assert_called_once()
        
        # Тест с неправильным ответом
        with patch('app.database.operations.create_user_answer') as mock_create_answer:
            mock_create_answer.return_value = self.answer2
            
            with patch('app.learning.questions.get_question') as mock_get_question:
                mock_get_question.return_value = self.question2
                
                result = check_answer(2, 1, "C")
                self.assertFalse(result)
                
                mock_get_question.assert_called_once_with(mock_get_db(), 2)
                mock_create_answer.assert_called_once()
    
    @patch('app.learning.questions.get_db', side_effect=mock_get_db)
    def test_get_explanation(self, mock_get_db):
        """Тест функции получения объяснения."""
        with patch('app.learning.questions.get_question') as mock_get_question:
            mock_get_question.return_value = self.question1
            
            explanation = get_explanation(1)
            self.assertEqual(explanation, "Объяснение правильного ответа 1")
            
            mock_get_question.assert_called_once_with(mock_get_db(), 1)
    
    @patch('app.learning.questions.get_db', side_effect=mock_get_db)
    def test_course_structure(self, mock_get_db):
        """Тест структуры курсов и уроков."""
        # Проверяем, что определены курсы
        self.assertIsInstance(COURSES, list)
        self.assertTrue(len(COURSES) > 0)
        
        # Проверяем, что определены уроки
        self.assertIsInstance(LESSONS, dict)
        self.assertTrue(len(LESSONS) > 0)
        
        # Проверяем, что все ID курсов есть в уроках
        for course_idx, course in enumerate(COURSES, 1):
            self.assertIn(course_idx, LESSONS)
            
            # Проверяем, что у каждого курса есть уроки
            course_lessons = LESSONS[course_idx]
            self.assertTrue(len(course_lessons) > 0)
            
            # Проверяем структуру уроков
            for lesson in course_lessons:
                self.assertIn("title", lesson)
                self.assertIn("content", lesson)
                self.assertIn("order", lesson)

if __name__ == '__main__':
    unittest.main()