"""
Модуль с дополнительными обработчиками для бота.
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.bot.stickers import (
    send_correct_answer_sticker,
    send_wrong_answer_sticker,
    send_lesson_success_sticker,
    send_lesson_fail_sticker,
    send_topic_success_sticker
)
from app.database.models import get_db
from app.database.operations import (
    get_or_create_user,
    get_question,
    get_lesson,
    get_next_lesson
)
from app.learning.questions import (
    check_answer,
    get_explanation,
    get_questions_by_lesson
)
from app.bot.keyboards import (
    get_progress_bar,
    get_wrong_answer_keyboard,
    get_question_options_keyboard
)

logger = logging.getLogger(__name__)

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
    
    try:
        # Получаем вопрос из базы данных
        question = get_question(db, question_id)
        if not question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            await query.message.reply_text("Произошла ошибка при получении вопроса.")
            return
        
        # Получаем варианты ответов
        options = json.loads(question.options)
        
        # Находим текст выбранного варианта
        option_index = ord(answer_letter) - ord('A')
        if 0 <= option_index < len(options):
            selected_option = options[option_index]
        else:
            selected_option = "Неизвестный вариант"
        
        # Создаем сообщение с текстом выбранного ответа
        message_text = f"Выбран ответ: {answer_letter}. {selected_option}"
        
        # Отправляем сообщение с выбранным ответом в чат
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=message_text
        )
        
        # Сохраняем ID сообщения с ответом для возможного удаления
        context.user_data.setdefault('answer_messages', []).append(sent_message.message_id)
        
        # Теперь проверяем правильность ответа
        await check_answer_and_respond(update, context, question_id, answer_letter)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора ответа: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка при обработке ответа. Пожалуйста, попробуйте еще раз.")

async def check_answer_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int, answer_letter: str) -> None:
    """Проверяет ответ пользователя и отправляет соответствующий ответ."""
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
    
    try:
        # Проверяем ответ
        is_correct = check_answer(question_id, db_user.id, answer_letter)
        
        # Получаем объяснение
        explanation = get_explanation(question_id)
        
        # Получаем текущий вопрос для определения, к какому уроку он относится
        question = get_question(db, question_id)
        
        if not question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            await query.message.reply_text("Произошла ошибка при получении вопроса.")
            return
        
        # Получаем данные урока
        lesson_id = question.lesson_id
        lesson = get_lesson(db, lesson_id)
        
        # Обновляем счетчики в контексте
        context.user_data.setdefault('lesson_data', {})
        context.user_data['lesson_data'].setdefault(lesson_id, {
            'current_question': 0,
            'correct_answers': 0,
            'wrong_answers_streak': 0
        })
        
        # Получаем текущий индекс вопроса
        all_questions = get_questions_by_lesson(db, lesson_id)
        question_ids = [q.id for q in all_questions]
        current_idx = question_ids.index(question_id) if question_id in question_ids else 0
        
        # Обновляем счетчики ответов
        if is_correct:
            context.user_data['lesson_data'][lesson_id]['correct_answers'] = context.user_data['lesson_data'][lesson_id].get('correct_answers', 0) + 1
            context.user_data['lesson_data'][lesson_id]['wrong_answers_streak'] = 0
        else:
            context.user_data['lesson_data'][lesson_id]['wrong_answers_streak'] = context.user_data['lesson_data'][lesson_id].get('wrong_answers_streak', 0) + 1
        
        # Отправляем стикер в зависимости от результата
        if is_correct:
            if context.user_data['lesson_data'][lesson_id].get('correct_answers', 0) == 1:
                await send_correct_answer_sticker(context, chat_id, is_first=True)
            else:
                await send_correct_answer_sticker(context, chat_id, is_first=False)
            
            # Форматируем объяснение для лучшей читаемости
            explanation_formatted = format_explanation(explanation)
            
            # Отправляем сообщение о правильном ответе
            result_message = (
                "✅ *Правильно!*\n\n"
                f"{explanation_formatted}"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=result_message,
                parse_mode="Markdown"
            )
            
            # Переходим к следующему вопросу
            next_idx = current_idx + 1
            if next_idx < len(question_ids):
                # Отправляем новый вопрос
                await send_question(update, context, lesson_id, question_ids[next_idx])
            else:
                # Если вопросы закончились, показываем результаты
                await show_lesson_results(update, context, lesson_id)
                
        else:
            # Для неправильного ответа, отправляем стикер
            if context.user_data['lesson_data'][lesson_id].get('wrong_answers_streak', 0) == 1:
                await send_wrong_answer_sticker(context, chat_id, is_first=True)
            else:
                await send_wrong_answer_sticker(context, chat_id, is_first=False)
            
            # Форматируем объяснение для лучшей читаемости
            explanation_formatted = format_explanation(explanation)
            
            # Находим правильный ответ
            correct_letter = question.correct_answer
            correct_index = ord(correct_letter) - ord('A')
            options = json.loads(question.options)
            correct_option = options[correct_index] if 0 <= correct_index < len(options) else "Неизвестный вариант"
            
            # Отправляем сообщение о неправильном ответе с подсказкой
            result_message = (
                "❌ *Неправильно*\n\n"
                f"Правильный ответ: *{correct_letter}*. {correct_option}\n\n"
                f"{explanation_formatted}"
            )
            
            # Создаем клавиатуру для неправильного ответа
            keyboard = get_wrong_answer_keyboard(question_id, lesson_id)
            
            # Отправляем сообщение с объяснением и кнопками
            await context.bot.send_message(
                chat_id=chat_id,
                text=result_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при проверке ответа: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка при проверке ответа. Пожалуйста, попробуйте еще раз.")

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int, question_id: int = None) -> None:
    """Отправляет вопрос пользователю."""
    # Если это callback query, получаем данные из него
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        user = query.from_user
    else:
        chat_id = update.effective_chat.id
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
    
    # Если question_id не указан, берем первый вопрос урока
    if question_id is None:
        questions = get_questions_by_lesson(db, lesson_id)
        if not questions:
            # Если нет вопросов для урока, сообщаем об ошибке
            await context.bot.send_message(
                chat_id=chat_id,
                text="Ошибка: не найдены вопросы для этого урока."
            )
            return
        question_id = questions[0].id
    
    # Получаем вопрос из базы данных
    question = get_question(db, question_id)
    if not question:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ошибка: не удалось получить вопрос."
        )
        return
    
    # Определяем номер вопроса
    questions = get_questions_by_lesson(db, lesson_id)
    question_ids = [q.id for q in questions]
    current_idx = question_ids.index(question_id) if question_id in question_ids else 0
    question_number = current_idx + 1
    total_questions = len(questions)
    
    # Получаем варианты ответов
    options = json.loads(question.options)
    
    # Формируем текст вопроса
    question_text = (
        f"❓ *Вопрос {question_number} из {total_questions}*\n\n"
        f"{question.text}\n\n"
        "Выберите правильный ответ:\n"
    )
    
    # Добавляем варианты ответов в текст вопроса
    for i, option in enumerate(options):
        letter = chr(65 + i)  # A, B, C, D...
        question_text += f"{letter}. {option}\n"
    
    # Создаем клавиатуру с вариантами ответов (только буквы)
    keyboard = get_question_options_keyboard(question)
    
    # Отправляем вопрос с вариантами ответов
    await context.bot.send_message(
        chat_id=chat_id,
        text=question_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_retry_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки 'Попробовать еще раз'."""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    # Получаем ID вопроса из callback_data
    question_id = int(query.data.replace("retry_question_", ""))
    
    # Отправляем вопрос заново
    db = get_db()
    question = get_question(db, question_id)
    if not question:
        await query.message.reply_text("Ошибка: не удалось найти вопрос.")
        return
    
    # Используем существующую функцию для отправки вопроса
    await send_question(update, context, question.lesson_id, question_id)

