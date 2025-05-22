"""
Обработчики для работы с уроками и вопросами пользователей.
Полная исправленная версия с улучшенной обработкой ошибок.
"""
import logging
import json
import asyncio
import requests
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.config import LLM_MODEL_PATH, MIN_SUCCESS_PERCENTAGE
from app.database.models import get_db
from app.database.operations import (
    get_or_create_user,
    update_user_activity,
    get_lesson_by_id,
    get_lesson,
    get_course,
    get_next_lesson,
    get_or_create_user_progress,
    update_user_progress,
    get_question,
    get_questions_by_lesson
)
from app.bot.keyboards import (
    get_question_options_keyboard,
    get_continue_keyboard,
    get_lessons_keyboard,
    get_progress_bar,
    get_wrong_answer_keyboard
)
from app.bot.stickers import (
    send_correct_answer_sticker,
    send_wrong_answer_sticker,
    send_lesson_success_sticker,
    send_topic_success_sticker,
    send_lesson_fail_sticker
)
from app.learning.questions import (
    generate_questions_for_lesson,
    check_answer,
    get_explanation
)

# Импортируем агенты с обработкой ошибок
try:
    from app.langchain.integration import agent_integration
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    logger.warning("Агенты недоступны, используется стандартная логика")

logger = logging.getLogger(__name__)

def get_lesson_context(lesson_content: str, lesson_title: str) -> str:
    """Формирует контекст урока для ИИ."""
    return f"""
Тема урока: {lesson_title}

Содержание урока:
{lesson_content}

Инструкция: Ты - эксперт по рискам нарушения непрерывности деятельности. 
Отвечай на вопросы пользователя, основываясь на содержании урока выше.
Если информации в уроке недостаточно для полного ответа, дополни ответ своими знаниями по теме рисков непрерывности деятельности.
Отвечай простым и понятным языком, структурируй ответ.
"""

