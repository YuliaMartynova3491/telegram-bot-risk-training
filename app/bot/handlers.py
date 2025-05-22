"""
Модуль для обработчиков Telegram бота.
Финальная исправленная версия.
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
    get_lesson_by_id,
    get_next_lesson,
    get_available_lessons,
    get_user_progress,
    get_or_create_user_progress,
    update_user_progress,
    calculate_lesson_success_percentage,
    get_questions_by_lesson,
    get_question_by_id
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
        from app.learning.courses import init_courses
        courses = init_courses()
        
        # Инициализируем уроки для каждой темы
        from app.learning.lessons import init_lessons
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
    try:
        await send_welcome_sticker(context, chat_id)
    except Exception as e:
        logger.warning(f"Не удалось отправить стикер: {e}")
    
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
    
    # Проверяем, ожидаем ли вопрос от пользователя
    if context.user_data.get('waiting_for_question', False):
        # Базовая обработка вопроса пользователя
        try:
            # Получаем урок из контекста
            lesson_id = context.user_data.get('question_lesson_id')
            if lesson_id:
                lesson = get_lesson(db, lesson_id)
                lesson_title = lesson.title if lesson else "урок"
            else:
                lesson_title = "урок"
            
            # Простой ответ на вопрос
            answer_message = (
                f"🤔 Спасибо за ваш вопрос по теме '{lesson_title}'!\n\n"
                f"**Ваш вопрос:** {update.message.text}\n\n"
                "К сожалению, функция ответов на вопросы временно недоступна. "
                "Рекомендую обратиться к материалам урока для получения дополнительной информации.\n\n"
                "Если у вас есть конкретные вопросы по материалу, попробуйте:\n"
                "• Перечитать содержание урока\n"
                "• Обратить внимание на объяснения к вопросам теста\n"
                "• Пройти тест еще раз для закрепления материала"
            )
            
            await update.message.reply_text(
                answer_message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📖 Вернуться к уроку", callback_data=f"lesson_{lesson_id}")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            
            # Сбрасываем флаг ожидания вопроса
            context.user_data['waiting_for_question'] = False
            context.user_data.pop('question_lesson_id', None)
            return
            
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {e}")
            await update.message.reply_text(
                "Произошла ошибка при обработке вопроса. Попробуйте позже."
            )
            context.user_data['waiting_for_question'] = False
            return
    
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
        from app.bot.handlers_menu import show_progress
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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на inline кнопки."""
    query = update.callback_query
    user = query.from_user
    
    # ОТЛАДКА: Логируем все callback данные
    logger.info(f"Получен callback: {query.data} от пользователя {user.id}")
    
    try:
        # Отвечаем на callback query
        await query.answer()
        
        # Парсим callback data
        if query.data == "main_menu" or query.data == "back_to_main":
            await show_main_menu(update, context)
        elif query.data == "courses":
            await show_courses(update, context)
        elif query.data.startswith("course_"):
            course_id = int(query.data.replace("course_", ""))
            await show_course_lessons(update, context, course_id)
        elif query.data.startswith("lesson_"):
            lesson_id = int(query.data.replace("lesson_", ""))
            logger.info(f"Попытка открыть урок {lesson_id}")
            await show_lesson_content(update, context, lesson_id)
                
        elif query.data.startswith("start_test_"):
            lesson_id = int(query.data.replace("start_test_", ""))
            logger.info(f"Попытка запустить тест для урока {lesson_id}")
            await start_lesson_test(update, context, lesson_id)
                
        elif query.data.startswith("ask_question_"):
            lesson_id = int(query.data.replace("ask_question_", ""))
            logger.info(f"Попытка задать вопрос по уроку {lesson_id}")
            await handle_user_question(update, context, lesson_id)
                
        elif query.data.startswith("answer_"):
            # Парсим данные ответа: answer_questionId_letter
            parts = query.data.split("_")
            if len(parts) >= 3:
                question_id = int(parts[1])
                answer_letter = parts[2]
                logger.info(f"Ответ на вопрос {question_id}: {answer_letter}")
                await handle_answer_selection(update, context, question_id, answer_letter)
            else:
                logger.error(f"Неверный формат данных ответа: {query.data}")
                
        elif query.data == "next_question":
            logger.info("Переход к следующему вопросу")
            await handle_next_question(update, context)
            
        elif query.data.startswith("next_question_"):
            lesson_id = int(query.data.replace("next_question_", ""))
            await handle_next_question_in_lesson(update, context, lesson_id)
            
        elif query.data.startswith("retry_question_"):
            question_id = int(query.data.replace("retry_question_", ""))
            await retry_question(update, context, question_id)
            
        else:
            logger.warning(f"Неизвестный callback: {query.data}")
            await query.message.edit_text("❌ Неизвестная команда")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        except:
            logger.error("Не удалось отправить сообщение об ошибке")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает главное меню."""
    query = update.callback_query
    user = query.from_user
    
    welcome_message = (
        f"🏠 **Главное меню**\n\n"
        f"Привет, {user.first_name}!\n"
        "Выберите действие:"
    )
    
    await query.message.edit_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список курсов."""
    query = update.callback_query
    
    db = get_db()
    courses = get_all_courses(db)
    
    await query.message.edit_text(
        "📚 **Выберите тему для изучения:**",
        parse_mode="Markdown",
        reply_markup=get_courses_keyboard(courses)
    )

