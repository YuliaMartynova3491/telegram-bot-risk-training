#!/usr/bin/env python
"""
Улучшенный скрипт инициализации системы с полной проверкой всех компонентов.
init_enhanced_system.py
"""
import sys
import os
import asyncio
import argparse
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Добавляем корневой каталог в путь импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging(verbose: bool = False):
    """Настройка логирования."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("enhanced_system_init.log")
        ]
    )
    return logging.getLogger(__name__)

class SystemInitializer:
    """Класс для инициализации всей системы."""
    
    def __init__(self, logger):
        self.logger = logger
        self.checks_results = {}
        self.warnings = []
        self.errors = []
    
    async def run_full_initialization(self) -> bool:
        """Запуск полной инициализации системы."""
        self.logger.info("=" * 80)
        self.logger.info("🚀 ЗАПУСК ПОЛНОЙ ИНИЦИАЛИЗАЦИИ ENHANCED AI LEARNING BOT")
        self.logger.info("=" * 80)
        
        # Список всех проверок
        checks = [
            ("🔧 Конфигурация", self.check_configuration),
            ("📦 Зависимости", self.check_dependencies),
            ("🗄️ База данных", self.check_database),
            ("🤖 LM Studio", self.check_lm_studio),
            ("🧠 RAG система", self.check_rag_system),
            ("👥 Система агентов", self.check_agents_system),
            ("📚 База знаний", self.check_knowledge_base),
            ("🎯 Генератор вопросов", self.check_question_generator),
            ("🔗 Интеграция систем", self.check_system_integration),
            ("📊 Аналитика", self.check_analytics_system)
        ]
        
        # Выполняем проверки
        for check_name, check_func in checks:
            self.logger.info(f"\n{check_name}...")
            try:
                start_time = time.time()
                result = await check_func()
                elapsed = time.time() - start_time
                
                self.checks_results[check_name] = result
                status = "✅ УСПЕШНО" if result else "❌ ОШИБКА"
                self.logger.info(f"{check_name}: {status} ({elapsed:.1f}s)")
                
            except Exception as e:
                self.checks_results[check_name] = False
                self.errors.append(f"{check_name}: {str(e)}")
                self.logger.error(f"{check_name}: ❌ КРИТИЧЕСКАЯ ОШИБКА - {e}")
        
        # Генерируем отчет
        return self.generate_final_report()
    
    async def check_configuration(self) -> bool:
        """Проверка конфигурации."""
        try:
            from app.config import TELEGRAM_TOKEN, DATABASE_URL, LLM_MODEL_PATH
            
            if not TELEGRAM_TOKEN:
                self.errors.append("TELEGRAM_TOKEN не установлен")
                return False
            
            if len(TELEGRAM_TOKEN) < 20:
                self.warnings.append("TELEGRAM_TOKEN выглядит некорректно")
            
            self.logger.info(f"✅ DATABASE_URL: {DATABASE_URL}")
            self.logger.info(f"✅ LLM_MODEL_PATH: {LLM_MODEL_PATH}")
            
            # Проверяем необходимые директории
            required_dirs = [
                "app/knowledge",
                "app/knowledge/jsonl",
                "app/langchain",
                "logs"
            ]
            
            for dir_path in required_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                self.logger.info(f"✅ Директория {dir_path} готова")
            
            return True
            
        except ImportError as e:
            self.errors.append(f"Ошибка импорта конфигурации: {e}")
            return False
    
    async def check_dependencies(self) -> bool:
        """Проверка зависимостей."""
        required_packages = {
            "telegram": "python-telegram-bot",
            "sqlalchemy": "sqlalchemy", 
            "dotenv": "python-dotenv",
            "requests": "requests"
        }
        
        optional_packages = {
            "sentence_transformers": "sentence-transformers",
            "faiss": "faiss-cpu",
            "numpy": "numpy",
            "langchain": "langchain",
            "langchain_core": "langchain-core"
        }
        
        missing_required = []
        missing_optional = []
        
        # Проверяем обязательные пакеты
        for import_name, package_name in required_packages.items():
            try:
                __import__(import_name)
                self.logger.info(f"✅ {package_name}")
            except ImportError:
                missing_required.append(package_name)
                self.logger.error(f"❌ {package_name} (ОБЯЗАТЕЛЬНЫЙ)")
        
        # Проверяем опциональные пакеты
        for import_name, package_name in optional_packages.items():
            try:
                __import__(import_name)
                self.logger.info(f"✅ {package_name}")
            except ImportError:
                missing_optional.append(package_name)
                self.logger.warning(f"⚠️ {package_name} (опциональный)")
        
        if missing_required:
            self.errors.append(f"Отсутствуют обязательные пакеты: {', '.join(missing_required)}")
            return False
        
        if missing_optional:
            self.warnings.append(f"Отсутствуют опциональные пакеты: {', '.join(missing_optional)}")
        
        return True
    
    async def check_database(self) -> bool:
        """Проверка базы данных."""
        try:
            from app.database.models import init_db, get_db, test_connection
            from app.database.operations import get_all_courses
            
            # Инициализируем БД
            init_db()
            self.logger.info("✅ База данных инициализирована")
            
            # Тестируем соединение
            if not test_connection():
                self.errors.append("Не удалось подключиться к базе данных")
                return False
            
            # Проверяем данные
            db = get_db()
            courses = get_all_courses(db)
            self.logger.info(f"✅ Найдено {len(courses)} курсов в БД")
            
            return True
            
        except Exception as e:
            self.errors.append(f"Ошибка базы данных: {e}")
            return False
    
    async def check_lm_studio(self) -> bool:
        """Проверка LM Studio."""
        try:
            import requests
            from app.config import LLM_MODEL_PATH
            
            # Проверяем доступность сервера
            try:
                models_response = requests.get(f"{LLM_MODEL_PATH}/models", timeout=10)
                if models_response.status_code != 200:
                    self.warnings.append(f"LM Studio недоступен (код: {models_response.status_code})")
                    return False
            except requests.exceptions.ConnectionError:
                self.warnings.append("LM Studio недоступен (нет соединения)")
                return False
            except requests.exceptions.Timeout:
                self.warnings.append("LM Studio недоступен (таймаут)")
                return False
            
            # Получаем список моделей
            models_data = models_response.json()
            available_models = models_data.get('data', [])
            
            if not available_models:
                self.warnings.append("В LM Studio нет загруженных моделей")
                return False
            
            # Тестируем чат API
            test_model = available_models[0]['id']
            headers = {"Content-Type": "application/json"}
            data = {
                "model": test_model,
                "messages": [{"role": "user", "content": "Test"}],
                "temperature": 0.7,
                "max_tokens": 10
            }
            
            chat_response = requests.post(
                f"{LLM_MODEL_PATH}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if chat_response.status_code == 200:
                response_data = chat_response.json()
                content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                self.logger.info(f"✅ LM Studio полностью функционален")
                self.logger.info(f"✅ Активная модель: {test_model}")
                self.logger.info(f"✅ Тестовый ответ: {content}")
                return True
            else:
                self.warnings.append(f"Chat API недоступен (код: {chat_response.status_code})")
                return False
            
        except Exception as e:
            self.warnings.append(f"Ошибка проверки LM Studio: {e}")
            return False
    
    async def check_rag_system(self) -> bool:
        """Проверка RAG системы."""
        try:
            from app.knowledge.rag_advanced import rag_system, initialize_rag
            
            # Пытаемся инициализировать RAG
            rag_initialized = await initialize_rag()
            
            if rag_initialized:
                self.logger.info("✅ RAG система инициализирована")
                
                # Тестируем поиск
                try:
                    search_results = await rag_system.search("риск непрерывности", top_k=3)
                    self.logger.info(f"✅ Поиск работает: найдено {len(search_results)} результатов")
                    
                    # Тестируем генерацию ответа
                    if search_results:
                        rag_response = await rag_system.generate_answer("Что такое риск нарушения непрерывности?")
                        self.logger.info(f"✅ Генерация ответов работает (уверенность: {rag_response.confidence:.2f})")
                    
                except Exception as e:
                    self.warnings.append(f"RAG функции работают частично: {e}")
                
                return True
            else:
                self.warnings.append("RAG система не инициализирована")
                return False
                
        except ImportError:
            self.warnings.append("RAG модули недоступны (отсутствуют зависимости)")
            return False
        except Exception as e:
            self.warnings.append(f"Ошибка RAG системы: {e}")
            return False
    
    async def check_agents_system(self) -> bool:
        """Проверка системы агентов."""
        try:
            from app.langchain.enhanced_agents import enhanced_agent_system, LearningContext
            
            if enhanced_agent_system.is_available:
                self.logger.info("✅ Система агентов доступна")
                
                # Тестируем агентов
                test_context = LearningContext(
                    user_id=1,
                    lesson_id=1,
                    topic="test",
                    question_text="Тестовый вопрос?",
                    user_answer="A",
                    correct_answer="A"
                )
                
                try:
                    assessment = await enhanced_agent_system.assess_knowledge(test_context)
                    if assessment.success:
                        self.logger.info("✅ Агент оценки знаний работает")
                    else:
                        self.warnings.append("Агент оценки знаний работает частично")
                except Exception as e:
                    self.warnings.append(f"Ошибка агента оценки: {e}")
                
                return True
            else:
                self.warnings.append("Система агентов недоступна (LLM недоступен)")
                return False
                
        except ImportError:
            self.warnings.append("Модули агентов недоступны")
            return False
        except Exception as e:
            self.warnings.append(f"Ошибка системы агентов: {e}")
            return False
    
    async def check_knowledge_base(self) -> bool:
        """Проверка базы знаний."""
        try:
            from app.config import KNOWLEDGE_DIR
            
            knowledge_file = KNOWLEDGE_DIR / "jsonl" / "risk_knowledge.jsonl"
            
            if not knowledge_file.exists():
                # Создаем базовую базу знаний
                self.create_basic_knowledge_base(knowledge_file)
            
            # Проверяем содержимое
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            if len(lines) < 5:
                self.warnings.append("База знаний содержит мало записей")
                return False
            
            # Проверяем формат
            try:
                for i, line in enumerate(lines[:3]):
                    json.loads(line)
                self.logger.info(f"✅ База знаний содержит {len(lines)} записей")
                return True
            except json.JSONDecodeError:
                self.errors.append("Некорректный формат базы знаний")
                return False
                
        except Exception as e:
            self.errors.append(f"Ошибка базы знаний: {e}")
            return False
    
    def create_basic_knowledge_base(self, knowledge_file: Path):
        """Создание базовой базы знаний."""
        knowledge_items = [
            {
                "prompt": "Что такое риск нарушения непрерывности деятельности?",
                "response": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций, в результате воздействия угроз непрерывности.",
                "metadata": {
                    "topic": "риск_нарушения_непрерывности",
                    "difficulty": "базовый",
                    "keywords": ["непрерывность", "кредитная организация", "операционная устойчивость"]
                }
            },
            {
                "prompt": "Что такое угроза непрерывности?",
                "response": "Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы, распространения заболевания, представляющего опасность для окружающих, стихийного или иного бедствия.",
                "metadata": {
                    "topic": "риск_нарушения_непрерывности",
                    "difficulty": "базовый",
                    "keywords": ["угроза непрерывности", "чрезвычайная ситуация", "авария"]
                }
            }
        ]
        
        knowledge_file.parent.mkdir(parents=True, exist_ok=True)
        with open(knowledge_file, 'w', encoding='utf-8') as f:
            for item in knowledge_items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        self.logger.info(f"✅ Создана базовая база знаний: {knowledge_file}")
    
    async def check_question_generator(self) -> bool:
        """Проверка генератора вопросов."""
        try:
            from app.learning.question_generator import question_generator
            
            # Тестируем создание профиля пользователя
            user_profile = await question_generator.generate_user_profile(1)
            self.logger.info(f"✅ Создан профиль пользователя (уровень: {user_profile.knowledge_level:.2f})")
            
            # Тестируем генерацию вопросов
            questions = await question_generator.generate_adaptive_questions(
                topic="риск_нарушения_непрерывности",
                lesson_id=1,
                user_profile=user_profile,
                num_questions=2
            )
            
            if questions:
                self.logger.info(f"✅ Сгенерировано {len(questions)} тестовых вопросов")
                return True
            else:
                self.warnings.append("Не удалось сгенерировать тестовые вопросы")
                return False
                
        except ImportError:
            self.warnings.append("Модуль генератора вопросов недоступен")
            return False
        except Exception as e:
            self.warnings.append(f"Ошибка генератора вопросов: {e}")
            return False
    
    async def check_system_integration(self) -> bool:
        """Проверка интеграции систем."""
        try:
            from app.core.enhanced_integration import enhanced_learning_system, initialize_enhanced_system
            
            # Инициализируем интегрированную систему
            integration_success = await initialize_enhanced_system()
            
            if integration_success:
                self.logger.info("✅ Интеграция систем успешна")
                return True
            else:
                self.warnings.append("Интеграция систем работает частично")
                return False
                
        except ImportError:
            self.warnings.append("Модуль интеграции недоступен")
            return False
        except Exception as e:
            self.warnings.append(f"Ошибка интеграции: {e}")
            return False
    
    async def check_analytics_system(self) -> bool:
        """Проверка системы аналитики."""
        try:
            from app.core.enhanced_integration import get_enhanced_learning_analytics
            
            # Тестируем получение аналитики
            analytics = await get_enhanced_learning_analytics(1)
            
            if analytics and "overall_stats" in analytics:
                self.logger.info("✅ Система аналитики работает")
                return True
            else:
                self.warnings.append("Система аналитики работает частично")
                return False
                
        except Exception as e:
            self.warnings.append(f"Ошибка системы аналитики: {e}")
            return False
    
    def generate_final_report(self) -> bool:
        """Генерация финального отчета."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("📊 ФИНАЛЬНЫЙ ОТЧЕТ ИНИЦИАЛИЗАЦИИ СИСТЕМЫ")
        self.logger.info("=" * 80)
        
        # Подсчет результатов
        total_checks = len(self.checks_results)
        successful_checks = sum(self.checks_results.values())
        success_rate = successful_checks / total_checks if total_checks > 0 else 0
        
        self.logger.info(f"Общий результат: {successful_checks}/{total_checks} проверок пройдено ({success_rate:.1%})")
        
        # Детальные результаты
        self.logger.info("\nДетальные результаты:")
        for check_name, result in self.checks_results.items():
            status = "✅ УСПЕШНО" if result else "❌ ОШИБКА"
            self.logger.info(f"  {check_name}: {status}")
        
        # Предупреждения
        if self.warnings:
            self.logger.info(f"\n⚠️ Предупреждения ({len(self.warnings)}):")
            for warning in self.warnings:
                self.logger.warning(f"  - {warning}")
        
        # Ошибки
        if self.errors:
            self.logger.info(f"\n❌ Ошибки ({len(self.errors)}):")
            for error in self.errors:
                self.logger.error(f"  - {error}")
        
        # Рекомендации
        self.logger.info("\n" + "=" * 80)
        self.logger.info("🎯 РЕКОМЕНДАЦИИ")
        self.logger.info("=" * 80)
        
        if success_rate >= 0.8:
            self.logger.info("🎉 СИСТЕМА ГОТОВА К РАБОТЕ!")
            self.logger.info("✅ Все основные компоненты функционируют")
            self.logger.info("🚀 Запуск бота: python -m app.main")
            
            if self.warnings:
                self.logger.info("\n📝 Дополнительные улучшения:")
                if "LM Studio" in [w for w in self.warnings if "LM Studio" in w]:
                    self.logger.info("  - Установите и настройте LM Studio для полной функциональности AI")
                if "RAG" in [w for w in self.warnings if "RAG" in w]:
                    self.logger.info("  - Установите sentence-transformers для улучшенного поиска")
                if "агент" in [w for w in self.warnings if "агент" in w]:
                    self.logger.info("  - Настройте систему агентов для адаптивного обучения")
            
        else:
            self.logger.info("❌ СИСТЕМА НЕ ГОТОВА")
            self.logger.info("Необходимо устранить критические ошибки перед запуском:")
            
            for error in self.errors[:5]:  # Показываем первые 5 ошибок
                self.logger.info(f"  🔧 {error}")
        
        return success_rate >= 0.6  # Минимум 60% для базовой работоспособности

