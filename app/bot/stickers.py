"""
Модуль для работы со стикерами.
Содержит функции для отправки стикеров в разных ситуациях.
"""
import random
from app.config import STICKERS

async def send_welcome_sticker(context, chat_id):
    """Отправляет приветственный стикер."""
    sticker_id = random.choice(STICKERS["welcome"])
    await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)

async def send_correct_answer_sticker(context, chat_id, is_first=True):
    """Отправляет стикер при правильном ответе."""
    sticker_id = STICKERS["first_correct"] if is_first else STICKERS["next_correct"]
    await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)

async def send_wrong_answer_sticker(context, chat_id, is_first=True):
    """Отправляет стикер при неправильном ответе."""
    sticker_id = STICKERS["first_wrong"] if is_first else STICKERS["next_wrong"]
    await context.bot.send_sticker(chat_id=chat_id, sticker=sticker_id)

async def send_lesson_success_sticker(context, chat_id):
    """Отправляет стикер при успешном прохождении урока."""
    await context.bot.send_sticker(chat_id=chat_id, sticker=STICKERS["lesson_success"])

async def send_topic_success_sticker(context, chat_id):
    """Отправляет стикер при успешном прохождении темы."""
    await context.bot.send_sticker(chat_id=chat_id, sticker=STICKERS["topic_success"])

async def send_lesson_fail_sticker(context, chat_id):
    """Отправляет стикер при неуспешном прохождении урока."""
    await context.bot.send_sticker(chat_id=chat_id, sticker=STICKERS["lesson_fail"])