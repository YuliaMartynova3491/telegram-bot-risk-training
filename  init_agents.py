#!/usr/bin/env python
"""
Скрипт для инициализации и проверки работы агентов.
Запустите этот скрипт перед запуском бота для проверки 
доступности языковой модели и инициализации базы знаний.
"""
import sys
import os
import argparse
import time
import logging
import requests
import json

print("🚀 Скрипт init_agents.py запущен!")

# Добавляем корневой каталог в путь импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agents_init.log")
    ]
)
logger = logging.getLogger(__name__)

def check_lm_studio_connection():
    """Проверяет подключение к LM Studio."""
    try:
        from app.config import LLM_MODEL_PATH
        
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "local-model",
            "messages": [{"role": "user", "content": "Привет! Это тестовое сообщение."}],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        logger.info(f"Проверка соединения с LM Studio по адресу: {LLM_MODEL_PATH}")
        
        # Пробуем запрос с большим таймаутом для первого соединения
        response = requests.post(
            f"{LLM_MODEL_PATH}/chat/completions", 
            headers=headers, 
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            logger.info(f"✅ Соединение с LM Studio установлено успешно")
            logger.info(f"Ответ модели: {content[:100]}...")
            return True
        else:
            logger.error(f"❌ Не удалось подключиться к LM Studio: статус {response.status_code}")
            if hasattr(response, 'text'):
                logger.error(f"Ответ: {response.text[:200]}...")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке соединения с LM Studio: {e}")
        return False

def initialize_knowledge_base():
    """Создает и инициализирует базу знаний для агентов."""
    try:
        logger.info("Начало создания расширенной базы знаний...")
        
        # Создаем директорию для JSONL файлов, если она не существует
        os.makedirs("app/knowledge/jsonl", exist_ok=True)
        
        # Создаем базовый JSONL файл, если он еще не существует
        basic_knowledge_file = "app/knowledge/jsonl/risk_knowledge.jsonl"
        if not os.path.exists(basic_knowledge_file):
            logger.info(f"Создание базового файла базы знаний: {basic_knowledge_file}")
            create_basic_knowledge_file(basic_knowledge_file)
        
        # Определяем путь к расширенной базе знаний
        enhanced_knowledge_file = "app/knowledge/jsonl/enhanced_risk_knowledge.jsonl"
        
        # Создаем расширенную базу знаний
        create_enhanced_knowledge_base(basic_knowledge_file, enhanced_knowledge_file)
        
        # Проверяем, что файл был создан
        if os.path.exists(enhanced_knowledge_file):
            file_size = os.path.getsize(enhanced_knowledge_file)
            logger.info(f"✅ Расширенная база знаний создана: {enhanced_knowledge_file} (размер: {file_size} байт)")
            return True
        else:
            logger.error(f"❌ Не удалось создать файл расширенной базы знаний")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при создании расширенной базы знаний: {e}")
        return False

def create_basic_knowledge_file(file_path):
    """Создает базовый файл базы знаний."""
    # Базовые записи для JSONL файла
    knowledge_items = [
        {
            "prompt": "Что такое риск нарушения непрерывности деятельности?",
            "response": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций, в результате воздействия угроз непрерывности.",
            "metadata": {
                "topic": "риск_нарушения_непрерывности",
                "difficulty": "базовый",
                "keywords": ["непрерывность", "кредитная организация", "операционная устойчивость"],
                "related_questions": ["Что такое угроза непрерывности?", "Как классифицируются угрозы непрерывности?"]
            }
        },
        {
            "prompt": "Что такое угроза непрерывности?",
            "response": "Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы, распространения заболевания, представляющего опасность для окружающих, стихийного или иного бедствия, которые могут повлечь или повлекли за собой человеческие жертвы, ущерб здоровью людей или окружающей среде, значительные материальные потери и нарушение условий жизнедеятельности людей.",
            "metadata": {
                "topic": "риск_нарушения_непрерывности",
                "difficulty": "базовый",
                "keywords": ["угроза непрерывности", "чрезвычайная ситуация", "авария", "катастрофа"],
                "related_questions": ["Что такое риск нарушения непрерывности деятельности?", "Какие типы угроз непрерывности существуют?"]
            }
        },
        {
            "prompt": "Как риск нарушения непрерывности связан с операционным риском?",
            "response": "Риск нарушения непрерывности является подвидом операционного риска и управляется по классической схеме (идентификация, оценка, реагирование, мониторинг), с некоторыми изменениями.",
            "metadata": {
                "topic": "риск_нарушения_непрерывности",
                "difficulty": "базовый",
                "keywords": ["операционный риск", "управление риском", "непрерывность деятельности"],
                "related_questions": ["Что такое операционный риск?", "Какие этапы включает управление риском нарушения непрерывности?"]
            }
        },
        {
            "prompt": "Какие типы угроз непрерывности существуют?",
            "response": "Угрозы непрерывности делятся на 7 типов: техногенные, природные, геополитические, социальные, биолого-социальные, экономические. Угрозы имеют масштаб и вероятность реализации, которые определяются экспертным путем в соответствии с Общим планом обеспечения непрерывности и восстановления деятельности (ОНиВД) и Регламентом ОНиВД.",
            "metadata": {
                "topic": "риск_нарушения_непрерывности",
                "difficulty": "средний",
                "keywords": ["угрозы непрерывности", "типы угроз", "масштаб угрозы", "вероятность реализации"],
                "related_questions": ["Что такое угроза непрерывности?", "Как оценивается масштаб и вероятность угрозы?"]
            }
        },
        {
            "prompt": "Что такое оценка критичности процессов?",
            "response": "Оценка критичности процессов - это процедура, в результате которой процессам присваивается категория критичности: критически важный, основной или прочий. Риск нарушения непрерывности оценивается только для критически важных процессов. Оценка критичности проводится по методике №5908, в рамках которой владелец процесса проверяет включение своего процесса в перечень критичных функций организации и оценивает потери в случае простоя процесса в результате чрезвычайной ситуации.",
            "metadata": {
                "topic": "оценка_критичности_процессов",
                "difficulty": "средний",
                "keywords": ["критичность процессов", "категория критичности", "критически важный процесс", "методика оценки"],
                "related_questions": ["Какие категории критичности процессов существуют?", "Как оцениваются потери при простое процесса?"]
            }
        }
    ]
    
    # Записываем базовые элементы в JSONL файл
    with open(file_path, 'w', encoding='utf-8') as file:
        for item in knowledge_items:
            file.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    logger.info(f"Создан базовый файл базы знаний с {len(knowledge_items)} элементами")

def create_enhanced_knowledge_base(source_path, target_path):
    """Создает расширенную базу знаний на основе существующей базы."""
    try:
        # Загружаем существующую базу знаний
        knowledge_items = []
        with open(source_path, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    knowledge_items.append(json.loads(line.strip()))
        
        # Создаем расширенную базу знаний
        enhanced_items = []
        
        # Обрабатываем каждый элемент из исходной базы
        for item in knowledge_items:
            # Получаем базовые данные
            prompt = item.get('prompt', '')
            response = item.get('response', '')
            metadata = item.get('metadata', {})
            
            # Создаем дополнительные метаданные
            enhanced_metadata = metadata.copy()
            
            # Добавляем уровни сложности для объяснений
            difficulty = metadata.get('difficulty', 'средний')
            
            # Создаем примеры для разных уровней сложности
            examples = {
                'basic': {
                    'explanation': response.split('.')[0] + '.',
                    'analogy': "Это как подготовка к любым неожиданностям, чтобы бизнес не останавливался",
                    'example': "Например, при сбое в работе ИТ-систем банка нужно быстро восстановить работу, чтобы клиенты не пострадали"
                },
                'intermediate': {
                    'explanation': '.'.join(response.split('.')[:2]) + '.',
                    'practical_example': "Банк создал резервный дата-центр в другом городе, чтобы в случае аварии в основном центре все критические системы продолжили работу",
                    'important_points': [s.strip() + '.' for s in response.split('.')[:3] if s.strip()]
                },
                'advanced': {
                    'explanation': response,
                    'technical_details': "Методология BCP (Business Continuity Planning) включает детальный анализ воздействия на бизнес (BIA), определение стратегий восстановления, разработку и тестирование планов, а также непрерывное обучение сотрудников и аудит готовности.",
                    'case_study': "В 2021 году крупный банк успешно отразил масштабную атаку шифровальщиков благодаря многоуровневой системе защиты и изолированным резервным копиям."
                }
            }
            
            # Создаем расширенный элемент
            enhanced_item = {
                'prompt': prompt,
                'response': response,
                'metadata': enhanced_metadata,
                'examples': examples,
                'related_concepts': []
            }
            
            enhanced_items.append(enhanced_item)
        
        # Сохраняем расширенную базу знаний
        with open(target_path, 'w', encoding='utf-8') as file:
            for item in enhanced_items:
                file.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logger.info(f"Расширенная база знаний создана: {target_path}")
        logger.info(f"Количество элементов: {len(enhanced_items)}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании расширенной базы знаний: {e}")
        return False

def check_rag_functionality():
    """Проверяет работу функций RAG."""
    try:
        logger.info("Проверка функциональности RAG...")
        
        # Создаем директорию app/knowledge, если она не существует
        os.makedirs("app/knowledge", exist_ok=True)
        
        # Создаем пустой файл __init__.py в директории, если его нет
        init_file = "app/knowledge/__init__.py"
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('"""Модуль для работы с базой знаний."""\n')
        
        # Создаем файл rag_simple.py, если его нет
        rag_simple_file = "app/knowledge/rag_simple.py"
        if not os.path.exists(rag_simple_file):
            create_rag_simple_file(rag_simple_file)
        
        # Импортируем функции
        # Используем относительный импорт для избежания проблем с путями
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app.knowledge.rag_simple import generate_questions, convert_questions_for_db
        
        # Тестируем генерацию вопросов
        questions = generate_questions(
            topic="риск_нарушения_непрерывности", 
            difficulty="средний", 
            num_questions=1
        )
        
        if questions and len(questions) > 0:
            logger.info(f"✅ Успешно сгенерирован тестовый вопрос:")
            logger.info(f"Вопрос: {questions[0]['question']}")
            logger.info(f"Правильный ответ: {questions[0]['correct_answer']}")
            
            # Тестируем конвертацию для базы данных
            db_questions = convert_questions_for_db(questions, lesson_id=1)
            
            if db_questions and len(db_questions) > 0:
                logger.info(f"✅ Успешно преобразован вопрос для базы данных")
                return True
            else:
                logger.error(f"❌ Не удалось преобразовать вопрос для базы данных")
                return False
        else:
            logger.error(f"❌ Не удалось сгенерировать тестовый вопрос")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке функциональности RAG: {e}")
        return False

def create_rag_simple_file(file_path):
    """Создает файл rag_simple.py с простой реализацией RAG."""
    code = '''"""
Модуль для работы с RAG (упрощенная версия для локального тестирования).
Используется для генерации вопросов на основе базы знаний без использования LLM.
"""
import json
import random
import os
from typing import List, Dict, Any

# Путь к базе знаний
RISK_KNOWLEDGE_PATH = "app/knowledge/jsonl/risk_knowledge.jsonl"

def load_knowledge_base(path: str = RISK_KNOWLEDGE_PATH) -> List[Dict[str, Any]]:
    """Загружает базу знаний из JSONL файла."""
    knowledge_base = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Проверяем, что строка не пустая
                    knowledge_base.append(json.loads(line.strip()))
        return knowledge_base
    except FileNotFoundError:
        print(f"Файл не найден: {path}")
        return []
    except json.JSONDecodeError:
        print(f"Ошибка декодирования JSON в файле: {path}")
        return []

def generate_questions(
    topic: str, 
    difficulty: str = "средний", 
    num_questions: int = 3
) -> List[Dict[str, Any]]:
    """Генерирует вопросы из базы знаний."""
    # Загружаем базу знаний
    knowledge_base = load_knowledge_base()
    if not knowledge_base:
        print("Ошибка: база знаний пуста")
        return []
    
    # Фильтруем базу знаний по теме и сложности
    filtered_kb = [
        item for item in knowledge_base 
        if (
            item.get('metadata', {}).get('topic', '').startswith(topic.split('_')[0]) and 
            item.get('metadata', {}).get('difficulty', '') == difficulty
        )
    ]
    
    # Если не нашли подходящих элементов, используем все элементы базы
    if not filtered_kb:
        filtered_kb = knowledge_base
    
    # Создаем вопросы
    questions = []
    selected_items = []
    
    # Выбираем случайные элементы без повторений
    if len(filtered_kb) >= num_questions:
        selected_items = random.sample(filtered_kb, num_questions)
    else:
        selected_items = filtered_kb.copy()
        remaining = [item for item in knowledge_base if item not in selected_items]
        if remaining:
            additional_items = random.sample(remaining, min(num_questions - len(selected_items), len(remaining)))
            selected_items.extend(additional_items)
    
    # Создаем вопросы на основе выбранных элементов
    for item in selected_items:
        question_text = item['prompt']
        correct_answer = item['response']
        
        # Формируем краткий ответ (первое предложение)
        short_answer = correct_answer.split('.')[0] + '.'
        
        # Генерируем неправильные варианты, используя другие ответы из базы
        other_answers = [
            kb_item['response'].split('.')[0] + '.' 
            for kb_item in knowledge_base 
            if kb_item['response'] != correct_answer
        ]
        
        # Выбираем случайные неправильные ответы
        wrong_answers = random.sample(other_answers, min(3, len(other_answers)))
        while len(wrong_answers) < 3:
            wrong_answers.append("Недостаточно информации для ответа")
        
        # Формируем варианты ответов
        options = [short_answer] + wrong_answers
        random.shuffle(options)
        
        # Определяем правильный ответ
        correct_index = options.index(short_answer)
        correct_letter = chr(65 + correct_index)  # A, B, C или D
        
        question_data = {
            "question": question_text,
            "options": options,
            "correct_answer": correct_letter,
            "explanation": correct_answer
        }
        
        questions.append(question_data)
    
    return questions

def convert_questions_for_db(questions: List[Dict[str, Any]], lesson_id: int) -> List[Dict[str, Any]]:
    """Преобразует сгенерированные вопросы в формат для сохранения в базе данных."""
    db_questions = []
    
    for question in questions:
        db_question = {
            "lesson_id": lesson_id,
            "text": question["question"],
            "options": json.dumps(question["options"], ensure_ascii=False),
            "correct_answer": question["correct_answer"],
            "explanation": question.get("explanation", "")
        }
        db_questions.append(db_question)
    
    return db_questions
'''
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code.strip())
    
    logger.info(f"Создан файл rag_simple.py для простой реализации RAG")

def initialize_langchain_integration():
    """Создает файл интеграции с LangChain."""
    # Создаем директорию app/langchain, если она не существует
    os.makedirs("app/langchain", exist_ok=True)
    
    # Создаем пустой файл __init__.py в директории, если его нет
    init_file = "app/langchain/__init__.py"
    if not os.path.exists(init_file):
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('"""Модуль для работы с LangGraph и агентами."""\n')
    
    # Создаем файл integration.py, если его нет
    integration_file = "app/langchain/integration.py"
    if not os.path.exists(integration_file):
        create_integration_file(integration_file)
        logger.info(f"Создан файл integration.py для интеграции агентов")
        return True
    else:
        logger.info(f"Файл integration.py уже существует")
        return True

def create_integration_file(file_path):
    """Создает файл integration.py с базовой интеграцией агентов."""
    code = '''"""
Модуль для интеграции LangGraph агентов с Telegram ботом.
"""
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple

from app.config import LLM_MODEL_PATH

# Настройка логирования
logger = logging.getLogger(__name__)

class AgentIntegration:
    """Класс для интеграции агентов LangGraph с Telegram ботом."""
    
    def __init__(self):
        """Инициализация интеграции агентов."""
        # Флаг доступности LLM
        self.llm_available = False
        
        # Создаем заглушки для агентов
        self.knowledge_agent = self.KnowledgeAgentStub()
        self.explanation_agent = self.ExplanationAgentStub()
        self.query_agent = self.QueryAgentStub()
    
    class KnowledgeAgentStub:
        """Заглушка для агента оценки знаний."""
        def assess(self, question, user_answer, correct_answer):
            """Оценивает ответ пользователя."""
            is_correct = user_answer.lower() in correct_answer.lower()
            return {
                "score": 100 if is_correct else 0,
                "explanation": "Ответ верный!" if is_correct else "Ответ неверный."
            }
    
    class ExplanationAgentStub:
        """Заглушка для агента объяснения."""
        def explain(self, topic, concept, user_level, misconceptions):
            """Объясняет концепцию."""
            return "Это объяснение было бы адаптировано под ваш уровень знаний, если бы LLM был доступен."
    
    class QueryAgentStub:
        """Заглушка для агента ответов на запросы."""
        def answer_query(self, query, context):
            """Отвечает на запрос."""
            return "К сожалению, я не могу дать подробный ответ на этот вопрос сейчас. Попробуйте задать более конкретный вопрос или обратитесь к материалам урока."
    
    async def assess_answer(self, question: str, user_answer: str, correct_answer: str) -> Dict[str, Any]:
        """Оценивает ответ пользователя с помощью агента оценки знаний."""
        if not self.llm_available:
            # Простая оценка без агента
            is_correct = user_answer == correct_answer
            return {
                "score": 100 if is_correct else 0,
                "explanation": "Ответ верный!" if is_correct else "Ответ неверный."
            }
        
        try:
            # Используем агента для оценки
            assessment = self.knowledge_agent.assess(question, user_answer, correct_answer)
            return assessment
        except Exception as e:
            logger.error(f"Ошибка при оценке ответа агентом: {e}")
            # Запасной вариант
            is_correct = user_answer == correct_answer
            return {
                "score": 100 if is_correct else 0,
                "explanation": "Ответ верный!" if is_correct else "Ответ неверный."
            }
    
    async def generate_adaptive_explanation(
        self, 
        topic: str, 
        concept: str, 
        user_level: int, 
        misconceptions: List[str]
    ) -> str:
        """Генерирует адаптивное объяснение с учетом уровня пользователя и его заблуждений."""
        if not self.llm_available:
            # Простое объяснение без агента
            return "К сожалению, не удалось сгенерировать детальное объяснение. Рекомендуем еще раз изучить материал урока."
        
        try:
            # Используем агента для генерации объяснения
            explanation = self.explanation_agent.explain(topic, concept, user_level, misconceptions)
            return explanation
        except Exception as e:
            logger.error(f"Ошибка при генерации объяснения агентом: {e}")
            # Запасной вариант
            return "К сожалению, не удалось сгенерировать детальное объяснение. Рекомендуем еще раз изучить материал урока."
    
    async def answer_user_query(self, query: str, context: str) -> str:
        """Отвечает на запрос пользователя с помощью агента запросов."""
        if not self.llm_available:
            # Простой ответ без агента
            return "К сожалению, не могу ответить на этот вопрос сейчас. Попробуйте задать более конкретный вопрос или обратитесь к материалам урока."
        
        try:
            # Используем агента для ответа
            answer = self.query_agent.answer_query(query, context)
            return answer
        except Exception as e:
            logger.error(f"Ошибка при ответе на запрос агентом: {e}")
            # Запасной вариант
            return "К сожалению, не могу ответить на этот вопрос сейчас. Попробуйте задать более конкретный вопрос или обратитесь к материалам урока."
    
    async def start_learning_session(self, user_id: int, lesson_id: int) -> Dict[str, Any]:
        """Запускает сессию обучения с использованием LangGraph."""
        # В режиме заглушки всегда используем стандартный поток
        return {"use_standard_flow": True}

# Создаем синглтон для интеграции агентов
agent_integration = AgentIntegration()
'''
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code.strip())

