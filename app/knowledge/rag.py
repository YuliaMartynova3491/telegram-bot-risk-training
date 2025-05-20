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
        
        response = requests.post(
            f"{LLM_MODEL_PATH}/chat/completions", 
            headers=headers, 
            json=data,
            timeout=5
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
    # ИСПРАВЛЕНИЕ: Улучшенная проверка подключения к LM Studio
    if not check_lm_studio_connection():
        print("ВНИМАНИЕ: Не удалось подключиться к LM Studio. Будет использован запасной вариант генерации вопросов.")
        return None
    
    # Используем модель через LM Studio (или другой локальный LLM)
    # ИСПРАВЛЕНИЕ: Исправлен параметр base_url и добавлены дополнительные параметры для надежного подключения
    try:
        llm = ChatOpenAI(
            base_url=LLM_MODEL_PATH,
            api_key="not-needed",  # LM Studio не требует API ключа
            model_name="local-model",
            temperature=0.7,
            max_tokens=2048,
            request_timeout=30  # Увеличиваем таймаут для стабильности
        )
        # Проверяем модель простым запросом
        test_response = llm.invoke([HumanMessage(content="Тестовое сообщение")])
        return llm
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
        return []
    
    # ИСПРАВЛЕНИЕ: Проверяем доступность LLM Studio до создания векторного хранилища
    use_rag = check_lm_studio_connection()
    
    if use_rag:
        # Преобразуем базу знаний в документы
        documents = prepare_documents(knowledge_base)
        
        # Создаем векторное хранилище
        try:
            vectorstore = create_vector_store(documents)
        except Exception as e:
            print(f"Ошибка создания векторного хранилища: {e}")
            # Используем запасной вариант - случайные вопросы из базы знаний
            return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
        
        # Инициализируем LLM
        llm = init_llm()
        if not llm:
            return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
        
        # Поиск релевантных документов
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        query = f"Информация о {topic}"
        try:
            relevant_docs = retriever.get_relevant_documents(query)
        except Exception as e:
            print(f"Ошибка при поиске релевантных документов: {e}")
            return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
        
        # Если не нашли релевантных документов, используем запасной вариант
        if not relevant_docs:
            return fallback_generate_questions(knowledge_base, topic, difficulty, num_questions)
        
        # Генерация вопросов
        questions = []
        for _ in range(num_questions):
            # Выбираем случайный документ из релевантных
            random_doc = random.choice(relevant_docs)
            context = random_doc.page_content
            
            # Создаем промпт для генерации вопроса
            prompt = generate_question_prompt(context, topic, difficulty)
            
            try:
                # Генерируем вопрос
                response = llm.invoke([HumanMessage(content=prompt)])
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
            additional_questions = fallback_generate_questions(
                knowledge_base, 
                topic, 
                difficulty, 
                num_questions - len(questions)
            )
            questions.extend(additional_questions)
        
        return questions
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
    
    return questions

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