async def ask_llm_question(question: str, lesson_context: str) -> str:
    """Отправляет вопрос в LM Studio и получает ответ."""
    try:
        headers = {"Content-Type": "application/json"}
        
        # Улучшенный промпт для более точных ответов
        system_prompt = """Ты - эксперт по рискам нарушения непрерывности деятельности. 
Отвечай на основе предоставленного содержания урока.
Если информации недостаточно, используй свои знания по теме рисков непрерывности деятельности.
Отвечай четко, структурированно и понятным языком."""
        
        user_prompt = f"""Контекст урока:
{lesson_context}

Вопрос студента: {question}

Дай подробный и понятный ответ на основе содержания урока. Если в уроке нет прямого ответа, дай общее объяснение по теме рисков нарушения непрерывности деятельности."""
        
        data = {
            "model": "qwen2.5-14b-instruct",
            "messages": [
                {
                    "role": "system", 
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1500,
            "stop": ["Вопрос студента:", "###", "---"]
        }
        
        logger.info(f"Отправка запроса в LM Studio для вопроса: {question[:50]}...")
        
        response = requests.post(
            f"{LLM_MODEL_PATH}/chat/completions",
            headers=headers,
            json=data,
            timeout=45
        )
        
        logger.info(f"Статус ответа LM Studio: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content.strip():
                logger.info(f"Получен ответ от LM Studio: {content[:100]}...")
                return content.strip()
            else:
                logger.warning("LM Studio вернул пустой ответ")
                return "Извините, не удалось сформировать ответ. Попробуйте переформулировать вопрос."
        else:
            logger.error(f"Ошибка LM Studio: {response.status_code} - {response.text}")
            return f"Извините, произошла техническая ошибка при обработке вашего вопроса (код: {response.status_code})."
    
    except requests.exceptions.Timeout:
        logger.error("Таймаут при обращении к LM Studio")
        return "Извините, обработка вопроса заняла слишком много времени. Попробуйте задать более простой вопрос."
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения с LM Studio")
        return "Извините, не удалось подключиться к системе обработки вопросов. Попробуйте позже."
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обращении к LM Studio: {e}")
        return "Извините, произошла неожиданная ошибка при обработке вашего вопроса. Попробуйте позже."

def format_question_with_options(question_text: str, options: list) -> str:
    """
    Форматирует вопрос с вариантами ответов для красивого отображения.
    
    Args:
        question_text: Текст вопроса
        options: Список вариантов ответов
    
    Returns:
        Отформатированная строка с вопросом и вариантами
    """
    formatted = f"❓ **{question_text}**\n\n"
    
    letters = ['A', 'B', 'C', 'D', 'E', 'F']  # На случай, если будет больше 4 вариантов
    
    for i, option in enumerate(options):
        if i < len(letters):
            formatted += f"**{letters[i]}.** {option}\n\n"
    
    return formatted.rstrip()  # Убираем последние лишние переносы

def create_answer_keyboard(question_id: int, num_options: int):
    """
    Создает клавиатуру с вариантами ответов.
    
    Args:
        question_id: ID вопроса
        num_options: Количество вариантов ответов
    
    Returns:
        InlineKeyboardMarkup с кнопками вариантов ответов
    """
    letters = ['A', 'B', 'C', 'D', 'E', 'F']
    buttons = []
    
    # Создаем кнопки для каждого варианта
    for i in range(min(num_options, len(letters))):
        button = InlineKeyboardButton(
            text=f"🔘 {letters[i]}",
            callback_data=f"answer_{question_id}_{letters[i]}"
        )
        buttons.append([button])
    
    return InlineKeyboardMarkup(buttons)

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
    try:
        await query.message.delete()
    except:
        pass  # Игнорируем ошибки удаления
    
    # Отправляем содержимое урока
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
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Начать тест", callback_data=f"start_test_{lesson_id}")],
            [InlineKeyboardButton("❓ Задать вопрос по уроку", callback_data=f"ask_question_{lesson_id}")]
        ])
    )

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Обрабатывает начало диалога для вопроса по уроку."""
    query = update.callback_query
    user = update.effective_user
    
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
    
    # Получаем урок
    lesson = get_lesson_by_id(db, lesson_id)
    if not lesson:
        await query.message.edit_text(
            "❌ Урок не найден.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        return
    
    # Сохраняем информацию об уроке в context для последующего использования
    context.user_data['current_lesson_id'] = lesson_id
    context.user_data['lesson_context'] = get_lesson_context(lesson.content, lesson.title)
    context.user_data['waiting_for_question'] = True
    
    await query.message.edit_text(
        f"❓ **Задайте вопрос по уроку:** *{lesson.title}*\n\n"
        "💡 Вы можете спросить о любом аспекте урока. Например:\n"
        "• Что такое риск нарушения непрерывности?\n"
        "• Какие типы угроз существуют?\n"
        "• Как оценивается критичность процессов?\n\n"
        "✍️ Напишите ваш вопрос:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Вернуться к уроку", callback_data=f"lesson_{lesson_id}")]
        ])
    )

async def process_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает вопрос пользователя и генерирует ответ."""
    user_question = update.message.text
    user = update.effective_user
    
    # Проверяем, ожидаем ли мы вопрос
    if not context.user_data.get('waiting_for_question', False):
        return
    
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
    
    # Получаем контекст урока
    lesson_context = context.user_data.get('lesson_context', '')
    lesson_id = context.user_data.get('current_lesson_id', 0)
    
    if not lesson_context:
        await update.message.reply_text(
            "❌ Не удалось найти контекст урока. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        return
    
    # Отправляем индикатор "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Пытаемся использовать агентов для ответа
    try:
        if AGENTS_AVAILABLE:
            # Используем агента для ответа на вопрос
            ai_response = await agent_integration.answer_user_query(user_question, lesson_context)
        else:
            raise Exception("Агенты недоступны")
    except Exception as e:
        logger.warning(f"Агенты недоступны ({e}), используем прямой запрос к LM Studio")
        # Если агент недоступен, используем прямой запрос к LM Studio
        ai_response = await ask_llm_question(user_question, lesson_context)
    
    # Отправляем ответ пользователю
    response_text = f"❓ **Ваш вопрос:** {user_question}\n\n"
    response_text += f"🤖 **Ответ:**\n{ai_response}\n\n"
    response_text += "💡 Есть еще вопросы по этому уроку?"
    
    # Создаем клавиатуру для дальнейших действий
    keyboard = [
        [InlineKeyboardButton("❓ Задать еще вопрос", callback_data=f"ask_question_{lesson_id}")],
        [InlineKeyboardButton("📝 Начать тест", callback_data=f"start_test_{lesson_id}")],
        [InlineKeyboardButton("🔙 К уроку", callback_data=f"lesson_{lesson_id}")]
    ]
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Сбрасываем флаг ожидания вопроса
    context.user_data['waiting_for_question'] = False

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
    if not lesson:
        await query.message.edit_text("❌ Урок не найден.")
        return
    
    # Получаем курс для определения темы
    course = get_course(db, lesson.course_id)
    
    # Создаем или получаем прогресс пользователя по уроку
    progress = get_or_create_user_progress(db, db_user.id, lesson_id)
    
    # Пытаемся использовать агентов для обучения
    try:
        if AGENTS_AVAILABLE:
            learning_session = await agent_integration.start_learning_session(db_user.id, lesson_id)
            adaptive_learning = not learning_session.get("use_standard_flow", True)
        else:
            raise Exception("Агенты недоступны")
    except Exception as e:
        logger.warning(f"Агенты недоступны ({e}), используется стандартная логика")
        # Если агенты недоступны, используем стандартную логику
        learning_session = {"use_standard_flow": True}
        adaptive_learning = False
    
    # Генерируем вопросы для урока
    topic = course.name.lower().replace(" ", "_") if course else "risk_management"
    
    try:
        questions = generate_questions_for_lesson(lesson_id, topic)
    except Exception as e:
        logger.error(f"Ошибка при генерации вопросов: {e}")
        # Попробуем получить существующие вопросы из базы данных
        questions = get_questions_by_lesson(db, lesson_id)
    
    if not questions:
        await query.message.edit_text(
            "⚠️ К сожалению, для этого урока пока нет доступных вопросов.\n"
            "Попробуйте другой урок или обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К уроку", callback_data=f"lesson_{lesson_id}")]
            ])
        )
        return
    
    # Инициализируем контекст теста
    context.user_data['current_question'] = 0
    context.user_data['questions'] = [q.id for q in questions]
    context.user_data['lesson_id'] = lesson_id
    context.user_data['correct_answers'] = 0
    context.user_data['wrong_answers_streak'] = 0
    context.user_data['user_level'] = 50  # Начальный уровень пользователя
    context.user_data['misconceptions'] = []  # Список заблуждений пользователя
    context.user_data['adaptive_learning'] = adaptive_learning
    
    # Отправляем первый вопрос
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет вопрос пользователю с улучшенным форматированием."""
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
    
    # Парсим опции
    if isinstance(question.options, str):
        try:
            options = json.loads(question.options)
        except:
            options = [opt.strip() for opt in question.options.split('\n') if opt.strip()]
    else:
        options = question.options
    
    # Формируем сообщение с вопросом
    question_number = current_question_index + 1
    total_questions = len(questions)
    
    # Адаптируем сложность вопроса на основе уровня пользователя
    user_level = context.user_data.get('user_level', 50)
    adaptive_learning = context.user_data.get('adaptive_learning', False)
    
    # Добавляем информацию о прогрессе
    progress_text = f"📊 Вопрос {question_number} из {total_questions}\n\n"
    
    # Добавляем индикатор сложности
    difficulty_map = {
        "легкий": "⭐",
        "средний": "⭐⭐", 
        "сложный": "⭐⭐⭐"
    }
    difficulty = getattr(question, 'difficulty', 'средний')
    difficulty_indicator = difficulty_map.get(difficulty, "⭐⭐")
    
    # Если включено адаптивное обучение, добавляем информацию о пользовательском уровне
    if adaptive_learning:
        if user_level < 30:
            difficulty_text = f"{difficulty_indicator} **Сложность: базовая**"
        elif user_level < 70:
            difficulty_text = f"{difficulty_indicator} **Сложность: средняя**"
        else:
            difficulty_text = f"{difficulty_indicator} **Сложность: продвинутая**"
    else:
        difficulty_text = f"{difficulty_indicator} **Сложность:** {difficulty}"
    
    # Форматируем вопрос с вариантами ответов
    question_text = format_question_with_options(question.text, options)
    
    full_text = f"{progress_text}{difficulty_text}\n\n{question_text}"
    
    # Создаем клавиатуру
    keyboard = create_answer_keyboard(question.id, len(options))
    
    await query.message.edit_text(
        full_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def process_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int, answer: str) -> None:
    """Обрабатывает ответ пользователя на вопрос с поддержкой агентов."""
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
    
    # Получаем вопрос
    question = get_question(db, question_id)
    if not question:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при обработке ответа. Пожалуйста, попробуйте позже."
        )
        return
    
    # Проверяем ответ
    is_correct = check_answer(question_id, db_user.id, answer)
    
    # Адаптивное обучение
    adaptive_learning = context.user_data.get('adaptive_learning', False)
    user_level = context.user_data.get('user_level', 50)
    misconceptions = context.user_data.get('misconceptions', [])
    
    # Если адаптивное обучение включено, используем агентов для оценки
    if adaptive_learning and AGENTS_AVAILABLE:
        try:
            # Оцениваем ответ пользователя с помощью агента
            assessment = await agent_integration.assess_answer(question.text, answer, question.correct_answer)
            
            # Обновляем уровень пользователя
            if 'score' in assessment:
                # Новый уровень = 70% старый + 30% новая оценка
                new_level = int(0.7 * user_level + 0.3 * assessment.get('score', 0))
                context.user_data['user_level'] = max(0, min(100, new_level))
        except Exception as e:
            logger.warning(f"Агенты недоступны для оценки ответа: {e}")
        
        # Если ответ неправильный, добавляем в список заблуждений
        if not is_correct:
            misconceptions.append(question.text)
            context.user_data['misconceptions'] = misconceptions
    
    # Обновляем счетчик правильных ответов
    if is_correct:
        context.user_data['correct_answers'] = context.user_data.get('correct_answers', 0) + 1
        context.user_data['wrong_answers_streak'] = 0
    else:
        context.user_data['wrong_answers_streak'] = context.user_data.get('wrong_answers_streak', 0) + 1
    
    # Получаем объяснение
    explanation = get_explanation(question_id)
    
    # Если адаптивное обучение включено и ответ неправильный, генерируем дополнительное объяснение
    additional_explanation = ""
    if adaptive_learning and not is_correct and AGENTS_AVAILABLE:
        try:
            # Получаем урок
            lesson_id = context.user_data.get('lesson_id')
            lesson = get_lesson(db, lesson_id)
            course = get_course(db, lesson.course_id)
            
            # Генерируем дополнительное объяснение
            topic = course.name.lower().replace(" ", "_")
            concept = question.text
            
            additional_explanation = await agent_integration.generate_adaptive_explanation(
                topic, 
                concept, 
                context.user_data.get('user_level', 50), 
                misconceptions
            )
        except Exception as e:
            logger.warning(f"Не удалось сгенерировать дополнительное объяснение: {e}")
    
    # Определяем правильный вариант ответа текстом
    options = json.loads(question.options) if isinstance(question.options, str) else question.options
    correct_index = ord(question.correct_answer) - ord('A')
    correct_option_text = options[correct_index] if 0 <= correct_index < len(options) else ""
    
    # Формируем сообщение с результатом
    if is_correct:
        # Отправляем стикер
        if context.user_data.get('correct_answers', 0) == 1:
            await send_correct_answer_sticker(context, chat_id, is_first=True)
        else:
            await send_correct_answer_sticker(context, chat_id, is_first=False)
        
        result_message = (
            "✅ **Правильно!**\n\n"
            f"**Ответ {question.correct_answer}:** {correct_option_text}\n\n"
            f"**Объяснение:** {explanation}\n\n"
        )
    else:
        # Отправляем стикер
        if context.user_data.get('wrong_answers_streak', 0) == 1:
            await send_wrong_answer_sticker(context, chat_id, is_first=True)
        else:
            await send_wrong_answer_sticker(context, chat_id, is_first=False)
        
        result_message = (
            "❌ **Неправильно**\n\n"
            f"**Правильный ответ: {question.correct_answer}.** {correct_option_text}\n\n"
            f"**Объяснение:** {explanation}\n\n"
        )
        
        # Если есть дополнительное объяснение, добавляем его
        if additional_explanation:
            result_message += f"**Дополнительное объяснение:**\n{additional_explanation}\n\n"
    
    # Добавляем кнопку "Продолжить"
    keyboard = [
        [InlineKeyboardButton("▶️ Продолжить", callback_data="next_question")]
    ]
    
    # Отправляем сообщение с результатом
    await query.message.edit_text(
        result_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки Продолжить."""
    # Переходим к следующему вопросу
    context.user_data['current_question'] = context.user_data.get('current_question', 0) + 1
    
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
    adaptive_learning = context.user_data.get('adaptive_learning', False)
    user_level = context.user_data.get('user_level', 50)
    
    if total_questions == 0:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при подсчете результатов. Пожалуйста, попробуйте позже."
        )
        return
    
    # Вычисляем процент успешности
    success_percentage = (correct_answers / total_questions) * 100.0
    
    # Обновляем прогресс пользователя
    update_user_progress(db, db_user.id, lesson_id, success_percentage >= MIN_SUCCESS_PERCENTAGE, success_percentage)
    
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
            f"🎉 **Поздравляем!** Вы успешно прошли урок \"{lesson.title}\".\n\n"
            f"**Ваш результат:** {correct_answers} из {total_questions} ({success_percentage:.1f}%)\n\n"
        )
        
        # Если адаптивное обучение включено, добавляем информацию о нем
        if adaptive_learning:
            result_message += (
                f"**Ваш текущий уровень знаний:** {user_level}/100\n\n"
            )
        
        result_message += (
            f"**Прогресс:** {get_progress_bar(success_percentage)}\n\n"
            "Вы можете перейти к следующему уроку или вернуться к списку уроков."
        )
        
        # Если это последний урок в теме, отправляем стикер успешного завершения темы
        if not next_lesson or next_lesson.course_id != lesson.course_id:
            await send_topic_success_sticker(context, chat_id)
    else:
        # Отправляем стикер неуспешного завершения урока
        await send_lesson_fail_sticker(context, chat_id)
        
        result_message = (
            f"📊 **Результаты теста по уроку** \"{lesson.title}\":\n\n"
            f"Вы ответили правильно на {correct_answers} из {total_questions} вопросов ({success_percentage:.1f}%)\n\n"
        )
        
        # Если адаптивное обучение включено, добавляем информацию о нем
        if adaptive_learning:
            result_message += (
                f"**Ваш текущий уровень знаний:** {user_level}/100\n\n"
            )
        
        result_message += (
            f"**Прогресс:** {get_progress_bar(success_percentage)}\n\n"
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
    context.user_data.pop('adaptive_learning', None)
    context.user_data.pop('user_level', None)
    context.user_data.pop('misconceptions', None)
    context.user_data.pop('current_lesson_id', None)
    context.user_data.pop('lesson_context', None)
    context.user_data.pop('waiting_for_question', None)