async def show_course_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE, course_id: int) -> None:
    """Показывает список уроков курса."""
    query = update.callback_query
    user = query.from_user
    
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    course = get_course(db, course_id)
    lessons = get_lessons_by_course(db, course_id)
    
    if not lessons:
        await query.message.edit_text(
            "❌ Уроки для этой темы пока не созданы.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К темам", callback_data="courses")]
            ])
        )
        return
    
    # Создаем клавиатуру с уроками
    keyboard = []
    for lesson in lessons:
        # Проверяем прогресс по уроку
        progress = get_user_progress(db, db_user.id, lesson.id)
        
        if progress and progress.is_completed:
            status = "✅"
        else:
            status = "📝"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {lesson.title}",
                callback_data=f"lesson_{lesson.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 К темам", callback_data="courses")])
    
    message_text = f"📖 **{course.name}**\n\n{course.description}\n\n**Уроки:**"
    
    await query.message.edit_text(
        message_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_lesson_content(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Показывает содержимое урока с кнопками действий."""
    query = update.callback_query
    user = query.from_user
    
    # Получаем пользователя и урок из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    lesson = get_lesson(db, lesson_id)
    
    if not lesson:
        await query.message.edit_text(
            "❌ Урок не найден.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    # Удаляем предыдущее сообщение и отправляем новое с содержимым урока
    try:
        await query.message.delete()
    except:
        pass
    
    # Разбиваем содержимое на части, если оно слишком длинное
    content = lesson.content
    max_length = 4000
    
    if len(content) <= max_length:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📝 **{lesson.title}**\n\n{content}",
            parse_mode="Markdown"
        )
    else:
        # Отправляем заголовок
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📝 **{lesson.title}**",
            parse_mode="Markdown"
        )
        
        # Отправляем содержимое частями
        chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
        for chunk in chunks:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=chunk,
                parse_mode="Markdown"
            )
    
    # Отправляем предложение пройти тест
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Теперь давайте проверим ваши знания. Готовы ответить на несколько вопросов?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Начать тест", callback_data=f"start_test_{lesson_id}")],
            [InlineKeyboardButton("❓ Задать вопрос по уроку", callback_data=f"ask_question_{lesson_id}")],
            [InlineKeyboardButton("📋 К урокам", callback_data=f"course_{lesson.course_id}")]
        ])
    )

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Обрабатывает запрос пользователя задать вопрос по уроку."""
    query = update.callback_query
    
    # Устанавливаем флаг ожидания вопроса
    context.user_data['waiting_for_question'] = True
    context.user_data['question_lesson_id'] = lesson_id
    
    await query.message.edit_text(
        "❓ **Задать вопрос по уроку**\n\n"
        "Напишите ваш вопрос по материалу урока, и я постараюсь на него ответить.\n\n"
        "Например:\n"
        "• Что означает термин 'угроза непрерывности'?\n"
        "• Как оценивается критичность процессов?\n"
        "• Какие факторы влияют на риск нарушения непрерывности?\n\n"
        "Напишите ваш вопрос:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data=f"lesson_{lesson_id}")]
        ])
    )

