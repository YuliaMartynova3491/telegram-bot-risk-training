"""
Точка входа в приложение.
Запуск Telegram бота с поддержкой агентов.
"""
import logging
import sys
import os
import asyncio
import traceback
import requests

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.bot.handlers import run_bot, handle_callback, handle_message
from app.bot.handlers_additions import update_callback_handler, handle_message_with_question

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
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
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."
            )
        except:
            logger.error("Не удалось отправить сообщение об ошибке пользователю")

def check_lm_studio_connection(url):
    """Проверяет подключение к LM Studio."""
    try:
        # Сначала проверяем доступность моделей
        models_response = requests.get(f"{url}/models", timeout=5)
        if models_response.status_code != 200:
            logger.warning(f"Не удалось получить список моделей: {models_response.status_code}")
            return False
        
        models_data = models_response.json()
        if not models_data.get('data'):
            logger.warning("Нет доступных моделей в LM Studio")
            return False
        
        # Получаем имя первой доступной модели
        model_name = models_data['data'][0]['id']
        logger.info(f"Найдена модель: {model_name}")
        
        # Тестируем чат с найденной моделью
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Привет! Это тестовое сообщение."}],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        response = requests.post(
            f"{url}/chat/completions", 
            headers=headers, 
            json=data,
            timeout=30  # Увеличиваем таймаут для больших моделей
        )
        
        logger.info(f"Проверка подключения к LM Studio: status_code={response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info("✅ Соединение с LM Studio установлено успешно.")
            logger.info(f"✅ Активная модель: {model_name}")
            logger.info(f"✅ Ответ модели: {content[:30]}...")
            return True
        else:
            logger.warning(f"Не удалось подключиться к LM Studio: {response.status_code}")
            if hasattr(response, 'text'):
                logger.warning(f"Ответ: {response.text[:200]}...")
            return False
    except requests.exceptions.ConnectTimeout:
        logger.warning("Таймаут соединения с LM Studio. Проверьте, что сервер запущен.")
        return False
    except requests.exceptions.ConnectionError:
        logger.warning("Ошибка соединения с LM Studio. Проверьте, что LM Studio запущен и сервер активен.")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке соединения с LM Studio: {e}")
        return False

def run_bot_with_agents():
    """Запускает бота с обработчиками для агентов."""
    # Оригинальный обработчик бота
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
    from telegram import Update
    from app.config import TELEGRAM_TOKEN
    
    logger.info("Инициализация бота с поддержкой агентов...")
    
    # Инициализация данных
    from app.bot.handlers import init_data
    init_data()
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)
    
    # Добавление обработчиков с поддержкой агентов
    from app.bot.handlers import start
    application.add_handler(CommandHandler("start", start))
    
    # Используем обновленный обработчик сообщений с поддержкой обработки вопросов
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_with_question))
    
    # Обновляем обработчик callback запросов для поддержки новых типов данных
    updated_callback_handler = update_callback_handler(handle_callback)
    application.add_handler(CallbackQueryHandler(updated_callback_handler))
    
    # Запуск бота
    logger.info("Запуск бота с поддержкой агентов...")
    # Исправляем проблему с ALL_TYPES
    application.run_polling(allowed_updates=Update.ALL_TYPES)

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
            
            # Используем проверку соединения с очень коротким таймаутом
            connected = check_lm_studio_connection(LLM_MODEL_PATH)
            if connected:
                logger.info("LM Studio доступен и готов к использованию.")
                logger.info("Бот будет запущен с поддержкой агентов.")
                
                # Инициализируем модуль интеграции с агентами
                try:
                    from app.langchain.integration import agent_integration
                    agent_integration.llm_available = True
                except ImportError:
                    logger.warning("Модуль интеграции агентов не найден. Бот будет работать в базовом режиме.")
            else:
                logger.warning("LM Studio недоступен. Бот будет использовать запасной вариант генерации вопросов.")
                logger.warning("Бот продолжит работу в автономном режиме без поддержки агентов.")
                
                # Отключаем использование агентов
                try:
                    from app.langchain.integration import agent_integration
                    agent_integration.llm_available = False
                except ImportError:
                    logger.info("Модуль интеграции агентов не найден, что нормально для автономного режима.")
            
        except Exception as e:
            logger.warning(f"Ошибка при проверке соединения с LM Studio: {e}")
            logger.warning("Бот будет запущен без поддержки агентов.")
            
            # Отключаем использование агентов
            try:
                from app.langchain.integration import agent_integration
                agent_integration.llm_available = False
            except ImportError:
                logger.info("Модуль интеграции агентов не найден, что нормально для автономного режима.")
        
        # Запуск Telegram бота с обработчиками для агентов
        run_bot_with_agents()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        # Выводим полный трейс ошибки
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()