def check_requirements():
    """Проверяет необходимые зависимости."""
    try:
        logger.info("Проверка необходимых зависимостей...")
        
        # Список необходимых библиотек
        required_packages = [
            "python-telegram-bot",
            "sqlalchemy",
            "python-dotenv"
        ]
        
        # Дополнительные библиотеки для работы с агентами
        agent_packages = [
            "langchain",
            "langchain-community"
        ]
        
        missing_packages = []
        
        # Проверяем основные библиотеки
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                logger.info(f"✅ Библиотека {package} установлена")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"❌ Библиотека {package} не установлена")
        
        # Проверяем библиотеки для агентов
        for package in agent_packages:
            try:
                __import__(package.replace("-", "_"))
                logger.info(f"✅ Библиотека {package} установлена")
            except ImportError:
                logger.warning(f"⚠️ Библиотека {package} не установлена (требуется для полной функциональности агентов)")
        
        # Выводим рекомендации по установке недостающих библиотек
        if missing_packages:
            logger.error(f"❌ Отсутствуют необходимые библиотеки: {', '.join(missing_packages)}")
            logger.error(f"Установите их с помощью команды: pip install {' '.join(missing_packages)}")
            return False
        
        logger.info("✅ Все необходимые зависимости установлены")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке зависимостей: {e}")
        return False

