"""
Скрипт для запуска всех тестов проекта.
"""
import unittest
import sys
import os

# Добавляем корневой каталог проекта в путь импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Загружаем все тесты
loader = unittest.TestLoader()
start_dir = os.path.dirname(os.path.abspath(__file__))
suite = loader.discover(start_dir, pattern="test_*.py")

# Запускаем тесты
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Выход с кодом ошибки, если есть неудачные тесты
sys.exit(not result.wasSuccessful())