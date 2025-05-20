"""
Скрипт проверки импортов в проекте.
Запустите этот скрипт, чтобы проверить, что все импорты работают корректно.
"""

import sys
import os
import importlib

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_import(module_name, item_name=None):
    """
    Проверяет возможность импорта модуля или элемента из модуля.
    Возвращает True, если импорт успешен, иначе False.
    """
    try:
        module = importlib.import_module(module_name)
        if item_name:
            getattr(module, item_name)
        print(f"✅ Импорт {module_name}{f'.{item_name}' if item_name else ''} успешен!")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля {module_name}: {e}")
        return False
    except AttributeError as e:
        print(f"❌ Ошибка импорта {module_name}.{item_name}: {e}")
        return False

# Проверяем основные импорты
print("Проверка основных импортов...")
check_import('app.config')
check_import('app.database.models')
check_import('app.database.operations')

# Проверяем импорты модуля bot
print("\nПроверка импортов модуля bot...")
check_import('app.bot')
check_import('app.bot.keyboards')
check_import('app.bot.stickers')
check_import('app.bot.handlers')

# Проверяем конкретные функции из проблемных модулей
print("\nПроверка конкретных функций из модуля keyboards...")
check_import('app.bot.keyboards', 'get_main_menu_keyboard')
check_import('app.bot.keyboards', 'get_courses_keyboard')
check_import('app.bot.keyboards', 'get_lessons_keyboard')

# Проверяем функцию run_bot
print("\nПроверка функции run_bot из модуля handlers...")
check_import('app.bot.handlers', 'run_bot')

print("\nПроверка импортов завершена!")