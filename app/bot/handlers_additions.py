"""
Дополнительные обработчики для интеграции с агентами.
"""
import logging
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.config import START_COMMANDS
from app.database.models import get_db
from app.database.operations import (
    get_or_create_user,
    update_user_activity,
    get_all_courses
)
from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_courses_keyboard
)
from app.bot.handlers_menu import show_progress

logger = logging.getLogger(__name__)

async def handle_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки "Задать вопрос по уроку"."""
    query = update.callback_query
    
    # Получаем ID урока из callback_data
    lesson_id = int(query.data.replace("ask_question_", ""))
    
    # Пытаемся импортировать функцию из handlers_lesson
    try:
        from app.bot.handlers_lesson import handle_user_question
        await handle_user_question(update, context, lesson_id)
    except ImportError:
        # Если модуль не найден, используем базовую функциональность
        await query.message.edit_text(
            "❓ Функция вопросов по уроку временно недоступна.\n"
            "Пожалуйста, обратитесь к материалам урока или попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Вернуться к уроку", callback_data=f"lesson_{lesson_id}")]
            ])
        )

async def handle_message_with_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения с учетом возможного вопроса по уроку."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    message_text = update.message.text.lower()
    
    # Получаем пользователя из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    update_user_activity(db, db_user.id)
    
    # Проверяем, ожидаем ли вопрос от пользователя
    if context.user_data.get('waiting_for_question', False):
        # Пытаемся использовать функцию обработки вопроса из handlers_lesson
        try:
            from app.bot.handlers_lesson import process_user_question
            await process_user_question(update, context)
            return
        except ImportError:
            # Если модуль не найден, используем базовую обработку
            await update.message.reply_text(
                "К сожалению, функция обработки вопросов временно недоступна.\n"
                "Попробуйте обратиться к материалам урока."
            )
            context.user_data['waiting_for_question'] = False
            return
    
    # Обработка команд запуска
    if message_text in [cmd.lower() for cmd in START_COMMANDS]:
        from app.bot.handlers import start
        await start(update, context)
        return
    
    # Обработка выбора пункта меню
    if message_text == "📚 обучение":
        courses = get_all_courses(db)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Выберите тему для изучения:",
            reply_markup=get_courses_keyboard(courses)
        )
    
    elif message_text == "📊 мой прогресс":
        await show_progress(update, context)
    
    elif message_text == "ℹ️ инструкция":
        instructions = (
            "📋 **Инструкция по работе с ботом**\n\n"
            "1️⃣ **Структура обучения**:\n"
            "   • Обучение разделено на темы\n"
            "   • Каждая тема содержит несколько уроков\n"
            "   • После каждого урока вы ответите на вопросы\n\n"
            
            "2️⃣ **Прохождение уроков**:\n"
            "   • Уроки открываются последовательно\n"
            "   • Для перехода к следующему уроку необходимо правильно ответить на 80% вопросов\n"
            "   • Урок можно проходить повторно\n\n"
            
            "3️⃣ **Ответы на вопросы**:\n"
            "   • После каждого урока вам будет предложено ответить на 3 вопроса\n"
            "   • Выбирайте один из предложенных вариантов ответа\n"
            "   • После ответа вы получите объяснение\n"
            "   • При неправильном ответе вы получите дополнительные пояснения\n\n"
            
            "4️⃣ **Интерактивные возможности**:\n"
            "   • Вы можете задавать вопросы по материалу урока\n"
            "   • Система адаптируется к вашему уровню знаний\n"
            "   • Сложность и объяснения подстраиваются под ваши потребности\n\n"
            
            "5️⃣ **Прогресс обучения**:\n"
            "   • В разделе 'Мой прогресс' вы можете увидеть пройденные и доступные уроки\n"
            "   • Прогресс обучения сохраняется между сессиями\n\n"
            
            "Желаем успешного обучения! 🚀"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=instructions,
            parse_mode="Markdown"
        )
    
    else:
        # Если не распознали команду, предлагаем варианты
        await context.bot.send_message(
            chat_id=chat_id,
            text="Выберите действие из меню:",
            reply_markup=get_main_menu_keyboard()
        )

def update_callback_handler(original_handler):
    """
    Декоратор для добавления обработки новых типов callback данных
    в существующий обработчик callback запросов.
    """
    async def updated_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            callback_data = query.data
            
            # Подтверждаем получение callback запроса
            await query.answer()
            
            # Добавляем обработку новых типов callback данных
            if callback_data.startswith("ask_question_"):
                await handle_ask_question(update, context)
                return
            
            # Если это не новый тип callback, вызываем оригинальный обработчик
            await original_handler(update, context)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке callback: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                await query.message.reply_text(
                    "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз."
                )
            except:
                # Если не удается отправить сообщение, просто логируем
                logger.error("Не удалось отправить сообщение об ошибке пользователю")
    
    return updated_handler