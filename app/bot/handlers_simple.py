"""
Упрощенная версия обработчиков для отладки.
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.config import TELEGRAM_TOKEN

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context):
    """Обрабатывает команду /start."""
    logger.info("Обработка команды /start")
    await update.message.reply_text("Привет! Я бот для обучения рискам непрерывности деятельности.")

async def handle_message(update: Update, context):
    """Обрабатывает текстовые сообщения."""
    logger.info(f"Получено сообщение: {update.message.text}")
    await update.message.reply_text(f"Вы написали: {update.message.text}")

def run_bot():
    """Запускает Telegram бота."""
    logger.info(f"Инициализация приложения с токеном: {TELEGRAM_TOKEN[:5]}...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Настройка параметров сети
    logger.info("Настройка параметров сети...")
    application.bot._request.con_pool_size = 10
    
    # Добавление обработчиков
    logger.info("Добавление обработчиков...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота с увеличенным таймаутом
    logger.info("Запуск бота...")
    application.run_polling(timeout=60, allowed_updates=["message", "callback_query"])
