"""
Модуль для обработчиков Telegram бота.
"""
import logging
import json
import random
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
    calculate_lesson_success_percentage,
    get_course_progress,
    get_question
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

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных и данных
def init_data():
    """Инициализирует базу данных и данные."""
    # Инициализируем базу данных
    init_db()
    
    # Инициализируем темы
    courses = init_courses()
    
    # Инициализируем уроки для каждой темы
    for course in courses:
        init_lessons(course.id)

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
            "   • После ответа вы получите объяснение\n\n"
            
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
        answer = parts[2]
        await process_question_answer(update, context, question_id, answer)
    
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
    
    # Информация о теме
    elif callback_data.startswith("course_info_"):
        course_id = int(callback_data.replace("course_info_", ""))
        course = get_course(db, course_id)
        await query.message.reply_text(
            f"ℹ️ *{course.name}*\n\n{course.description}",
            parse_mode="Markdown"
        )

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
    
    # Отправляем содержимое урока
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"📝 *{lesson.title}*\n\n{lesson.content}",
        parse_mode="Markdown"
    )
    
    # Отправляем предложение пройти тест
    await context.bot.send_message(
        chat_id=chat_id,
        text="Теперь давайте проверим ваши знания. Готовы ответить на несколько вопросов?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Начать тест", callback_data=f"start_test_{lesson_id}")]
        ])
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
    
    # Сохраняем первый вопрос в контексте
    context.user_data['current_question'] = 0
    context.user_data['questions'] = [q.id for q in questions]
    context.user_data['lesson_id'] = lesson_id
    context.user_data['correct_answers'] = 0
    context.user_data['wrong_answers_streak'] = 0
    
    # Отправляем первый вопрос
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет вопрос пользователю."""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    # Получаем текущий вопрос
    current_question_index = context.user_data.get('current_question', 0)
    questions = context.user_data.get('questions', [])
    
    if current_question_index >= len(questions):
        # Если все вопросы заданы, показываем результаты
        await show_test_results(update, context)
        return
    
    # Получаем вопрос из базы данных
    db = get_db()
    question_id = questions[current_question_index]
    question = get_question(db, question_id)
    
    if not question:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при получении вопроса. Пожалуйста, попробуйте позже."
        )
        return
    
    # Формируем сообщение с вопросом
    question_number = current_question_index + 1
    total_questions = len(questions)
    
    message = (
        f"❓ *Вопрос {question_number} из {total_questions}*\n\n"
        f"{question.text}\n\n"
        "Выберите правильный ответ:"
    )
    
    # Отправляем вопрос с вариантами ответов
    keyboard = get_question_options_keyboard(question)
    
    if query.message:
        await query.message.edit_text(
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

async def process_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int, answer: str) -> None:
    """Обрабатывает ответ пользователя на вопрос."""
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
    
    # Проверяем ответ
    is_correct = check_answer(question_id, db_user.id, answer)
    
    # Обновляем счетчик правильных ответов
    if is_correct:
        context.user_data['correct_answers'] = context.user_data.get('correct_answers', 0) + 1
        context.user_data['wrong_answers_streak'] = 0
    else:
        context.user_data['wrong_answers_streak'] = context.user_data.get('wrong_answers_streak', 0) + 1
    
    # Получаем объяснение
    explanation = get_explanation(question_id)
    
    # Формируем сообщение с результатом
    if is_correct:
        # Отправляем стикер
        if context.user_data.get('correct_answers', 0) == 1:
            await send_correct_answer_sticker(context, chat_id, is_first=True)
        else:
            await send_correct_answer_sticker(context, chat_id, is_first=False)
        
        result_message = (
            "✅ *Правильно!*\n\n"
            f"{explanation}\n\n"
            "Переходим к следующему вопросу..."
        )
    else:
        # Отправляем стикер
        if context.user_data.get('wrong_answers_streak', 0) == 1:
            await send_wrong_answer_sticker(context, chat_id, is_first=True)
        else:
            await send_wrong_answer_sticker(context, chat_id, is_first=False)
        
        result_message = (
            "❌ *Неправильно*\n\n"
            f"{explanation}\n\n"
            "Переходим к следующему вопросу..."
        )
    
    # Отправляем сообщение с результатом
    await query.message.edit_text(
        result_message,
        parse_mode="Markdown"
    )
    
    # Переходим к следующему вопросу
    context.user_data['current_question'] = context.user_data.get('current_question', 0) + 1
    
    # Небольшая задержка перед следующим вопросом
    await asyncio.sleep(2)
    
    # Отправляем следующий вопрос
    await send_question(update, context)

async def show_test_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает результаты тестирования."""
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
    
    # Получаем данные теста
    lesson_id = context.user_data.get('lesson_id')
    correct_answers = context.user_data.get('correct_answers', 0)
    total_questions = len(context.user_data.get('questions', []))
    
    if total_questions == 0:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при подсчете результатов. Пожалуйста, попробуйте позже."
        )
        return
    
    # Вычисляем процент успешности
    success_percentage = (correct_answers / total_questions) * 100.0
    
    # Обновляем прогресс пользователя
    update_user_progress(db, db_user.id, lesson_id, True, success_percentage)
    
    # Определяем, успешно ли пройден тест
    is_successful = success_percentage >= MIN_SUCCESS_PERCENTAGE
    
    # Получаем урок и следующий урок
    lesson = get_lesson(db, lesson_id)
    next_lesson = get_next_lesson(db, lesson_id)
    
    # Формируем сообщение с результатами
    if is_successful:
        # Отправляем стикер успешного завершения урока
        await send_lesson_success_sticker(context, chat_id)
        
        result_message = (
            f"🎉 *Поздравляем!* Вы успешно прошли урок \"{lesson.title}\".\n\n"
            f"Ваш результат: {correct_answers} из {total_questions} ({success_percentage:.1f}%)\n\n"
            f"Прогресс: {get_progress_bar(success_percentage)}\n\n"
            "Вы можете перейти к следующему уроку или вернуться к списку уроков."
        )
        
        # Если это последний урок в теме, отправляем стикер успешного завершения темы
        if not next_lesson or next_lesson.course_id != lesson.course_id:
            await send_topic_success_sticker(context, chat_id)
    else:
        # Отправляем стикер неуспешного завершения урока
        await send_lesson_fail_sticker(context, chat_id)
        
        result_message = (
            f"📊 Результаты теста по уроку \"{lesson.title}\":\n\n"
            f"Вы ответили правильно на {correct_answers} из {total_questions} вопросов ({success_percentage:.1f}%)\n\n"
            f"Прогресс: {get_progress_bar(success_percentage)}\n\n"
            f"Для перехода к следующему уроку необходимо набрать не менее {MIN_SUCCESS_PERCENTAGE}%.\n"
            "Рекомендуем повторить материал и пройти тест еще раз."
        )
    
    # Создаем клавиатуру с кнопками действий
    keyboard = []
    
    if is_successful and next_lesson:
        keyboard.append([
            InlineKeyboardButton("▶️ Следующий урок", callback_data=f"lesson_{next_lesson.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Пройти урок заново", callback_data=f"lesson_{lesson_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("📋 К списку уроков", callback_data=f"course_{lesson.course_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
    ])
    
    # Отправляем сообщение с результатами
    await query.message.edit_text(
        result_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    # Очищаем данные теста
    context.user_data.pop('current_question', None)
    context.user_data.pop('questions', None)
    context.user_data.pop('lesson_id', None)
    context.user_data.pop('correct_answers', None)
    context.user_data.pop('wrong_answers_streak', None)

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

def run_bot():
    """Запускает Telegram бота."""
    # Инициализация данных
    logger.info("Инициализация бота...")
    init_data()
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)