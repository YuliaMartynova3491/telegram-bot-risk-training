"""
Модуль для определения агентов LangGraph.
"""
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage
import json

from app.config import LLM_MODEL_PATH
from app.langchain.prompts import (
    KNOWLEDGE_ASSESSMENT_PROMPT,
    QUESTION_GENERATION_PROMPT,
    EXPLANATION_PROMPT,
    QUERY_RESPONSE_PROMPT,
    PERSONALIZATION_PROMPT
)

# Инициализация LLM
def init_llm(temperature: float = 0.7):
    """Инициализирует модель для работы агентов."""
    llm = ChatOpenAI(
        base_url=LLM_MODEL_PATH,
        api_key="not-needed",
        model_name="local-model",
        temperature=temperature,
        max_tokens=2048
    )
    return llm

class KnowledgeAssessmentAgent:
    """Агент для оценки знаний пользователя."""
    
    def __init__(self):
        self.llm = init_llm(temperature=0.3)  # Низкая температура для более стабильных оценок
    
    def assess(self, question: str, user_answer: str, correct_answer: str) -> Dict[str, Any]:
        """Оценивает ответ пользователя на вопрос."""
        prompt = KNOWLEDGE_ASSESSMENT_PROMPT.format(
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Извлекаем оценку и объяснение
        score = 0
        explanation = ""
        
        for line in content.split("\n"):
            if line.startswith("Оценка:"):
                try:
                    score = int(line.replace("Оценка:", "").strip())
                except ValueError:
                    score = 0
            elif line.startswith("Объяснение:"):
                explanation = line.replace("Объяснение:", "").strip()
        
        return {
            "score": score,
            "explanation": explanation
        }


class QuestionGenerationAgent:
    """Агент для генерации вопросов."""
    
    def __init__(self):
        self.llm = init_llm(temperature=0.7)  # Средняя температура для разнообразия вопросов
    
    def generate_question(
        self, 
        topic: str, 
        difficulty: str,
        previous_questions: List[str], 
        user_level: int
    ) -> Dict[str, Any]:
        """Генерирует вопрос на основе темы и уровня пользователя."""
        # Форматируем предыдущие вопросы
        previous_questions_text = "\n".join([f"- {q}" for q in previous_questions])
        
        prompt = QUESTION_GENERATION_PROMPT.format(
            topic=topic,
            difficulty=difficulty,
            previous_questions=previous_questions_text,
            user_level=user_level
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Извлекаем JSON из ответа
        try:
            # Ищем JSON в тексте
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end]
                question_data = json.loads(json_str)
                return question_data
            else:
                return {
                    "question": "Ошибка генерации вопроса",
                    "options": ["Ошибка 1", "Ошибка 2", "Ошибка 3", "Ошибка 4"],
                    "correct_answer": "A",
                    "explanation": "Произошла ошибка при генерации вопроса."
                }
        except json.JSONDecodeError:
            return {
                "question": "Ошибка генерации вопроса",
                "options": ["Ошибка 1", "Ошибка 2", "Ошибка 3", "Ошибка 4"],
                "correct_answer": "A",
                "explanation": "Произошла ошибка при генерации вопроса."
            }


class ExplanationAgent:
    """Агент для объяснения концепций."""
    
    def __init__(self):
        self.llm = init_llm(temperature=0.5)  # Средняя температура для баланса точности и творчества
    
    def explain(
        self, 
        topic: str, 
        concept: str, 
        user_level: int, 
        misconceptions: List[str]
    ) -> str:
        """Объясняет концепцию с учетом уровня пользователя и его заблуждений."""
        # Форматируем заблуждения пользователя
        misconceptions_text = "\n".join([f"- {m}" for m in misconceptions])
        
        prompt = EXPLANATION_PROMPT.format(
            topic=topic,
            concept=concept,
            user_level=user_level,
            misconceptions=misconceptions_text
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content


class QueryResponseAgent:
    """Агент для ответа на вопросы пользователя."""
    
    def __init__(self):
        self.llm = init_llm(temperature=0.5)  # Средняя температура для баланса точности и естественности
    
    def answer_query(self, query: str, context: str) -> str:
        """Отвечает на вопрос пользователя с учетом контекста."""
        prompt = QUERY_RESPONSE_PROMPT.format(
            query=query,
            context=context
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content


class PersonalizationAgent:
    """Агент для персонализации обучения."""
    
    def __init__(self):
        self.llm = init_llm(temperature=0.4)  # Ниже средней температуры для стабильности рекомендаций
    
    def personalize(
        self, 
        user_progress: Dict[str, Any], 
        user_answers: List[Dict[str, Any]], 
        lesson_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Персонализирует обучение на основе прогресса и ответов пользователя."""
        # Форматируем данные для промпта
        user_progress_text = json.dumps(user_progress, ensure_ascii=False, indent=2)
        user_answers_text = json.dumps(user_answers, ensure_ascii=False, indent=2)
        lesson_structure_text = json.dumps(lesson_structure, ensure_ascii=False, indent=2)
        
        prompt = PERSONALIZATION_PROMPT.format(
            user_progress=user_progress_text,
            user_answers=user_answers_text,
            lesson_structure=lesson_structure_text
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Парсим ответ
        result = {
            "knowledge_gaps": [],
            "strengths": [],
            "recommended_difficulty": 2,  # По умолчанию средний уровень
            "learning_recommendations": ""
        }
        
        for line in content.split("\n"):
            if line.startswith("Пробелы в знаниях:"):
                result["knowledge_gaps"] = [
                    gap.strip() for gap in line.replace("Пробелы в знаниях:", "").strip().split(",")
                ]
            elif line.startswith("Сильные стороны:"):
                result["strengths"] = [
                    strength.strip() for strength in line.replace("Сильные стороны:", "").strip().split(",")
                ]
            elif line.startswith("Рекомендуемый уровень сложности:"):
                try:
                    result["recommended_difficulty"] = int(
                        line.replace("Рекомендуемый уровень сложности:", "").strip()
                    )
                except ValueError:
                    pass
            elif line.startswith("Рекомендации по обучению:"):
                result["learning_recommendations"] = line.replace("Рекомендации по обучению:", "").strip()
        
        return result