def check_database():
    """Проверяет подключение к базе данных."""
    try:
        logger.info("Проверка подключения к базе данных...")
        
        # Импортируем функции
        from app.database.models import get_db, init_db
        
        # Инициализируем базу данных
        init_db()
        
        # Пытаемся получить соединение с базой данных
        db = get_db()
        
        if db:
            logger.info("✅ Соединение с базой данных установлено успешно")
            return True
        else:
            logger.error("❌ Не удалось подключиться к базе данных")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке подключения к базе данных: {e}")
        return False

def check_bot_token():
    """Проверяет наличие токена Telegram бота."""
    try:
        logger.info("Проверка токена Telegram бота...")
        
        # Импортируем конфигурацию
        from app.config import TELEGRAM_TOKEN
        
        if TELEGRAM_TOKEN:
            # Маскируем токен для безопасности
            masked_token = TELEGRAM_TOKEN[:4] + "*" * (len(TELEGRAM_TOKEN) - 8) + TELEGRAM_TOKEN[-4:]
            logger.info(f"✅ Токен Telegram бота найден: {masked_token}")
            return True
        else:
            logger.error("❌ Токен Telegram бота не найден")
            logger.error("Проверьте файл .env и убедитесь, что он содержит значение TELEGRAM_TOKEN")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке токена Telegram бота: {e}")
        return False