async def start_lesson_test(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Запускает тест по уроку."""
    query = update.callback_query
    user = query.from_user
    
    # Получаем пользователя и урок из базы данных
    db = get_db()
    db_user = get_or_create_user(
        db,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    lesson = get_lesson(db, lesson_id)
    if not lesson:
        await query.message.edit_text("❌ Урок не найден.")
        return
    
    # Получаем или создаем вопросы для урока
    questions = get_questions_by_lesson(db, lesson_id)
    
    if not questions:
        # Создаем вопросы, если их нет
        try:
            from app.learning.questions import generate_questions_for_lesson
            course = get_course(db, lesson.course_id)
            topic = course.name.lower().replace(" ", "_") if course else "risk_management"
            questions = generate_questions_for_lesson(lesson_id, topic)
        except Exception as e:
            logger.error(f"Ошибка при генерации вопросов: {e}")
            questions = []
    
    if not questions:
        await query.message.edit_text(
            f"❌ К сожалению, для урока '{lesson.title}' пока нет вопросов.\n"
            "Попробуйте другой урок или вернитесь позже.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К уроку", callback_data=f"lesson_{lesson_id}")]
            ])
        )
        return
    
    # Инициализируем тест в контексте пользователя
    context.user_data['current_test'] = {
        'lesson_id': lesson_id,
        'questions': [q.id for q in questions],
        'current_question_index': 0,
        'correct_answers': 0,
        'total_questions': len(questions)
    }
    
    # Показываем первый вопрос
    await send_question(update, context, questions[0].id)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int) -> None:
    """Отправляет вопрос пользователю."""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    db = get_db()
    question = get_question_by_id(db, question_id)
    
    if not question:
        await query.message.edit_text("❌ Вопрос не найден.")
        return
    
    # Получаем данные теста
    test_data = context.user_data.get('current_test', {})
    current_index = test_data.get('current_question_index', 0)
    total_questions = test_data.get('total_questions', 1)
    
    # Парсим варианты ответов
    if isinstance(question.options, str):
        try:
            options = json.loads(question.options)
        except:
            options = [opt.strip() for opt in question.options.split('\n') if opt.strip()]
    else:
        options = question.options
    
    # Формируем текст вопроса
    question_number = current_index + 1
    progress_text = f"📊 Вопрос {question_number} из {total_questions}\n\n"
    
    # Добавляем индикатор сложности
    difficulty_map = {
        "легкий": "⭐",
        "средний": "⭐⭐", 
        "сложный": "⭐⭐⭐"
    }
    difficulty = getattr(question, 'difficulty', 'средний')
    difficulty_indicator = difficulty_map.get(difficulty, "⭐⭐")
    difficulty_text = f"{difficulty_indicator} **Сложность:** {difficulty}\n\n"
    
    # Форматируем вопрос с вариантами ответов
    question_text = f"❓ **{question.text}**\n\n"
    
    letters = ['A', 'B', 'C', 'D', 'E', 'F']
    for i, option in enumerate(options):
        if i < len(letters):
            question_text += f"**{letters[i]}.** {option}\n\n"
    
    full_text = f"{progress_text}{difficulty_text}{question_text.rstrip()}"
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = []
    for i in range(min(len(options), len(letters))):
        button = InlineKeyboardButton(
            text=f"🔘 {letters[i]}",
            callback_data=f"answer_{question_id}_{letters[i]}"
        )
        keyboard.append([button])
    
    await query.message.edit_text(
        full_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_answer_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int, answer_letter: str) -> None:
    """Обрабатывает выбор варианта ответа пользователем."""
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
    try:
        from app.learning.questions import check_answer, get_explanation
        is_correct = check_answer(question_id, db_user.id, answer_letter)
        explanation = get_explanation(question_id)
    except ImportError:
        # Резервная логика проверки ответа
        question = get_question_by_id(db, question_id)
        is_correct = question.correct_answer == answer_letter if question else False
        explanation = question.explanation if question else "Объяснение недоступно."
    
    # Получаем вопрос для отображения правильного ответа
    question = get_question_by_id(db, question_id)
    
    if isinstance(question.options, str):
        try:
            options = json.loads(question.options)
        except:
            options = [opt.strip() for opt in question.options.split('\n') if opt.strip()]
    else:
        options = question.options
    
    # Обновляем счетчик правильных ответов
    test_data = context.user_data.get('current_test', {})
    if is_correct:
        test_data['correct_answers'] = test_data.get('correct_answers', 0) + 1
    
    # Определяем правильный вариант ответа текстом
    correct_index = ord(question.correct_answer) - ord('A')
    correct_option_text = options[correct_index] if 0 <= correct_index < len(options) else ""
    
    # Отправляем стикер
    try:
        if is_correct:
            await send_correct_answer_sticker(context, chat_id, is_first=test_data.get('correct_answers', 0) == 1)
        else:
            await send_wrong_answer_sticker(context, chat_id, is_first=True)
    except Exception as e:
        logger.warning(f"Не удалось отправить стикер: {e}")
    
    # Формируем сообщение с результатом
    if is_correct:
        result_message = (
            "✅ **Правильно!**\n\n"
            f"**Ответ {question.correct_answer}:** {correct_option_text}\n\n"
            f"**Объяснение:** {explanation}"
        )
    else:
        result_message = (
            "❌ **Неправильно**\n\n"
            f"**Правильный ответ: {question.correct_answer}.** {correct_option_text}\n\n"
            f"**Объяснение:** {explanation}"
        )
    
    # Отправляем результат
    await query.message.edit_text(
        result_message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Продолжить", callback_data="next_question")]
        ])
    )

async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переходит к следующему вопросу или показывает результаты."""
    test_data = context.user_data.get('current_test', {})
    
    if not test_data:
        await update.callback_query.message.edit_text("❌ Данные теста не найдены.")
        return
    
    # Увеличиваем индекс текущего вопроса
    current_index = test_data.get('current_question_index', 0)
    questions = test_data.get('questions', [])
    
    next_index = current_index + 1
    
    if next_index < len(questions):
        # Есть еще вопросы - отправляем следующий
        test_data['current_question_index'] = next_index
        context.user_data['current_test'] = test_data
        
        next_question_id = questions[next_index]
        await send_question(update, context, next_question_id)
    else:
        # Вопросы закончились - показываем результаты
        await show_test_results(update, context)

async def handle_next_question_in_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Обрабатывает переход к следующему вопросу в уроке."""
    # Эта функция используется для совместимости со старым кодом
    await handle_next_question(update, context)

async def retry_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int) -> None:
    """Позволяет пользователю повторить вопрос."""
    await send_question(update, context, question_id)

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
    test_data = context.user_data.get('current_test', {})
    lesson_id = test_data.get('lesson_id')
    correct_answers = test_data.get('correct_answers', 0)
    total_questions = test_data.get('total_questions', 0)
    
    if total_questions == 0:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при подсчете результатов.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    # Вычисляем процент успешности
    success_percentage = (correct_answers / total_questions) * 100.0
    
    # Обновляем прогресс пользователя
    is_successful = success_percentage >= MIN_SUCCESS_PERCENTAGE
    update_user_progress(db, db_user.id, lesson_id, is_successful, success_percentage)
    
    # Получаем урок и следующий урок
    lesson = get_lesson(db, lesson_id)
    next_lesson = get_next_lesson(db, lesson_id)
    
    # Отправляем стикер в зависимости от результата
    try:
        if is_successful:
            await send_lesson_success_sticker(context, chat_id)
            # Если это последний урок в теме, отправляем стикер завершения темы
            if not next_lesson or (hasattr(next_lesson, 'course_id') and next_lesson.course_id != lesson.course_id):
                await send_topic_success_sticker(context, chat_id)
        else:
            await send_lesson_fail_sticker(context, chat_id)
    except Exception as e:
        logger.warning(f"Не удалось отправить стикер: {e}")
    
    # Формируем сообщение с результатами
    progress_bar = get_progress_bar(success_percentage)
    
    if is_successful:
        result_message = (
            f"🎉 **Поздравляем!** Вы успешно прошли урок \"{lesson.title}\".\n\n"
            f"**Ваш результат:** {correct_answers} из {total_questions} "
            f"({success_percentage:.1f}%)\n\n"
            f"**Прогресс:** {progress_bar}\n\n"
            "Вы можете перейти к следующему уроку или вернуться к списку уроков."
        )
    else:
        result_message = (
            f"📊 **Результаты теста по уроку** \"{lesson.title}\":\n\n"
            f"Вы ответили правильно на {correct_answers} из {total_questions} "
            f"вопросов ({success_percentage:.1f}%)\n\n"
            f"**Прогресс:** {progress_bar}\n\n"
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
    context.user_data.pop('current_test', None)

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
    from telegram import Update
    application.run_polling(allowed_updates=Update.ALL_TYPES)