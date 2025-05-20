"""
Модуль для работы с RAG (упрощенная версия для локального тестирования).
Используется для генерации вопросов на основе базы знаний без использования LLM.
"""
import json
import random
import os
from typing import List, Dict, Any

from app.config import RISK_KNOWLEDGE_PATH, KNOWLEDGE_DIR

# Создаем директорию для базы знаний, если она не существует
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

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