"""
Точка входа в Enhanced AI Learning Bot.
Запуск Telegram бота с полной поддержкой AI-агентов и RAG.
"""
import logging
import sys
import os
import asyncio
import traceback
import signal
from typing import Optional

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update

# Настройка логирования
def setup_logging(level: str = "INFO"):
    """Настройка системы логирования."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Создаем директорию для логов
    os.makedirs("logs", exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler("logs/bot.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Настройка корневого логгера
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, console_handler]
    )
    
    return logging.getLogger(__name__)

class EnhancedBot:
    """Класс для управления улучшенным ботом."""
    
    def __init__(self):
        """Инициализация бота."""
        self.logger = setup_logging()
        self.application: Optional[Application] = None
        self.enhanced_system_available = False
        self.rag_available = False
        self.agents_available = False
        
    async def initialize_systems(self) -> bool:
        """Инициализация всех систем бота."""
        try:
            self.logger.info("🚀 Инициализация Enhanced AI Learning Bot...")
            
            # Проверяем конфигурацию
            success = await self._check_configuration()
            if not success:
                return False
            
            # Инициализируем базу данных
            success = await self._initialize_database()
            if not success:
                return False
            
            # Инициализируем улучшенные системы (опционально)
            await self._initialize_enhanced_systems()
            
            # Создаем Telegram приложение
            success = await self._create_telegram_application()
            if not success:
                return False
            
            self.logger.info("✅ Все системы успешно инициализированы")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка инициализации: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def _check_configuration(self) -> bool:
        """Проверка конфигурации."""
        try:
            from app.config import TELEGRAM_TOKEN, DATABASE_URL
            
            if not TELEGRAM_TOKEN:
                self.logger.error("❌ TELEGRAM_TOKEN не установлен")
                self.logger.error("Создайте файл .env и добавьте токен от @BotFather")
                return False
            
            if len(TELEGRAM_TOKEN) < 20:
                self.logger.error("❌ TELEGRAM_TOKEN выглядит некорректно")
                return False
            
            self.logger.info(f"✅ Конфигурация загружена")
            self.logger.info(f"✅ База данных: {DATABASE_URL}")
            
            return True
            
        except ImportError as e:
            self.logger.error(f"❌ Ошибка импорта конфигурации: {e}")
            return False
    
    async def _initialize_database(self) -> bool:
        """Инициализация базы данных."""
        try:
            from app.database.models import init_db
            from app.learning.courses import init_courses
            from app.learning.lessons import init_lessons
            
            # Инициализируем базу данных
            init_db()
            self.logger.info("✅ База данных инициализирована")
            
            # Инициализируем курсы
            courses = init_courses()
            self.logger.info(f"✅ Инициализировано {len(courses)} курсов")
            
            # Инициализируем уроки для каждого курса
            for course in courses:
                lessons = init_lessons(course.id)
                self.logger.info(f"✅ Курс '{course.name}': {len(lessons)} уроков")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            return False
    
    async def _initialize_enhanced_systems(self):
        """Инициализация улучшенных систем (опционально)."""
        # Пытаемся инициализировать улучшенную систему обучения
        try:
            from app.core.enhanced_integration import initialize_enhanced_system
            
            self.logger.info("🧠 Инициализация улучшенной системы обучения...")
            self.enhanced_system_available = await initialize_enhanced_system()
            
            if self.enhanced_system_available:
                self.logger.info("✅ Улучшенная система обучения активна")
                
                # Проверяем доступность RAG
                try:
                    from app.knowledge.rag_advanced import rag_system
                    self.rag_available = rag_system.is_initialized
                    if self.rag_available:
                        self.logger.info("✅ RAG система активна")
                    else:
                        self.logger.warning("⚠️ RAG система недоступна")
                except ImportError:
                    self.logger.warning("⚠️ RAG модули не установлены")
                
                # Проверяем доступность агентов
                try:
                    from app.langchain.enhanced_agents import enhanced_agent_system
                    self.agents_available = enhanced_agent_system.is_available
                    if self.agents_available:
                        self.logger.info("✅ Система агентов активна")
                    else:
                        self.logger.warning("⚠️ Система агентов недоступна (LLM недоступен)")
                except ImportError:
                    self.logger.warning("⚠️ Модули агентов не установлены")
            else:
                self.logger.warning("⚠️ Улучшенная система обучения недоступна")
                
        except ImportError:
            self.logger.warning("⚠️ Модули улучшенной системы не установлены")
            self.logger.info("ℹ️ Бот будет работать в базовом режиме")
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка инициализации улучшенных систем: {e}")
    
    async def _create_telegram_application(self) -> bool:
        """Создание Telegram приложения."""
        try:
            from app.config import TELEGRAM_TOKEN
            
            # Создаем приложение
            self.application = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # Добавляем обработчик ошибок
            self.application.add_error_handler(self._error_handler)
            
            # Добавляем обработчики команд и сообщений
            await self._setup_handlers()
            
            self.logger.info("✅ Telegram приложение создано")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания Telegram приложения: {e}")
            return False
    
    async def _setup_handlers(self):
        """Настройка обработчиков сообщений."""
        try:
            if self.enhanced_system_available:
                # Используем улучшенные обработчики
                from app.bot.enhanced_handlers import (
                    enhanced_start,
                    enhanced_handle_message,
                    enhanced_handle_callback
                )
                
                self.application.add_handler(CommandHandler("start", enhanced_start))
                self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_handle_message))
                self.application.add_handler(CallbackQueryHandler(enhanced_handle_callback))
                
                self.logger.info("✅ Подключены улучшенные обработчики")
            else:
                # Используем базовые обработчики
                from app.bot.handlers import start, handle_message, handle_callback
                
                self.application.add_handler(CommandHandler("start", start))
                self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
                self.application.add_handler(CallbackQueryHandler(handle_callback))
                
                self.logger.info("✅ Подключены базовые обработчики")
            
        except ImportError as e:
            self.logger.error(f"❌ Ошибка импорта обработчиков: {e}")
            # Fallback к базовым обработчикам
            from app.bot.handlers import start, handle_message, handle_callback
            
            self.application.add_handler(CommandHandler("start", start))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            self.application.add_handler(CallbackQueryHandler(handle_callback))
            
            self.logger.info("✅ Подключены fallback обработчики")
    
    async def _error_handler(self, update: Update, context):
        """Обработчик ошибок."""
        try:
            error = context.error
            
            # Логируем ошибку
            self.logger.error(f"Ошибка при обработке обновления: {update}")
            self.logger.error(f"Ошибка: {error}")
            self.logger.error("".join(traceback.format_tb(error.__traceback__)))
            
            # Отправляем сообщение пользователю, если возможно
            if update and update.effective_chat:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="😔 Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или обратитесь к администратору."
                    )
                except Exception:
                    self.logger.error("Не удалось отправить сообщение об ошибке пользователю")
                    
        except Exception as e:
            self.logger.error(f"Ошибка в обработчике ошибок: {e}")
    
    async def start(self):
        """Запуск бота."""
        try:
            self.logger.info("🚀 Запуск Enhanced AI Learning Bot...")
            
            # Выводим информацию о доступных системах
            self._log_system_status()
            
            # Настройка обработки сигналов для graceful shutdown
            self._setup_signal_handlers()
            
            # Запуск приложения
            self.logger.info("📡 Начинаю polling...")
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка запуска: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def _log_system_status(self):
        """Вывод статуса систем."""
        self.logger.info("=" * 60)
        self.logger.info("📊 СТАТУС СИСТЕМ")
        self.logger.info("=" * 60)
        self.logger.info(f"🤖 Enhanced Learning System: {'✅ Активна' if self.enhanced_system_available else '❌ Недоступна'}")
        self.logger.info(f"🧠 RAG System: {'✅ Активна' if self.rag_available else '❌ Недоступна'}")
        self.logger.info(f"👥 AI Agents: {'✅ Активны' if self.agents_available else '❌ Недоступны'}")
        self.logger.info("=" * 60)
        
        if not self.enhanced_system_available:
            self.logger.info("ℹ️ Для активации улучшенных функций:")
            self.logger.info("   1. Установите дополнительные зависимости: pip install sentence-transformers faiss-cpu langchain")
            self.logger.info("   2. Запустите LM Studio с загруженной моделью")
            self.logger.info("   3. Запустите инициализацию: python init_enhanced_system.py")
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов."""
        def signal_handler(signum, frame):
            self.logger.info(f"📡 Получен сигнал {signum}, завершение работы...")
            if self.application:
                asyncio.create_task(self.application.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def stop(self):
        """Остановка бота."""
        try:
            self.logger.info("🛑 Остановка бота...")
            
            if self.application:
                await self.application.stop()
                
            self.logger.info("✅ Бот успешно остановлен")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при остановке бота: {e}")

async def main():
    """Основная функция запуска."""
    bot = EnhancedBot()
    
    try:
        # Инициализация всех систем
        success = await bot.initialize_systems()
        if not success:
            print("❌ Не удалось инициализировать бота")
            print("💡 Попробуйте запустить: python init_enhanced_system.py")
            return 1
        
        # Запуск бота
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n⚠️ Получен сигнал прерывания...")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        traceback.print_exc()
        return 1
    finally:
        await bot.stop()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
        sys.exit(0)