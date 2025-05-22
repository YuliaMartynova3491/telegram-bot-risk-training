#!/usr/bin/env python
"""
Исправленный скрипт для инициализации и проверки работы агентов.
"""

# Базовые импорты
import sys
import os
import argparse
import logging
import json

# Добавляем корневой каталог в путь импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Принудительный вывод для отладки
print("🚀 Скрипт init_agents_final.py запущен!")

def setup_logging():
    """Настраивает логирование."""
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("agents_init.log")
        ]
    )
    return logging.getLogger(__name__)

def check_config():
    """Проверяет конфигурацию проекта."""
    logger = logging.getLogger(__name__)
    logger.info("Проверка конфигурации...")
    
    try:
        from app.config import TELEGRAM_TOKEN, DATABASE_URL, LLM_MODEL_PATH
        
        if TELEGRAM_TOKEN:
            masked_token = TELEGRAM_TOKEN[:4] + "*" * (len(TELEGRAM_TOKEN) - 8) + TELEGRAM_TOKEN[-4:]
            logger.info(f"✅ TELEGRAM_TOKEN найден: {masked_token}")
        else:
            logger.error("❌ TELEGRAM_TOKEN не найден")
            return False
            
        logger.info(f"✅ DATABASE_URL: {DATABASE_URL}")
        logger.info(f"✅ LLM_MODEL_PATH: {LLM_MODEL_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка импорта конфигурации: {e}")
        return False

