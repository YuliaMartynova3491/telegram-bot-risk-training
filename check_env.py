"""
Проверка загрузки переменных окружения из .env
"""
import os
import sys
from dotenv import load_dotenv

# Получаем абсолютный путь к файлу .env
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')

print(f"Текущая директория: {current_dir}")
print(f"Путь к .env: {env_path}")
print(f"Файл .env существует: {os.path.exists(env_path)}")

# Проверяем содержимое файла .env
if os.path.exists(env_path):
    try:
        with open(env_path, 'r') as f:
            env_content = f.read()
            print("\nСодержимое файла .env (первые 10 символов каждой строки):")
            for line in env_content.split('\n'):
                if line.strip() and not line.strip().startswith('#'):
                    # Показываем только начало строки для безопасности
                    print(f"  {line[:10]}...")
    except Exception as e:
        print(f"Ошибка при чтении файла .env: {e}")

# Загружаем переменные окружения
print("\nЗагрузка переменных окружения...")
load_dotenv(env_path)

# Проверяем, загрузилась ли переменная TELEGRAM_TOKEN
token = os.getenv("TELEGRAM_TOKEN")
if token:
    token_preview = f"{token[:5]}...{token[-5:]}"
    print(f"TELEGRAM_TOKEN загружен: {token_preview}")
else:
    print("TELEGRAM_TOKEN не найден после загрузки .env")

# Проверяем системные переменные окружения
print("\nПроверка системных переменных окружения:")
for env_var in os.environ:
    if "TOKEN" in env_var or "TELEGRAM" in env_var:
        value = os.environ[env_var]
        value_preview = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else value
        print(f"  {env_var}: {value_preview}")

print("\nГотово!")