async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки 'Следующий вопрос'."""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    # Получаем ID урока из callback_data
    lesson_id = int(query.data.replace("next_question_", ""))
    
    # Получаем все вопросы для урока
    db = get_db()
    questions = get_questions_by_lesson(db, lesson_id)
    question_ids = [q.id for q in questions]
    
    # Определяем текущий индекс вопроса
    current_idx = context.user_data.get('lesson_data', {}).get(lesson_id, {}).get('current_question', 0)
    
    # Увеличиваем индекс для перехода к следующему вопросу
    next_idx = current_idx + 1
    
    # Если есть следующий вопрос, отправляем его
    if next_idx < len(question_ids):
        # Обновляем текущий индекс вопроса в контексте
        if lesson_id in context.user_data.get('lesson_data', {}):
            context.user_data['lesson_data'][lesson_id]['current_question'] = next_idx
        
        # Отправляем следующий вопрос
        await send_question(update, context, lesson_id, question_ids[next_idx])
    else:
        # Если вопросы закончились, показываем результаты
        await show_lesson_results(update, context, lesson_id)

async def show_lesson_results(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int) -> None:
    """Показывает результаты урока."""
    # Если это callback query, получаем данные из него
    if update.callback_query:
        query = update.callback_query
        chat_id = query.message.chat_id
        user = query.from_user
    else:
        chat_id = update.effective_chat.id
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
    
    # Получаем урок и следующий урок
    lesson = get_lesson(db, lesson_id)
    next_lesson = get_next_lesson(db, lesson_id)
    
    # Получаем все вопросы для урока
    questions = get_questions_by_lesson(db, lesson_id)
    total_questions = len(questions)
    
    # Получаем количество правильных ответов из контекста
    correct_answers = context.user_data.get('lesson_data', {}).get(lesson_id, {}).get('correct_answers', 0)
    
    # Вычисляем процент успешности
    if total_questions > 0:
        success_percentage = (correct_answers / total_questions) * 100.0
    else:
        success_percentage = 0.0
    
    # Определяем, успешно ли пройден урок
    is_successful = success_percentage >= 80.0  # минимальный процент для успешного прохождения
    
    # Обновляем прогресс пользователя в базе данных
    from app.database.operations import update_user_progress
    update_user_progress(db, db_user.id, lesson_id, is_successful, success_percentage)
    
    # Формируем прогресс-бар
    progress_bar = get_progress_bar(success_percentage)
    
    if is_successful:
        # Отправляем стикер успешного завершения урока
        await send_lesson_success_sticker(context, chat_id)
        
        result_message = (
            f"🎉 *Поздравляем!* Вы успешно прошли урок \"{lesson.title}\".\n\n"
            f"Ваш результат: {correct_answers} из {total_questions} "
            f"({success_percentage:.1f}%)\n\n"
            f"Прогресс: {progress_bar}\n\n"
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
            f"Вы ответили правильно на {correct_answers} из {total_questions} "
            f"вопросов ({success_percentage:.1f}%)\n\n"
            f"Прогресс: {progress_bar}\n\n"
            "Для перехода к следующему уроку необходимо набрать не менее 80%.\n"
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
    await context.bot.send_message(
        chat_id=chat_id,
        text=result_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    # Очищаем данные теста
    if lesson_id in context.user_data.get('lesson_data', {}):
        del context.user_data['lesson_data'][lesson_id]

def format_explanation(explanation: str) -> str:
    """Форматирует объяснение с переносами строк для лучшей читаемости."""
    # Разбиваем объяснение на параграфы по двойным переносам строк
    paragraphs = explanation.split('\n\n')
    
    # Разбиваем каждый параграф на предложения
    formatted_paragraphs = []
    for paragraph in paragraphs:
        sentences = paragraph.split('. ')
        # Группируем предложения по 2-3 для лучшей читаемости
        formatted_paragraph = ''
        for i in range(0, len(sentences), 2):
            group = sentences[i:i+2]
            formatted_paragraph += '. '.join(group)
            if i + 2 < len(sentences):
                formatted_paragraph += '.\n'
            elif not group[-1].endswith('.'):
                formatted_paragraph += '.'
        
        formatted_paragraphs.append(formatted_paragraph)
    
    # Соединяем параграфы с двойным переносом строк
    return '\n\n'.join(formatted_paragraphs)