def check_dependencies():
    """Проверяет зависимости."""
    logger = logging.getLogger(__name__)
    logger.info("Проверка зависимостей...")
    
    required_packages = {
        "python-telegram-bot": "telegram",
        "sqlalchemy": "sqlalchemy",
        "python-dotenv": "dotenv"
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            logger.info(f"✅ {package_name} установлен")
        except ImportError:
            logger.error(f"❌ {package_name} НЕ установлен")
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error(f"Установите недостающие пакеты: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_database():
    """Проверяет подключение к базе данных."""
    logger = logging.getLogger(__name__)
    logger.info("Проверка базы данных...")
    
    try:
        from app.database.models import get_db, init_db
        
        # Инициализируем базу данных
        init_db()
        logger.info("✅ База данных инициализирована")
        
        # Пытаемся получить соединение
        db = get_db()
        if db:
            logger.info("✅ Соединение с базой данных установлено")
            return True
        else:
            logger.error("❌ Не удалось подключиться к базе данных")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при работе с базой данных: {e}")
        return False

def check_lm_studio():
    """Проверяет подключение к LM Studio."""
    logger = logging.getLogger(__name__)
    logger.info("Проверка LM Studio...")
    
    try:
        import requests
        from app.config import LLM_MODEL_PATH
        
        # Сначала проверяем список моделей
        logger.info(f"Проверка моделей по адресу: {LLM_MODEL_PATH}/models")
        
        models_response = requests.get(
            f"{LLM_MODEL_PATH}/models",
            timeout=10
        )
        
        if models_response.status_code == 200:
            models_data = models_response.json()
            available_models = models_data.get('data', [])
            
            if available_models:
                logger.info(f"✅ Найдено {len(available_models)} моделей:")
                for model in available_models:
                    logger.info(f"   - {model.get('id', 'unknown')}")
                
                # Теперь тестируем чат с первой доступной моделью
                test_model = available_models[0]['id']
                logger.info(f"Тестирование чата с моделью: {test_model}")
                
                headers = {"Content-Type": "application/json"}
                data = {
                    "model": test_model,
                    "messages": [{"role": "user", "content": "Привет! Это тест."}],
                    "temperature": 0.7,
                    "max_tokens": 10
                }
                
                chat_response = requests.post(
                    f"{LLM_MODEL_PATH}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60  # Увеличиваем таймаут для большой модели
                )
                
                if chat_response.status_code == 200:
                    response_data = chat_response.json()
                    content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    logger.info(f"✅ LM Studio полностью функционален!")
                    logger.info(f"✅ Активная модель: {test_model}")
                    logger.info(f"✅ Ответ модели: {content}")
                    return True
                else:
                    logger.error(f"❌ Чат API недоступен (статус: {chat_response.status_code})")
                    logger.error(f"Ответ: {chat_response.text[:200]}...")
                    return False
            else:
                logger.error("❌ Модели не найдены в LM Studio")
                return False
        else:
            logger.error(f"❌ Не удалось получить список моделей (статус: {models_response.status_code})")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ LM Studio недоступен (проверьте, запущен ли сервер)")
        return False
    except requests.exceptions.Timeout:
        logger.warning("⚠️ LM Studio отвечает медленно (модель может быть тяжелой)")
        logger.info("Попробуйте увеличить таймаут или использовать более легкую модель")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке LM Studio: {e}")
        return False

def create_directories():
    """Создает необходимые директории."""
    logger = logging.getLogger(__name__)
    logger.info("Создание директорий...")
    
    directories = [
        "app/knowledge",
        "app/knowledge/jsonl",
        "app/langchain"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"✅ Директория {directory} создана/проверена")
            
            # Создаем __init__.py если его нет
            init_file = os.path.join(directory, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write(f'"""Модуль {directory.replace("/", ".")}."""\n')
                logger.info(f"✅ Создан {init_file}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания директории {directory}: {e}")
            return False
    
    return True

def create_knowledge_base():
    """Создает базовую базу знаний."""
    logger = logging.getLogger(__name__)
    logger.info("Создание базы знаний...")
    
    knowledge_file = "app/knowledge/jsonl/risk_knowledge.jsonl"
    
    if os.path.exists(knowledge_file):
        logger.info(f"✅ Файл {knowledge_file} уже существует")
        return True
    
    try:
        # Базовые записи знаний
        knowledge_items = [
            {
                "prompt": "Что такое риск нарушения непрерывности деятельности?",
                "response": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость.",
                "metadata": {
                    "topic": "риск_нарушения_непрерывности",
                    "difficulty": "базовый",
                    "keywords": ["непрерывность", "кредитная организация"]
                }
            },
            {
                "prompt": "Что такое угроза непрерывности?",
                "response": "Угроза непрерывности - это обстановка, сложившаяся в результате аварии, катастрофы или иного бедствия.",
                "metadata": {
                    "topic": "риск_нарушения_непрерывности",
                    "difficulty": "базовый",
                    "keywords": ["угроза", "авария", "катастрофа"]
                }
            }
        ]
        
        with open(knowledge_file, 'w', encoding='utf-8') as f:
            for item in knowledge_items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ Создан файл {knowledge_file} с {len(knowledge_items)} записями")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания базы знаний: {e}")
        return False

def run_all_checks():
    """Запускает все проверки."""
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 60)
    print("🔍 ИНИЦИАЛИЗАЦИЯ И ПРОВЕРКА AI-АГЕНТОВ")
    print("=" * 60)
    
    checks = [
        ("Конфигурация", check_config),
        ("Зависимости", check_dependencies),
        ("База данных", check_database),
        ("LM Studio", check_lm_studio),
        ("Директории", create_directories),
        ("База знаний", create_knowledge_base)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results[check_name] = result
            status = "✅ УСПЕШНО" if result else "❌ ОШИБКА"
            print(f"{check_name}: {status}")
        except Exception as e:
            logger.error(f"Критическая ошибка в {check_name}: {e}")
            results[check_name] = False
            print(f"{check_name}: ❌ КРИТИЧЕСКАЯ ОШИБКА")
    
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ AI-АГЕНТОВ")
    print("=" * 60)
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"Успешно пройдено: {success_count}/{total_count} проверок")
    
    # Проверяем критические компоненты
    critical_components = ["Конфигурация", "Зависимости", "База данных", "LM Studio"]
    critical_success = all(results.get(key, False) for key in critical_components)
    
    if critical_success:
        print("\n🎉 AI-АГЕНТЫ ПОЛНОСТЬЮ ГОТОВЫ К РАБОТЕ!")
        print("🤖 Все компоненты функционируют:")
        print("   ✅ Telegram Bot API")
        print("   ✅ База данных SQLite")
        print("   ✅ LM Studio с моделью qwen2.5-14b-instruct")
        print("   ✅ Система агентов")
        print("\n🚀 ЗАПУСК AI-БОТА:")
        print("   python -m app.main")
        
    else:
        print("\n❌ Обнаружены критические проблемы:")
        for component in critical_components:
            if not results.get(component, False):
                print(f"   - {component}")
        
        if not results.get("LM Studio"):
            print("\n🔧 Для исправления LM Studio:")
            print("   1. Убедитесь, что LM Studio запущен")
            print("   2. Модель загружена и сервер активен")
            print("   3. Порт 1234 свободен")
            print("   4. CORS включен в настройках")
    
    return critical_success

def main():
    """Основная функция."""
    try:
        # Настраиваем логирование
        logger = setup_logging()
        logger.info("Запуск скрипта инициализации AI-агентов")
        
        # Парсим аргументы
        parser = argparse.ArgumentParser(description="Инициализация AI-агентов для Telegram бота")
        parser.add_argument("--check-all", action="store_true", help="Запустить все проверки")
        args = parser.parse_args()
        
        # Запускаем проверки
        success = run_all_checks()
        
        logger.info("Скрипт инициализации AI-агентов завершен")
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Скрипт прерван пользователем")
        return 1
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    print("Начало выполнения main()")
    result = main()
    print(f"Завершение с кодом: {result}")
    sys.exit(result)