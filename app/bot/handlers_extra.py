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
    get_explanation
)
from app.bot.keyboards import get_progress_bar

logger = logging.getLogger(__name__)

async def handle_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_id: int, answer_letter: str) -> None:
    """Обрабатывает ответ на вопрос и отправляет следующий."""
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
        
        # Обновляем счетчики в контексте
        lesson_id = question.lesson_id
        context.user_data.setdefault('lesson_data', {})
        context.user_data['lesson_data'].setdefault(lesson_id, {
            'current_question': 0,
            'questions': [],
            'correct_answers': 0,
            'wrong_answers_streak': 0
        })
        
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
            
            # ИСПРАВЛЕНИЕ: Разбиваем длинный текст объяснения на абзацы для лучшей читаемости
            explanation_paragraphs = explanation.replace(". ", ".\n").split("\n")
            formatted_explanation = "\n".join(explanation_paragraphs)
            
            result_message = (
                "✅ *Правильно!*\n\n"
                f"{formatted_explanation}\n\n"
                "Переходим к следующему вопросу..."
            )
        else:
            if context.user_data['lesson_data'][lesson_id].get('wrong_answers_streak', 0) == 1:
                await send_wrong_answer_sticker(context, chat_id, is_first=True)
            else:
                await send_wrong_answer_sticker(context, chat_id, is_first=False)
            
            # ИСПРАВЛЕНИЕ: Разбиваем длинный текст объяснения на абзацы для лучшей читаемости
            explanation_paragraphs = explanation.replace(". ", ".\n").split("\n")
            formatted_explanation = "\n".join(explanation_paragraphs)
            
            # ИСПРАВЛЕНИЕ: Добавляем правильный ответ в читаемом формате
            try:
                options = json.loads(question.options)
                correct_index = ord(question.correct_answer) - ord('A')
                correct_option = options[correct_index] if 0 <= correct_index < len(options) else "Неизвестный вариант"
                
                result_message = (
                    "❌ *Неправильный ответ*\n\n"
                    f"Правильный ответ: *{question.correct_answer}*\n"
                    f"{correct_option}\n\n"
                    f"{formatted_explanation}\n\n"
                    "Переходим к следующему вопросу..."
                )
            except Exception as e:
                logger.error(f"Ошибка при форматировании объяснения: {e}")
                result_message = (
                    "❌ *Неправильный ответ*\n\n"
                    f"Правильный ответ: *{question.correct_answer}*\n\n"
                    f"{formatted_explanation}\n\n"
                    "Переходим к следующему вопросу..."
                )
        
        # Отправляем сообщение с результатом
        await query.message.edit_text(
            result_message,
            parse_mode="Markdown"
        )
        
        # Получаем все вопросы урока
        from app.learning.questions import get_questions_by_lesson
        all_questions = get_questions_by_lesson(db, lesson_id)
        question_ids = [q.id for q in all_questions]
        
        # Увеличиваем индекс текущего вопроса
        current_idx = question_ids.index(question_id) if question_id in question_ids else -1
        next_idx = current_idx + 1
        
        # Небольшая задержка перед следующим вопросом
        await asyncio.sleep(2)
        
        # Отправляем следующий вопрос или показываем результаты
        if next_idx < len(question_ids):
            # Отправляем следующий вопрос
            from app.bot.keyboards import get_question_options_keyboard
            next_question = get_question(db, question_ids[next_idx])
            
            message = (
                f"❓ *Вопрос {next_idx + 1} из {len(question_ids)}*\n\n"
                f"{next_question.text}\n\n"
                "Выберите правильный ответ:"
            )
            
            keyboard = get_question_options_keyboard(next_question)
            
            await query.message.edit_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # Показываем результаты
            from app.learning.questions import check_lesson_completion
            
            completion_data = check_lesson_completion(db_user.id, lesson_id)
            
            # Получаем урок и следующий урок
            lesson = get_lesson(db, lesson_id)
            next_lesson = get_next_lesson(db, lesson_id)
            
            # Определяем, успешно ли пройден тест
            is_successful = completion_data["is_successful"]
            success_percentage = completion_data["success_percentage"]
            
            # Формируем прогресс-бар
            progress_bar = get_progress_bar(success_percentage)
            
            if is_successful:
                # Отправляем стикер успешного завершения урока
                await send_lesson_success_sticker(context, chat_id)
                
                result_message = (
                    f"🎉 *Поздравляем!* Вы успешно прошли урок \"{lesson.title}\".\n\n"
                    f"Ваш результат: {context.user_data['lesson_data'][lesson_id].get('correct_answers', 0)} из {len(question_ids)} "
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
                    f"Вы ответили правильно на {context.user_data['lesson_data'][lesson_id].get('correct_answers', 0)} из {len(question_ids)} "
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
            await query.message.edit_text(
                result_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            # Очищаем данные теста
            if lesson_id in context.user_data.get('lesson_data', {}):
                del context.user_data['lesson_data'][lesson_id]
    
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа на вопрос: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.message.reply_text("Произошла ошибка при обработке ответа. Пожалуйста, попробуйте еще раз.")