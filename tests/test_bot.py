"""
Тесты для модуля бота.
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio

from telegram import Update, User as TelegramUser, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes

from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_courses_keyboard,
    get_lessons_keyboard,
    get_question_options_keyboard,
    get_progress_bar
)
from app.bot.stickers import (
    send_welcome_sticker,
    send_correct_answer_sticker,
    send_wrong_answer_sticker
)
from app.database.models import User, Course, Lesson, Question

class TestKeyboards(unittest.TestCase):
    """Тесты для функций создания клавиатур."""
    
    def test_main_menu_keyboard(self):
        """Тест создания главного меню."""
        keyboard = get_main_menu_keyboard()
        self.assertIsNotNone(keyboard)
        self.assertEqual(len(keyboard.keyboard), 2)  # 2 ряда кнопок
    
    def test_courses_keyboard(self):
        """Тест создания клавиатуры тем."""
        # Создаем тестовые курсы
        courses = [
            Course(id=1, name="Курс 1", description="Описание 1", order=1),
            Course(id=2, name="Курс 2", description="Описание 2", order=2)
        ]
        
        keyboard = get_courses_keyboard(courses)
        self.assertIsNotNone(keyboard)
        self.assertEqual(len(keyboard.inline_keyboard), 3)  # 2 курса + кнопка "Назад"
    
    def test_lessons_keyboard(self):
        """Тест создания клавиатуры уроков."""
        # Создаем тестовые уроки
        lessons = [
            Lesson(id=1, course_id=1, title="Урок 1", content="Содержание 1", order=1),
            Lesson(id=2, course_id=1, title="Урок 2", content="Содержание 2", order=2)
        ]
        
        available_lessons = [True, False]  # Первый урок доступен, второй заблокирован
        
        keyboard = get_lessons_keyboard(lessons, available_lessons)
        self.assertIsNotNone(keyboard)
        self.assertEqual(len(keyboard.inline_keyboard), 3)  # 2 урока + кнопка "К темам"
        
        # Проверяем, что первая кнопка содержит callback_data с id урока
        self.assertTrue(keyboard.inline_keyboard[0][0].callback_data.startswith("lesson_1"))
        
        # Проверяем, что вторая кнопка содержит callback_data "lesson_locked"
        self.assertEqual(keyboard.inline_keyboard[1][0].callback_data, "lesson_locked")
    
    def test_question_options_keyboard(self):
        """Тест создания клавиатуры вариантов ответов."""
        # Создаем тестовый вопрос
        options = json.dumps(["Вариант A", "Вариант B", "Вариант C", "Вариант D"])
        question = Question(
            id=1,
            lesson_id=1,
            text="Тестовый вопрос?",
            options=options,
            correct_answer="A",
            explanation="Объяснение"
        )
        
        keyboard = get_question_options_keyboard(question)
        self.assertIsNotNone(keyboard)
        self.assertEqual(len(keyboard.inline_keyboard), 4)  # 4 варианта ответа
        
        # Проверяем, что первая кнопка соответствует варианту A
        self.assertTrue(keyboard.inline_keyboard[0][0].text.startswith("A."))
        self.assertTrue(keyboard.inline_keyboard[0][0].callback_data.startswith("answer_1_A"))
    
    def test_progress_bar(self):
        """Тест создания прогресс-бара."""
        # Тестируем прогресс 0%
        progress_0 = get_progress_bar(0)
        self.assertEqual(progress_0, "□□□□□□□□□□ 0.0%")
        
        # Тестируем прогресс 50%
        progress_50 = get_progress_bar(50)
        self.assertEqual(progress_50, "■■■■■□□□□□ 50.0%")
        
        # Тестируем прогресс 100%
        progress_100 = get_progress_bar(100)
        self.assertEqual(progress_100, "■■■■■■■■■■ 100.0%")

class TestStickers(unittest.TestCase):
    """Тесты для функций отправки стикеров."""
    
    async def test_send_welcome_sticker(self):
        """Тест отправки приветственного стикера."""
        # Создаем мок контекста
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_sticker = AsyncMock()
        
        # Вызываем функцию
        chat_id = 123456
        await send_welcome_sticker(context, chat_id)
        
        # Проверяем, что функция отправки стикера была вызвана
        context.bot.send_sticker.assert_called_once()
    
    async def test_send_correct_answer_sticker(self):
        """Тест отправки стикера правильного ответа."""
        # Создаем мок контекста
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_sticker = AsyncMock()
        
        # Вызываем функцию для первого правильного ответа
        chat_id = 123456
        await send_correct_answer_sticker(context, chat_id, is_first=True)
        
        # Проверяем, что функция отправки стикера была вызвана
        context.bot.send_sticker.assert_called_once()
        
        # Сбрасываем вызовы
        context.bot.send_sticker.reset_mock()
        
        # Вызываем функцию для последующего правильного ответа
        await send_correct_answer_sticker(context, chat_id, is_first=False)
        
        # Проверяем, что функция отправки стикера была вызвана второй раз
        context.bot.send_sticker.assert_called_once()
    
    async def test_send_wrong_answer_sticker(self):
        """Тест отправки стикера неправильного ответа."""
        # Создаем мок контекста
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_sticker = AsyncMock()
        
        # Вызываем функцию для первого неправильного ответа
        chat_id = 123456
        await send_wrong_answer_sticker(context, chat_id, is_first=True)
        
        # Проверяем, что функция отправки стикера была вызвана
        context.bot.send_sticker.assert_called_once()
        
        # Сбрасываем вызовы
        context.bot.send_sticker.reset_mock()
        
        # Вызываем функцию для последующего неправильного ответа
        await send_wrong_answer_sticker(context, chat_id, is_first=False)
        
        # Проверяем, что функция отправки стикера была вызвана второй раз
        context.bot.send_sticker.assert_called_once()

# Для запуска асинхронных тестов
def run_async_test(test_func):
    """Функция для запуска асинхронных тестов."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_func())

if __name__ == '__main__':
    # Запускаем тесты для клавиатур
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKeyboards)
    unittest.TextTestRunner().run(suite)
    
    # Запускаем асинхронные тесты для стикеров
    for test_name in dir(TestStickers):
        if test_name.startswith("test_"):
            test_method = getattr(TestStickers, test_name)
            run_async_test(test_method)