def run_checks(args):
    """Запускает все проверки и инициализацию."""
    logger.info("=" * 50)
    logger.info("Запуск проверок и инициализации агентов")
    logger.info("=" * 50)
    
    results = {}
    
    # Проверка зависимостей
    if args.check_all or args.check_deps:
        results["dependencies"] = check_requirements()
    
    # Проверка токена бота
    if args.check_all or args.check_token:
        results["token"] = check_bot_token()
    
    # Проверка базы данных
    if args.check_all or args.check_db:
        results["database"] = check_database()
    
    # Проверка подключения к LM Studio
    if args.check_all or args.check_lm_studio:
        results["lm_studio"] = check_lm_studio_connection()
    
    # Инициализация базы знаний
    if args.check_all or args.init_knowledge:
        results["knowledge_base"] = initialize_knowledge_base()
    
    # Проверка RAG
    if args.check_all or args.check_rag:
        results["rag"] = check_rag_functionality()
    
    # Инициализация интеграции с агентами
    if args.check_all or args.init_agents:
        results["integration"] = initialize_langchain_integration()
    
    # Выводим итоговый отчет
    logger.info("=" * 50)
    logger.info("Отчет о проверках и инициализации")
    logger.info("=" * 50)
    
    for name, result in results.items():
        status = "✅ УСПЕШНО" if result else "❌ ОШИБКА"
        logger.info(f"{name}: {status}")
    
    # Определяем общий результат
    all_success = all(results.values())
    
    if all_success:
        logger.info("✅ Все проверки пройдены успешно")
        logger.info("✅ Можно запускать бота с поддержкой агентов")
        logger.info("📝 Для запуска бота выполните: python -m app.main")
    else:
        logger.warning("⚠️ Не все проверки пройдены успешно")
        
        if "lm_studio" in results and not results["lm_studio"]:
            logger.warning("⚠️ LM Studio недоступен. Бот будет работать без поддержки агентов.")
            logger.warning("⚠️ Рекомендуется запустить LM Studio и выбрать модель перед запуском бота.")
        
        if "dependencies" in results and not results["dependencies"]:
            logger.error("❌ Отсутствуют необходимые зависимости. Установите их перед запуском бота.")
        
        if "token" in results and not results["token"]:
            logger.error("❌ Токен Telegram бота не найден. Проверьте файл .env.")
        
        if "database" in results and not results["database"]:
            logger.error("❌ Проблемы с базой данных. Проверьте настройки подключения.")
    
    return all_success

def main():
    """Основная функция для запуска скрипта."""
    parser = argparse.ArgumentParser(description="Инициализация и проверка агентов для Telegram бота")
    
    # Добавляем аргументы командной строки
    parser.add_argument("--check-all", action="store_true", help="Запустить все проверки и инициализацию")
    parser.add_argument("--check-deps", action="store_true", help="Проверить зависимости")
    parser.add_argument("--check-token", action="store_true", help="Проверить токен Telegram бота")
    parser.add_argument("--check-db", action="store_true", help="Проверить подключение к базе данных")
    parser.add_argument("--check-lm-studio", action="store_true", help="Проверить подключение к LM Studio")
    parser.add_argument("--check-rag", action="store_true", help="Проверить функциональность RAG")
    parser.add_argument("--init-knowledge", action="store_true", help="Инициализировать базу знаний")
    parser.add_argument("--init-agents", action="store_true", help="Инициализировать интеграцию агентов")
    
    args = parser.parse_args()
    
    # Если не указаны аргументы, по умолчанию запускаем все проверки
    if not any(vars(args).values()):
        args.check_all = True
    
    # Запускаем проверки
    success = run_checks(args)
    
    # Возвращаем код завершения
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())