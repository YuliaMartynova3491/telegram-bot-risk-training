"""
Модуль для работы с Telegram ботом.

Этот модуль содержит компоненты для взаимодействия с Telegram API:
- handlers.py: Обработчики сообщений и команд
- keyboards.py: Функции для создания клавиатур и меню
- stickers.py: Функции для работы со стикерами
"""

from app.bot.stickers import (
    send_welcome_sticker,
    send_correct_answer_sticker,
    send_wrong_answer_sticker,
    send_lesson_success_sticker,
    send_topic_success_sticker,
    send_lesson_fail_sticker
)

from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_courses_keyboard,
    get_lessons_keyboard,
    get_question_options_keyboard,
    get_continue_keyboard,
    get_available_lessons_keyboard,
    get_progress_bar
)

__all__ = [
    # Стикеры
    'send_welcome_sticker',
    'send_correct_answer_sticker',
    'send_wrong_answer_sticker',
    'send_lesson_success_sticker',
    'send_topic_success_sticker',
    'send_lesson_fail_sticker',
    
    # Клавиатуры
    'get_main_menu_keyboard',
    'get_courses_keyboard',
    'get_lessons_keyboard',
    'get_question_options_keyboard',
    'get_continue_keyboard',
    'get_available_lessons_keyboard',
    'get_progress_bar'
]