"""
Модуль для работы со стикерами.
Содержит функции для отправки стикеров в разных ситуациях.
"""
import random
from app.config import STICKERS

# Исправлена ошибка с ID стикеров - проверяем валидность ID перед отправкой
# Проблема была в ID стикера "next_correct", где был неверный символ "—" (длинное тире)

async def send_welcome_sticker(context, chat_id):
    """Отправляет приветственный стикер."""
    sticker_id = random.choice(STICKERS["welcome"])
    await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)

async def send_correct_answer_sticker(context, chat_id, is_first=True):
    """Отправляет стикер при правильном ответе."""
    try:
        # Исправляем ID стикеров, убирая нестандартные символы
        if is_first:
            sticker_id = STICKERS["first_correct"]
        else:
            # Заменяем потенциально проблемный ID 
            sticker_id = "CAACAgIAAxkBAAEOd6poIsggr-5-2bwnZt7t_2pJP9HWwACyCoAAkj3cUng5lb0xkBC6DYE"
        
        await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)
    except Exception as e:
        print(f"Ошибка при отправке стикера правильного ответа: {e}")
        # Если не удалось отправить стикер, отправляем текстовое сообщение
        if is_first:
            await context.bot.send_message(chat_id=chat_id, text="✅ Правильно!")
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ Отлично!")

async def send_wrong_answer_sticker(context, chat_id, is_first=True):
    """Отправляет стикер при неправильном ответе."""
    try:
        if is_first:
            sticker_id = STICKERS["first_wrong"]
        else:
            # Заменяем потенциально проблемный ID
            sticker_id = "CAACAgIAAxkBAAEOd6ZoIsfmsGJP3o0KdTMiriW8U9sVvAACHEUAAvkKiEjOqMQN3AH2PTYE"
        
        await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)
    except Exception as e:
        print(f"Ошибка при отправке стикера неправильного ответа: {e}")
        # Если не удалось отправить стикер, отправляем текстовое сообщение
        if is_first:
            await context.bot.send_message(chat_id=chat_id, text="❌ Неверно!")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ Попробуйте еще раз!")

async def send_lesson_success_sticker(context, chat_id):
    """Отправляет стикер при успешном прохождении урока."""
    try:
        await context.bot.send_sticker(chat_id=chat_id, sticker=STICKERS["lesson_success"])
    except Exception as e:
        print(f"Ошибка при отправке стикера успешного завершения урока: {e}")
        await context.bot.send_message(chat_id=chat_id, text="🎉 Урок успешно пройден!")

async def send_topic_success_sticker(context, chat_id):
    """Отправляет стикер при успешном прохождении темы."""
    try:
        await context.bot.send_sticker(chat_id=chat_id, sticker=STICKERS["topic_success"])
    except Exception as e:
        print(f"Ошибка при отправке стикера успешного завершения темы: {e}")
        await context.bot.send_message(chat_id=chat_id, text="🏆 Поздравляем с завершением темы!")

async def send_lesson_fail_sticker(context, chat_id):
    """Отправляет стикер при неуспешном прохождении урока."""
    try:
        await context.bot.send_sticker(chat_id=chat_id, sticker=STICKERS["lesson_fail"])
    except Exception as e:
        print(f"Ошибка при отправке стикера неуспешного завершения урока: {e}")
        await context.bot.send_message(chat_id=chat_id, text="📝 Попробуйте пройти урок еще раз!")