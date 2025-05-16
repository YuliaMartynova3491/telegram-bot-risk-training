"""
Упрощенная точка входа в приложение для отладки.
"""
import logging
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.bot.handlers_simple import run_bot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска приложения."""
    logger.info("Запуск упрощенной версии бота для отладки")
    
    try:
        logger.info("Инициализация бота...")
        # Запуск Telegram бота
        run_bot()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
