#!/bin/bash

# Скрипт для исправления проблем с импортами и перезапуска бота

echo "Исправление проблем с импортами..."

# Обновляем файлы с исправлениями
echo "1. Обновляем app/bot/__init__.py..."
cat > app/bot/__init__.py << 'EOF'
"""
Модуль для работы с Telegram ботом.

Этот модуль содержит компоненты для взаимодействия с Telegram API:
- handlers.py: Обработчики сообщений и команд
- keyboards.py: Функции для создания клавиатур и меню
- stickers.py: Функции для работы со стикерами
"""

# Простой модуль-заглушка без импортов, чтобы избежать циклических зависимостей
EOF

# Проверяем, есть ли файл run_bot в handlers.py
echo "2. Проверяем app/bot/handlers.py..."
if grep -q "def run_bot" app/bot/handlers.py; then
    echo "   Функция run_bot найдена в handlers.py"
else
    echo "   ВНИМАНИЕ: Функция run_bot не найдена в handlers.py"
    echo "   Это может вызвать ошибки при запуске."
fi

# Создаем временный файл для проверки импортов
echo "3. Создаем тестовый скрипт для проверки импортов..."
cat > test_imports.py << 'EOF'
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.bot.keyboards import get_main_menu_keyboard
    print("✅ Импорт get_main_menu_keyboard успешен!")
except ImportError as e:
    print(f"❌ Ошибка импорта get_main_menu_keyboard: {e}")
    sys.exit(1)

try:
    from app.bot.handlers import run_bot
    print("✅ Импорт run_bot успешен!")
except ImportError as e:
    print(f"❌ Ошибка импорта run_bot: {e}")
    sys.exit(1)

print("Все необходимые импорты работают корректно!")
EOF

# Запускаем тест импортов
echo "4. Запускаем тест импортов..."
python test_imports.py

# Если тест прошел успешно, запускаем бота
if [ $? -eq 0 ]; then
    echo "5. Запускаем бота..."
    python -m app.main
else
    echo "5. Ошибка в импортах. Бот не запущен."
    exit 1
fi

# Удаляем временный файл
rm test_imports.py