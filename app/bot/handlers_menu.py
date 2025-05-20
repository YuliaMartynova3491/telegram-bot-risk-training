"""
Модуль для обработки меню и навигации по урокам.
"""
import logging
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.models import get_db
from app.database.operations import (
    get_or_create_user,
    update_user_activity,
    get_all_courses,
    get_course,
    get_lessons_by_course,
    get_user_progress,
    get_available_lessons,
    get_course_progress
)
from app.bot.keyboards import (
    get_courses_keyboard,
    get_lessons_keyboard,
    get_available_lessons_keyboard,
    get_progress_bar
)

logger = logging.getLogger(__name__)

async def show_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: int) -> None:
    """Показывает список уроков темы."""
    query = update.callback_query
    user = query.from_user
    
    # Получаем пользователя из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Получаем тему и уроки
    course = get_course(db, course_id)
    lessons = get_lessons_by_course(db, course_id)
    
    # Определяем доступность уроков
    available_lessons_data = get_available_lessons(db, db_user.id)
    
    # Фильтруем только уроки текущей темы
    available_lessons_current_course = [
        lesson_data for lesson_data in available_lessons_data
        if lesson_data["course"].id == course_id
    ]
    
    # ИСПРАВЛЕНИЕ: Всегда делаем первый урок первой темы доступным
    if course_id == 1 and available_lessons_current_course:
        available_lessons_current_course[0]["is_available"] = True
    
    # Создаем список доступности уроков
    available = [lesson_data["is_available"] for lesson_data in available_lessons_current_course]
    
    # Формируем сообщение
    message = f"📘 *{course.name}*\n\nВыберите урок:"
    
    # Редактируем сообщение
    await query.message.edit_text(
        message,
        reply_markup=get_lessons_keyboard(lessons, available),
        parse_mode="Markdown"
    )

async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает прогресс обучения пользователя."""
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        user = query.from_user
        message_obj = query.message
    else:
        chat_id = update.effective_chat.id
        user = update.effective_user
        message_obj = None
    
    # Получаем пользователя из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Получаем доступные уроки
    available_lessons_data = get_available_lessons(db, db_user.id)
    
    # ИСПРАВЛЕНИЕ: Всегда делаем первый урок первой темы доступным
    if available_lessons_data:
        for lesson_data in available_lessons_data:
            if lesson_data["course"].id == 1 and lesson_data["lesson"].order == 1:
                lesson_data["is_available"] = True
                break
    
    # Если нет данных о прогрессе, показываем сообщение
    if not available_lessons_data:
        message = "📊 *Ваш прогресс обучения*\n\nВы еще не начали обучение. Выберите тему и начните изучение!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Начать обучение", callback_data="course_1")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ])
    else:
        # Формируем сообщение с прогрессом
        message = "📊 *Ваш прогресс обучения*\n\n"
        
        # Добавляем прогресс по темам
        courses = get_all_courses(db)
        for course in courses:
            course_progress = get_course_progress(db, db_user.id, course.id)
            message += f"📘 *{course.name}*: {get_progress_bar(course_progress)}\n\n"
        
        message += "Выберите урок для продолжения обучения:"
        
        # Создаем клавиатуру с доступными уроками
        keyboard = get_available_lessons_keyboard(available_lessons_data)
    
    # Отправляем или редактируем сообщение
    if message_obj:
        await message_obj.edit_text(
            message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )