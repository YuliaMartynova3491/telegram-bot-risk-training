"""
Модуль для работы с RAG (Retrieval-Augmented Generation).
Используется для генерации вопросов на основе базы знаний.
"""
import json
import random
import os
import requests
from typing import List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from app.config import RISK_KNOWLEDGE_PATH, LLM_MODEL_PATH, KNOWLEDGE_DIR

# Создаем директорию для базы знаний, если она не существует
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# Проверка доступности LM Studio
def check_lm_studio_connection():
    """Проверяет соединение с LM Studio."""
    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "local-model",
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 10
        }
        
        # Устанавливаем очень короткий timeout для быстрой проверки
        response = requests.post(
            f"{LLM_MODEL_PATH}/chat/completions", 
            headers=headers, 
            json=data,
            timeout=2
        )
        
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка при проверке соединения с LLM: {e}")
        return False

# Загрузка базы знаний
def load_knowledge_base(path: str = RISK_KNOWLEDGE_PATH) -> List[Dict[str, Any]]:
    """Загружает базу знаний из JSONL файла."""
    knowledge_base = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Проверяем, что строка не пустая
                    knowledge_base.append(json.loads(line))
        return knowledge_base
    except FileNotFoundError:
        print(f"Файл базы знаний не найден: {path}")
        return []
    except json.JSONDecodeError:
        print(f"Ошибка декодирования JSON в файле: {path}")
        return []

# Создание векторного хранилища для RAG
def create_vector_store(documents: List[Document]):
    """Создает векторное хранилище на основе документов."""
    # Используем модель эмбеддингов от HuggingFace
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_folder=os.path.join(os.path.dirname(KNOWLEDGE_DIR), "models")
        )
        
        # Создаем хранилище Chroma
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=os.path.join(os.path.dirname(KNOWLEDGE_DIR), "chroma_db")
        )
        
        return vectorstore
    except Exception as e:
        print(f"Ошибка при создании векторного хранилища: {e}")
        return None

# Подготовка документов для RAG
def prepare_documents(knowledge_base: List[Dict[str, Any]]) -> List[Document]:
    """Подготавливает документы для векторного хранилища."""
    documents = []
    
    for item in knowledge_base:
        # Создаем документ из вопроса и ответа
        content = f"Вопрос: {item['prompt']}\nОтвет: {item['response']}"
        metadata = item.get('metadata', {})
        metadata['question'] = item['prompt']
        
        doc = Document(
            page_content=content,
            metadata=metadata
        )
        documents.append(doc)
    
    # Разбиваем документы на чанки для лучшего поиска
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "?", "!"]
    )
    
    split_documents = text_splitter.split_documents(documents)
    return split_documents

# Инициализация LLM
def init_llm():
    """Инициализирует модель для генерации вопросов."""
    # Улучшенная проверка подключения к LM Studio с коротким таймаутом
    if not check_lm_studio_connection():
        print("ВНИМАНИЕ: Не удалось подключиться к LM Studio. Будет использован запасной вариант генерации вопросов.")
        return None
    
    # Используем модель через LM Studio (или другой локальный LLM)
    try:
        llm = ChatOpenAI(
            base_url=LLM_MODEL_PATH,
            api_key="not-needed",  # LM Studio не требует API ключа
            model_name="local-model",
            temperature=0.7,
            max_tokens=2048,
            request_timeout=30,  # Увеличиваем таймаут для стабильности
            verbose=True  # Включаем подробный вывод для отладки
        )
        # Проверяем модель простым запросом с очень коротким таймаутом
        try:
            test_response = llm.invoke(
                [HumanMessage(content="Тестовое сообщение")],
                config={"timeout": 3}  # Очень короткий таймаут для проверки
            )
            return llm
        except Exception as e:
            print(f"Тестовый запрос к LLM не выполнен: {e}")
            return None
    except Exception as e:
        print(f"Ошибка при инициализации LLM: {e}")
        return None

# Создание запроса для генерации вопросов
def generate_question_prompt(context: str, topic: str, difficulty: str) -> str:
    """Создает промпт для генерации вопросов на основе контекста."""
    return f"""На основе следующего контекста:

{context}

Создай вопрос с вариантами ответов по теме "{topic}" сложности "{difficulty}". 
Вопрос должен быть понятным, конкретным и иметь 4 варианта ответа (A, B, C, D), 
из которых только один правильный. Укажи правильный ответ и добавь объяснение, 
почему этот ответ верный.

Ответ должен быть в формате JSON:
{{
  "question": "текст вопроса",
  "options": ["вариант A", "вариант B", "вариант C", "вариант D"],
  "correct_answer": "A (или B, C, D - буква правильного ответа)",
  "explanation": "объяснение правильного ответа"
}}
"""

# Генерация вопросов на основе RAG
def generate_questions(
    topic: str, 
    difficulty: str = "средний", 
    num_questions: int = 3
) -> List[Dict[str, Any]]:
    """Генерирует вопросы на основе RAG."""
    # Загружаем базу знаний
    knowledge_base = load_knowledge_base()
    if not knowledge_base:
        print("Ошибка: база знаний пуста")
        return fallback_generate_questions([], topic, difficulty, num_questions)
    
    # Проверяем доступность LLM Studio - используем короткий таймаут
    use_rag = check_lm_studio_connection()
    
    if use_rag:
        try:
            # Преобразуем базу знаний в документы
            documents = prepare_documents(knowledge_base)
            
            # Создаем векторное хранилище
            vectorstore = create_vector_store(documents)
            if not vectorstore:
                print("Не удалось создать векторное хранилище, использую запасной вариант")
                return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
            
            # Инициализируем LLM
            llm = init_llm()
            if not llm:
                print("Не удалось инициализировать LLM, использую запасной вариант")
                return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
            
            # Поиск релевантных документов
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            query = f"Информация о {topic}"
            try:
                relevant_docs = retriever.get_relevant_documents(query)
                if not relevant_docs:
                    print("Не найдено релевантных документов, использую запасной вариант")
                    return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
            except Exception as e:
                print(f"Ошибка при поиске релевантных документов: {e}")
                return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
            
            # Генерация вопросов
            questions = []
            for _ in range(num_questions):
                try:
                    # Выбираем случайный документ из релевантных
                    random_doc = random.choice(relevant_docs)
                    context = random_doc.page_content
                    
                    # Создаем промпт для генерации вопроса
                    prompt = generate_question_prompt(context, topic, difficulty)
                    
                    # Генерируем вопрос с уменьшенным таймаутом
                    response = llm.invoke(
                        [HumanMessage(content=prompt)],
                        config={"timeout": 10}  # Ограничиваем время ожидания
                    )
                    content = response.content
                    
                    # Извлекаем JSON из ответа
                    try:
                        # Ищем JSON в тексте
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        if json_start != -1 and json_end != -1:
                            json_str = content[json_start:json_end]
                            question_data = json.loads(json_str)
                            questions.append(question_data)
                        else:
                            print("Не удалось найти JSON в ответе LLM")
                    except json.JSONDecodeError:
                        print("Ошибка декодирования JSON из ответа LLM")
                except Exception as e:
                    print(f"Ошибка при генерации вопроса: {e}")
            
            # Если не удалось сгенерировать достаточно вопросов, используем запасной вариант
            if len(questions) < num_questions:
                print(f"Сгенерировано только {len(questions)} вопросов из {num_questions}, добавляю вопросы из запасного варианта")
                additional_questions = fallback_generate_questions(
                    knowledge_base, 
                    topic, 
                    difficulty, 
                    num_questions - len(questions)
                )
                questions.extend(additional_questions)
            
            return questions
        except Exception as e:
            print(f"Общая ошибка при генерации вопросов с RAG: {e}")
            return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
    else:
        # Если LLM недоступен, используем запасной вариант
        print("LM Studio недоступна. Используем запасной вариант генерации вопросов.")
        return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)

# Запасной вариант генерации вопросов
def fallback_generate_questions(
    knowledge_base: List[Dict[str, Any]], 
    topic: str, 
    difficulty: str = "средний", 
    num_questions: int = 3
) -> List[Dict[str, Any]]:
    """Запасной вариант генерации вопросов из базы знаний."""
    # Если база знаний пуста, попробуем загрузить ее снова
    if not knowledge_base:
        knowledge_base = load_knowledge_base()
        if not knowledge_base:
            print("Ошибка: база знаний пуста даже после повторной загрузки")
            # Создаем простые заглушки вопросов
            return create_fallback_questions(num_questions)
    
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
    for _ in range(min(num_questions, len(filtered_kb))):
        if not filtered_kb:
            break
        
        # Выбираем случайный элемент из базы
        item = random.choice(filtered_kb)
        filtered_kb.remove(item)
        
        # Создаем вопрос и варианты ответов
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
    
    # Если не удалось сгенерировать достаточно вопросов, добавляем заглушки
    if len(questions) < num_questions:
        placeholder_questions = create_fallback_questions(num_questions - len(questions))
        questions.extend(placeholder_questions)
    
    return questions

# Создание заглушек вопросов при отсутствии базы знаний
def create_fallback_questions(num_questions: int) -> List[Dict[str, Any]]:
    """Создает базовые заглушки вопросов при отсутствии базы знаний."""
    placeholders = [
        {
            "question": "Что такое риск нарушения непрерывности деятельности?",
            "options": [
                "Риск нарушения способности организации поддерживать операционную устойчивость.",
                "Риск потери денежных средств.",
                "Риск изменения курса валют.",
                "Риск увольнения сотрудников."
            ],
            "correct_answer": "A",
            "explanation": "Риск нарушения непрерывности деятельности - это риск нарушения способности организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций, в результате воздействия угроз непрерывности."
        },
        {
            "question": "Что такое угроза непрерывности?",
            "options": [
                "Обстановка, сложившаяся в результате аварии или стихийного бедствия.",
                "Отключение электроэнергии в офисе.",
                "Увольнение директора организации.",
                "Снижение рейтинга организации."
            ],
            "correct_answer": "A",
            "explanation": "Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы и т.д., которые могут повлечь или повлекли за собой человеческие жертвы, ущерб здоровью людей или окружающей среде, значительные материальные потери."
        },
        {
            "question": "Как классифицируются угрозы непрерывности?",
            "options": [
                "Техногенные, природные, геополитические, социальные, биолого-социальные, экономические.",
                "Внутренние и внешние.",
                "Финансовые и нефинансовые.",
                "Локальные и глобальные."
            ],
            "correct_answer": "A",
            "explanation": "Угрозы непрерывности делятся на типы: техногенные, природные, геополитические, социальные, биолого-социальные, экономические. Каждый тип имеет свои характеристики и требует специфических мер по управлению."
        },
        {
            "question": "Что такое оценка критичности процессов?",
            "options": [
                "Процедура, в результате которой процессам присваивается категория критичности.",
                "Проверка работоспособности процессов.",
                "Оценка количества сотрудников, участвующих в процессе.",
                "Расчет затрат на поддержание процесса."
            ],
            "correct_answer": "A",
            "explanation": "Оценка критичности процессов - это процедура, в результате которой процессам присваивается категория критичности: критически важный, основной или прочий. Риск нарушения непрерывности оценивается только для критически важных процессов."
        },
        {
            "question": "Какие категории критичности процессов существуют?",
            "options": [
                "Критически важный, основной, прочий.",
                "Высокий, средний, низкий.",
                "Красный, желтый, зеленый.",
                "Приоритетный, вторичный, третичный."
            ],
            "correct_answer": "A",
            "explanation": "Существуют три категории критичности процессов: критически важный, основной и прочий. Риск нарушения непрерывности оценивается только для критически важных процессов."
        }
    ]
    
    # Возвращаем нужное количество заглушек
    return placeholders[:num_questions]

# Преобразование сгенерированных вопросов в формат для базы данных
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