async def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description="Инициализация Enhanced AI Learning Bot")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument("--quick", "-q", action="store_true", help="Быстрая проверка (только критические компоненты)")
    parser.add_argument("--fix", "-f", action="store_true", help="Попытаться исправить найденные проблемы")
    parser.add_argument("--export-report", "-e", help="Экспорт отчета в файл")
    
    args = parser.parse_args()
    
    # Настройка логирования
    logger = setup_logging(args.verbose)
    
    try:
        # Создание инициализатора
        initializer = SystemInitializer(logger)
        
        # Запуск инициализации
        if args.quick:
            success = await initializer.run_quick_check()
        else:
            success = await initializer.run_full_initialization()
        
        # Исправление проблем, если запрошено
        if args.fix and not success:
            await initializer.attempt_fixes()
        
        # Экспорт отчета, если запрошено
        if args.export_report:
            initializer.export_report(args.export_report)
        
        # Завершение
        if success:
            logger.info("\n🎉 Инициализация завершена успешно!")
            return 0
        else:
            logger.error("\n❌ Инициализация завершена с ошибками")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ Инициализация прервана пользователем")
        return 1
    except Exception as e:
        logger.error(f"\n💥 Критическая ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return 1

# Добавляем недостающие методы в SystemInitializer
async def run_quick_check(self) -> bool:
    """Быстрая проверка критических компонентов."""
    self.logger.info("🚀 БЫСТРАЯ ПРОВЕРКА КРИТИЧЕСКИХ КОМПОНЕНТОВ")
    self.logger.info("=" * 60)
    
    # Только критические проверки
    critical_checks = [
        ("🔧 Конфигурация", self.check_configuration),
        ("📦 Зависимости", self.check_dependencies),
        ("🗄️ База данных", self.check_database),
        ("📚 База знаний", self.check_knowledge_base)
    ]
    
    for check_name, check_func in critical_checks:
        self.logger.info(f"\n{check_name}...")
        try:
            result = await check_func()
            self.checks_results[check_name] = result
            status = "✅ УСПЕШНО" if result else "❌ ОШИБКА"
            self.logger.info(f"{check_name}: {status}")
        except Exception as e:
            self.checks_results[check_name] = False
            self.errors.append(f"{check_name}: {str(e)}")
            self.logger.error(f"{check_name}: ❌ ОШИБКА - {e}")
    
    return self.generate_quick_report()

def generate_quick_report(self) -> bool:
    """Генерация быстрого отчета."""
    successful = sum(self.checks_results.values())
    total = len(self.checks_results)
    success_rate = successful / total if total > 0 else 0
    
    self.logger.info(f"\n📊 Результат быстрой проверки: {successful}/{total} ({success_rate:.1%})")
    
    if success_rate == 1.0:
        self.logger.info("✅ Все критические компоненты работают!")
        self.logger.info("🚀 Можно запускать бота: python -m app.main")
    else:
        self.logger.info("❌ Найдены критические проблемы:")
        for error in self.errors:
            self.logger.error(f"  - {error}")
    
    return success_rate >= 0.75

async def attempt_fixes(self):
    """Попытка автоматического исправления проблем."""
    self.logger.info("\n🔧 ПОПЫТКА ИСПРАВЛЕНИЯ ПРОБЛЕМ")
    self.logger.info("=" * 50)
    
    # Исправляем отсутствующие директории
    await self._fix_directories()
    
    # Исправляем базу знаний
    await self._fix_knowledge_base()
    
    # Исправляем конфигурацию
    await self._fix_configuration()
    
    self.logger.info("✅ Автоматические исправления завершены")

async def _fix_directories(self):
    """Исправление структуры директорий."""
    required_dirs = [
        "app/knowledge",
        "app/knowledge/jsonl", 
        "app/langchain",
        "logs",
        "temp",
        "cache"
    ]
    
    for dir_path in required_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✅ Создана директория: {dir_path}")
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать {dir_path}: {e}")

async def _fix_knowledge_base(self):
    """Исправление базы знаний."""
    try:
        from app.config import KNOWLEDGE_DIR
        knowledge_file = KNOWLEDGE_DIR / "jsonl" / "risk_knowledge.jsonl"
        
        if not knowledge_file.exists() or knowledge_file.stat().st_size < 100:
            self.create_basic_knowledge_base(knowledge_file)
            self.logger.info("✅ База знаний восстановлена")
    except Exception as e:
        self.logger.warning(f"⚠️ Не удалось исправить базу знаний: {e}")

async def _fix_configuration(self):
    """Исправление конфигурации."""
    try:
        # Проверяем наличие .env файла
        env_file = Path(".env")
        if not env_file.exists():
            env_example = Path(".env.example")
            if env_example.exists():
                import shutil
                shutil.copy(env_example, env_file)
                self.logger.info("✅ Создан файл .env из шаблона")
                self.logger.warning("⚠️ Не забудьте заполнить .env файл реальными значениями!")
    except Exception as e:
        self.logger.warning(f"⚠️ Не удалось исправить конфигурацию: {e}")

def export_report(self, filename: str):
    """Экспорт отчета в файл."""
    try:
        report_data = {
            "timestamp": time.time(),
            "checks_results": self.checks_results,
            "warnings": self.warnings,
            "errors": self.errors,
            "success_rate": sum(self.checks_results.values()) / len(self.checks_results) if self.checks_results else 0
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📄 Отчет экспортирован в {filename}")
        
    except Exception as e:
        self.logger.error(f"❌ Не удалось экспортировать отчет: {e}")

# Добавляем методы в класс SystemInitializer
SystemInitializer.run_quick_check = run_quick_check
SystemInitializer.generate_quick_report = generate_quick_report
SystemInitializer.attempt_fixes = attempt_fixes
SystemInitializer._fix_directories = _fix_directories
SystemInitializer._fix_knowledge_base = _fix_knowledge_base
SystemInitializer._fix_configuration = _fix_configuration
SystemInitializer.export_report = export_report

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))