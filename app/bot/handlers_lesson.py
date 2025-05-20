"""
Модуль для обработки уроков и вопросов.
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.config import MIN_SUCCESS_PERCENTAGE
from app.database.models import get_db
from app.database.operations import (
    get_or_create_user,
    update_user_activity,
    get_lesson,
    get_course,
    get_next_lesson,
    get_or_create_user_progress,
    get_question
)
from app.bot.keyboards import (
    get_question_options_keyboard,
    get_continue_keyboard,
    get_lessons_keyboard
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

logger = logging.getLogger(__name__)

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
    
    # ИСПРАВЛЕНИЕ: Форматируем вопрос с переносами строк для лучшей читаемости
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
    
    # Получаем вопрос
    question = get_question(db, question_id)
    if not question:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при обработке ответа. Пожалуйста, попробуйте позже."
        )
        return
    
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
    
    # ИСПРАВЛЕНИЕ: Форматируем объяснение с переносами строк для лучшей читаемости
    # Ограничиваем длину объяснения и разбиваем его на части, если оно слишком длинное
    max_explanation_length = 200
    if len(explanation) > max_explanation_length:
        short_explanation = explanation[:max_explanation_length] + "..." 
    else:
        short_explanation = explanation
    
    # Определяем правильный вариант ответа текстом
    options = json.loads(question.options)
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
            "✅ *Правильно!*\n\n"
            f"Ответ {question.correct_answer}: {correct_option_text}\n\n"
            f"Объяснение: {short_explanation}\n\n"
        )
    else:
        # Отправляем стикер
        if context.user_data.get('wrong_answers_streak', 0) == 1:
            await send_wrong_answer_sticker(context, chat_id, is_first=True)
        else:
            await send_wrong_answer_sticker(context, chat_id, is_first=False)
        
        result_message = (
            "❌ *Неправильно*\n\n"
            f"Правильный ответ: {question.correct_answer}. {correct_option_text}\n\n"
            f"Объяснение: {short_explanation}\n\n"
        )
    
    # ИСПРАВЛЕНИЕ: Добавляем кнопку "Попробовать еще раз" для неправильных ответов
    keyboard = []
    if not is_correct:
        # Добавляем кнопку попробовать еще раз
        keyboard.append([
            InlineKeyboardButton("🔄 Попробовать еще раз", callback_data=f"retry_question_{question_id}")
        ])
    
    # Добавляем кнопку продолжить
    keyboard.append([
        InlineKeyboardButton("▶️ Продолжить", callback_data=f"next_question")
    ])
    
    # Отправляем сообщение с результатом
    await query.message.edit_text(
        result_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    # ИСПРАВЛЕНИЕ: Обрабатываем нажатие кнопки "Продолжить" отдельно
    # чтобы не переходить автоматически к следующему вопросу
    # Это исправит проблему зависания после трех неверных ответов
    if callback_data == "next_question":
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
    
    if total_questions == 0:
        await query.message.edit_text(
            "⚠️ Произошла ошибка при подсчете результатов. Пожалуйста, попробуйте позже."
        )
        return
    
    # Вычисляем процент успешности
    success_percentage = (correct_answers / total_questions) * 100.0
    
    # Обновляем прогресс пользователя
    from app.database.operations import update_user_progress
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

# Добавляем функцию для обработки кнопки "Продолжить"
async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки Продолжить."""
    # Переходим к следующему вопросу
    context.user_data['current_question'] = context.user_data.get('current_question', 0) + 1
    
    # Отправляем следующий вопрос
    await send_question(update, context)