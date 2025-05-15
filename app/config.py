"""
Файл конфигурации проекта.
Здесь хранятся основные настройки и константы.
"""
import os
from dotenv import load_dotenv
import pathlib

# Загружаем переменные окружения из файла .env
load_dotenv()

# Токен Telegram бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7270707347:AAFqbP-c8tGX-fIe2ZlB1NZfwiANLjcYOHM")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///risk_training.db")

# Пути к файлам (используем pathlib для совместимости с разными ОС)
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()
KNOWLEDGE_DIR = BASE_DIR / "app" / "knowledge" / "jsonl"
RISK_KNOWLEDGE_PATH = KNOWLEDGE_DIR / "risk_knowledge.jsonl"

# Создаем директорию для базы знаний, если она не существует
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# Настройки обучения
MIN_SUCCESS_PERCENTAGE = 80  # Минимальный процент правильных ответов для успешного прохождения урока
QUESTIONS_PER_LESSON = 3  # Количество вопросов на один урок

# Идентификаторы стикеров
STICKERS = {
    "welcome": ["CAACAgIAAxkBAAEOd6RoIsd8Z1Gz2JyvVPrxpwRugDF89wAC8EAAAgMdyUh6q-4BL3FQLzYE", 
                "CAACAgIAAxkBAAEOd6xoIshSMujqTxf8Od_p7PLDGn7sUwACWToAAqePcUmYZialrHxKnTYE"],
    "first_correct": "CAACAgIAAxkBAAEOd6hoIsgIXelJD9h0RgVTxLtEz_ZgMgACky4AAgFM6UhFC9JlyfY5rzYE",
    "next_correct": "CAACAgIAAxkBAAEOd6poIsggr—5-2bwnZt7t_2pJP9HWwACyCoAAkj3cUng5lb0xkBC6DYE",
    "lesson_success": "CAACAgIAAxkBAAEOd65oIsiE9oHP2Cxsg9wkj1LXFi0L1AACR18AAuphSUoma5l9yrkFmjYE",
    "topic_success": "CAACAgIAAxkBAAEOd7JoIspvfu0_4EUpFnUcpq6OUjVMEAACRFkAAnnRSUru1p89ZmyntTYE",
    "first_wrong": "CAACAgIAAxkBAAEOd6JoIsc8ZgvKw1T8QqL2CNIpNtLUzAAC_0gAApjKwEh4Jj7i8mL2AjYE",
    "next_wrong": "CAACAgIAAxkBAAEOd6ZoIsfmsGJP3o0KdTMiriW8U9sVvwACHEUAAvkKiEjOqMQN3AH2PTYE",
    "lesson_fail": "CAACAgIAAxkBAAEOd7BoIsok2pkQSuPXBxRVf26hil-35gACEywAArBkcEno5QGUqynBvzYE"
}

# Модель для RAG и генерации вопросов
LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "http://localhost:1234/v1")  # URL для LM Studio

# Команды для запуска бота
START_COMMANDS = ["старт", "start", "начать", "начнем", "запуск", "/start"]