"""
Модуль для обработчиков Telegram бота.
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from app.config import TELEGRAM_TOKEN, START_COMMANDS, MIN_SUCCESS_PERCENTAGE
from app.database.models import get_db, init_db
from app.database.operations import (
    get_or_create_user,
    update_user_activity,
    get_all_courses,
    get_course,
    get_lessons_by_course,
    get_lesson,
    get_next_lesson,
    get_available_lessons,
    get_user_progress,
    get_or_create_user_progress,
    update_user_progress,
    calculate_lesson_success_percentage
)
from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_courses_keyboard,
    get_lessons_keyboard,
    get_question_options_keyboard,
    get_continue_keyboard,
    get_available_lessons_keyboard,
    get_progress_bar,
    get_start_test_keyboard
)
from app.bot.stickers import (
    send_welcome_sticker,
    send_correct_answer_sticker,
    send_wrong_answer_sticker,
    send_lesson_success_sticker,
    send_topic_success_sticker,
    send_lesson_fail_sticker
)
from app.learning.courses import init_courses
from app.learning.lessons import init_lessons
from app.learning.questions import (
    generate_questions_for_lesson,
    get_options_for_question,
    check_answer,
    get_explanation,
    check_lesson_completion,
    get_correct_answers_count
)
from app.bot.handlers_extra import (
    handle_answer_selection,
    handle_retry_question,
    handle_next_question,
    send_question,
    show_lesson_results
)
from app.bot.handlers_menu import show_lessons, show_progress

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных и данных
def init_data():
    """Инициализирует базу данных и данные."""
    try:
        # Инициализируем базу данных
        init_db()
        
        # Инициализируем темы
        courses = init_courses()
        
        # Инициализируем уроки для каждой темы
        for course in courses:
            init_lessons(course.id)
            
        logger.info("База данных и учебные материалы успешно инициализированы")
    except Exception as e:
        logger.error(f"Ошибка при инициализации данных: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Обработчики команд и сообщений

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Создаем пользователя в базе данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    update_user_activity(db, db_user.id)
    
    # Отправляем приветственный стикер
    await send_welcome_sticker(context, chat_id)
    
    # Отправляем приветственное сообщение
    welcome_message = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для обучения рискам нарушения непрерывности деятельности.\n\n"
        "Здесь ты сможешь изучить:\n"
        "📌 Основные понятия рисков нарушения непрерывности\n"
        "📌 Методы оценки критичности процессов\n"
        "📌 Подходы к оценке и минимизации рисков\n\n"
        "Выбери пункт меню, чтобы начать:"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_message,
        reply_markup=get_main_menu_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения."""
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
    
    # Обработка команд запуска
    if message_text in [cmd.lower() for cmd in START_COMMANDS]:
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
            "   • При неправильном ответе вы можете попробовать ответить еще раз\n\n"
            
            "4️⃣ **Прогресс обучения**:\n"
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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на инлайн-кнопки."""
    try:
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat_id
        
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
        
        # Обрабатываем callback data
        callback_data = query.data
        
        # Подтверждаем получение callback запроса
        await query.answer()
        
        # Обработка выбора темы
        if callback_data.startswith("course_"):
            if callback_data.startswith("course_info_"):
                course_id = int(callback_data.replace("course_info_", ""))
                course = get_course(db, course_id)
                await query.message.reply_text(
                    f"ℹ️ *{course.name}*\n\n{course.description}",
                    parse_mode="Markdown"
                )
            else:
                course_id = int(callback_data.replace("course_", ""))
                await show_lessons(update, context, course_id)
        
        # Обработка выбора урока
        elif callback_data.startswith("lesson_"):
            if callback_data == "lesson_locked":
                await query.message.reply_text(
                    "🔒 Этот урок пока недоступен. Сначала пройдите предыдущие уроки."
                )
            else:
                lesson_id = int(callback_data.replace("lesson_", ""))
                await show_lesson(update, context, lesson_id)
        
        # Обработка начала теста
        elif callback_data.startswith("start_test_"):
            lesson_id = int(callback_data.replace("start_test_", ""))
            await start_test(update, context, lesson_id)
        
        # Обработка ответа на вопрос
        elif callback_data.startswith("answer_"):
            parts = callback_data.split("_")
            question_id = int(parts[1])
            answer_letter = parts[2]
            
            # Используем выделенную функцию для обработки выбора ответа
            await handle_answer_selection(update, context, question_id, answer_letter)
        
        # Обработка кнопки "Попробовать еще раз"
        elif callback_data.startswith("retry_question_"):
            await handle_retry_question(update, context)
        
        # Обработка кнопки "Следующий вопрос"
        elif callback_data.startswith("next_question_"):
            await handle_next_question(update, context)
        
        # Возврат к меню тем
        elif callback_data == "back_to_courses":
            courses = get_all_courses(db)
            await query.message.edit_text(
                "Выберите тему для изучения:",
                reply_markup=get_courses_keyboard(courses)
            )
        
        # Возврат в главное меню
        elif callback_data == "back_to_main":
            await query.message.delete()
            await context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие из меню:",
                reply_markup=get_main_menu_keyboard()
            )
        
        # Показать прогресс
        elif callback_data == "progress":
            await show_progress(update, context)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.message.reply_text(
            "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз."
        )

async def show_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Показывает содержимое урока."""
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    
    # Получаем пользователя из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Получаем урок
    lesson = get_lesson(db, lesson_id)
    
    if not lesson:
        await query.message.reply_text("⚠️ Урок не найден.")
        return
    
    # Создаем или получаем прогресс пользователя по уроку
    progress = get_or_create_user_progress(db, db_user.id, lesson_id)
    
    # Удаляем предыдущее сообщение
    await query.message.delete()
    
    # Разбиваем содержимое на части, если оно слишком длинное
    content = lesson.content
    max_length = 4000  # Максимальная длина сообщения в Telegram
    
    if len(content) <= max_length:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 *{lesson.title}*\n\n{content}",
            parse_mode="Markdown"
        )
    else:
        # Отправляем заголовок
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 *{lesson.title}*",
            parse_mode="Markdown"
        )
        
        # Отправляем содержимое частями
        chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
        for chunk in chunks:
            await context.bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode="Markdown"
            )
    
    # Отправляем предложение пройти тест
    await context.bot.send_message(
        chat_id=chat_id,
        text="Теперь давайте проверим ваши знания. Готовы ответить на несколько вопросов?",
        reply_markup=get_start_test_keyboard(lesson_id)
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Начинает тестирование по уроку."""
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    
    # Получаем пользователя из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Получаем урок
    lesson = get_lesson(db, lesson_id)
    course = get_course(db, lesson.course_id)
    
    # Создаем или получаем прогресс пользователя по уроку
    progress = get_or_create_user_progress(db, db_user.id, lesson_id)
    
    # Генерируем вопросы для урока
    topic = course.name.lower().replace(" ", "_")
    questions = generate_questions_for_lesson(lesson_id, topic)
    
    if not questions:
        await query.message.edit_text(
            "⚠️ Не удалось сгенерировать вопросы. Пожалуйста, попробуйте позже."
        )
        return
    
    # Сохраняем информацию о тесте в контексте
    context.user_data.setdefault('lesson_data', {})
    context.user_data['lesson_data'].setdefault(lesson_id, {
        'current_question': 0,
        'correct_answers': 0,
        'wrong_answers_streak': 0
    })
    
    # Отправляем первый вопрос
    await query.message.delete()
    await send_question(update, context, lesson_id, questions[0].id)

def run_bot(error_handler=None):
    """Запускает Telegram бота."""
    logger.info("Инициализация бота...")
    
    # Инициализация данных
    init_data()
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавление обработчика ошибок, если предоставлен
    if error_handler:
        application.add_error_handler(error_handler)
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запуск бота
    logger.info("Запуск бота...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)