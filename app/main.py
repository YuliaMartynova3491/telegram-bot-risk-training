"""
Точка входа в приложение.
Запуск Telegram бота.
"""
import logging
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.bot.handlers import run_bot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска приложения."""
    logger.info("Запуск бота обучения рискам нарушения непрерывности деятельности")
    
    try:
        # Запуск Telegram бота
        run_bot()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()