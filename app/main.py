"""
Точка входа в приложение.
Запуск Telegram бота.
"""
import logging
import sys
import os
import asyncio
import traceback

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.bot.handlers import run_bot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Обработчик ошибок
async def error_handler(update, context):
    """Логирует ошибки и отправляет сообщение пользователю."""
    # Получаем информацию об ошибке
    error = context.error
    trace = "".join(traceback.format_tb(error.__traceback__))
    
    # Выводим полный текст ошибки в лог
    logger.error(f"Ошибка при обработке обновления: {update}")
    logger.error(f"Ошибка: {error}")
    logger.error(f"Трейс: {trace}")
    
    # Отправляем сообщение пользователю, если возможно
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."
        )

def main():
    """Основная функция для запуска приложения."""
    logger.info("Запуск бота обучения рискам нарушения непрерывности деятельности")
    logger.info("Инициализация бота...")
    
    try:
        # Проверяем наличие токена
        from app.config import TELEGRAM_TOKEN
        if not TELEGRAM_TOKEN:
            logger.error("Токен Telegram бота не найден. Проверьте файл .env и конфигурацию.")
            sys.exit(1)
        
        # Проверяем соединение с LM Studio
        try:
            from app.config import LLM_MODEL_PATH
            import requests
            
            test_headers = {"Content-Type": "application/json"}
            test_data = {"model": "local-model", "messages": [{"role": "user", "content": "test"}]}
            
            response = requests.post(
                f"{LLM_MODEL_PATH}/chat/completions", 
                headers=test_headers, 
                json=test_data,
                timeout=5
            )
            
            if response.status_code != 200:
                logger.warning(f"Не удалось подключиться к LM Studio: {response.status_code}")
                logger.warning("Бот будет запущен, но генерация вопросов может работать некорректно.")
                logger.warning("Будет использоваться запасной вариант генерации вопросов.")
            else:
                logger.info("Соединение с LM Studio установлено успешно.")
        
        except Exception as e:
            logger.warning(f"Ошибка при проверке соединения с LM Studio: {e}")
            logger.warning("Бот будет запущен, но генерация вопросов может работать некорректно.")
            logger.warning("Будет использоваться запасной вариант генерации вопросов из базы знаний.")
        
        # Запуск Telegram бота
        run_bot(error_handler)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        # Выводим полный трейс ошибки
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()