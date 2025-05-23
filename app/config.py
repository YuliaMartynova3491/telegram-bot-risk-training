"""
Модуль для настройки конфигурации проекта.
Исправленная версия с правильной обработкой LM Studio.
"""
import os
import pathlib
from dotenv import load_dotenv

# Получаем путь к корневой директории проекта
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()

# Проверяем и выводим информацию о загрузке .env
env_path = os.path.join(BASE_DIR, ".env")
print(f"Загрузка переменных окружения из файла: {env_path}")
print(f"Файл существует: {os.path.exists(env_path)}")

# Загружаем переменные окружения из файла .env
load_dotenv(env_path)

# Получаем токен телеграм бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if TELEGRAM_TOKEN:
    print(f"✅ Токен загружен: {TELEGRAM_TOKEN[:5]}...{TELEGRAM_TOKEN[-5:]}")
else:
    print("❌ Ошибка: токен не найден в файле .env")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///risk_training.db")

# Пути к файлам
KNOWLEDGE_DIR = BASE_DIR / "app" / "knowledge" / "jsonl"
RISK_KNOWLEDGE_PATH = KNOWLEDGE_DIR / "risk_knowledge.jsonl"

# Создаем директорию для базы знаний, если она не существует
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# Настройки обучения
MIN_SUCCESS_PERCENTAGE = 80  # Минимальный процент правильных ответов для успешного прохождения урока
QUESTIONS_PER_LESSON = 3  # Количество вопросов на один урок

# Исправленные идентификаторы стикеров
STICKERS = {
    "welcome": [
        "CAACAgIAAxkBAAEOd6RoIsd8Z1Gz2JyvVPrxpwRugDF89wAC8EAAAgMdyUh6q-4BL3FQLzYE", 
        "CAACAgIAAxkBAAEOd6xoIshSMujqTxf8Od_p7PLDGn7sUwACWToAAqePcUmYZialrHxKnTYE"
    ],
    "first_correct": "CAACAgIAAxkBAAEOd6hoIsgIXelJD9h0RgVTxLtEz_ZgMgACky4AAgFM6UhFC9JlyfY5rzYE",
    "next_correct": "CAACAgIAAxkBAAEOd6poIsggr-5-2bwnZt7t_2pJP9HWwACyCoAAkj3cUng5lb0xkBC6DYE",
    "lesson_success": "CAACAgIAAxkBAAEOd65oIsiE9oHP2Cxsg9wkj1LXFi0L1AACR18AAuphSUoma5l9yrkFmjYE",
    "topic_success": "CAACAgIAAxkBAAEOd7JoIspvfu0_4EUpFnUcpq6OUjVMEAACRFkAAnnRSUru1p89ZmyntTYE",
    "first_wrong": "CAACAgIAAxkBAAEOd6JoIsc8ZgvKw1T8QqL2CNIpNtLUzAAC_0gAApjKwEh4Jj7i8mL2AjYE",
    "next_wrong": "CAACAgIAAxkBAAEOd6ZoIsfmsGJP3o0KdTMiriW8U9sVvAACHEUAAvkKiEjOqMQN3AH2PTYE",
    "lesson_fail": "CAACAgIAAxkBAAEOd7BoIsok2pkQSuPXBxRVf26hil-35gACEywAArBkcEno5QGUqynBvzYE"
}

# Модель для RAG и генерации вопросов
LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "http://localhost:1234/v1")

# Команды для запуска бота
START_COMMANDS = ["старт", "start", "начать", "начнем", "запуск", "/start"]

# Настройки для LM Studio
LM_STUDIO_TIMEOUT = 30  # Таймаут для запросов к LM Studio
LM_STUDIO_MAX_RETRIES = 3  # Максимальное количество попыток подключения
LM_STUDIO_RETRY_DELAY = 5  # Задержка между попытками подключения (секунды)

# Настройки для генерации ответов
DEFAULT_TEMPERATURE = 0.7  # Температура для генерации ответов
DEFAULT_MAX_TOKENS = 1500  # Максимальное количество токенов в ответе

# Настройки для обработки ошибок
ENABLE_ERROR_RECOVERY = True  # Включить восстановление после ошибок
FALLBACK_TO_SIMPLE_ANSWERS = True  # Использовать простые ответы при недоступности LM Studio

print(f"✅ Конфигурация загружена успешно")
print(f"📊 DATABASE_URL: {DATABASE_URL}")
print(f"🤖 LLM_MODEL_PATH: {LLM_MODEL_PATH}")
print(f"📚 KNOWLEDGE_DIR: {KNOWLEDGE_DIR}")
print(f"⚙️ Fallback режим: {FALLBACK_TO_SIMPLE_ANSWERS}")