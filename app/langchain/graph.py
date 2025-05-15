"""
Модуль для создания графа агентов LangGraph.
"""
from typing import Dict, Any, List, Tuple, Optional
from langgraph.graph import StateGraph, END
import json

from app.langchain.agents import (
    KnowledgeAssessmentAgent,
    QuestionGenerationAgent,
    ExplanationAgent,
    PersonalizationAgent
)
from app.learning.questions import check_answer, get_explanation

# Определение состояния графа
class LearningState:
    """Класс для представления состояния обучения."""
    
    def __init__(
        self,
        user_id: int,
        lesson_id: int,
        topic: str,
        questions: List[Dict[str, Any]] = None,
        current_question_index: int = 0,
        answers: List[Dict[str, Any]] = None,
        user_level: int = 50,
        needs_explanation: bool = False,
        explanation: str = "",
        completed: bool = False,
        success_percentage: float = 0.0
    ):
        self.user_id = user_id
        self.lesson_id = lesson_id
        self.topic = topic
        self.questions = questions or []
        self.current_question_index = current_question_index
        self.answers = answers or []
        self.user_level = user_level
        self.needs_explanation = needs_explanation
        self.explanation = explanation
        self.completed = completed
        self.success_percentage = success_percentage
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует состояние в словарь."""
        return {
            "user_id": self.user_id,
            "lesson_id": self.lesson_id,
            "topic": self.topic,
            "questions": self.questions,
            "current_question_index": self.current_question_index,
            "answers": self.answers,
            "user_level": self.user_level,
            "needs_explanation": self.needs_explanation,
            "explanation": self.explanation,
            "completed": self.completed,
            "success_percentage": self.success_percentage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LearningState':
        """Создает состояние из словаря."""
        return cls(
            user_id=data.get("user_id", 0),
            lesson_id=data.get("lesson_id", 0),
            topic=data.get("topic", ""),
            questions=data.get("questions", []),
            current_question_index=data.get("current_question_index", 0),
            answers=data.get("answers", []),
            user_level=data.get("user_level", 50),
            needs_explanation=data.get("needs_explanation", False),
            explanation=data.get("explanation", ""),
            completed=data.get("completed", False),
            success_percentage=data.get("success_percentage", 0.0)
        )

# Функции для узлов графа
def generate_questions(state: Dict[str, Any]) -> Dict[str, Any]:
    """Узел для генерации вопросов."""
    learning_state = LearningState.from_dict(state)
    
    # Если вопросы уже сгенерированы, просто возвращаем состояние
    if learning_state.questions:
        return state
    
    # Генерируем вопросы
    agent = QuestionGenerationAgent()
    questions = []
    
    # Вместо вызова RAG напрямую, используем имеющиеся вопросы из базы
    # В реальном сценарии можно было бы генерировать вопросы на лету
    from app.learning.questions import generate_questions_for_lesson
    db_questions = generate_questions_for_lesson(learning_state.lesson_id, learning_state.topic)
    
    for question in db_questions:
        questions.append({
            "id": question.id,
            "text": question.text,
            "options": json.loads(question.options),
            "correct_answer": question.correct_answer,
            "explanation": question.explanation
        })
    
    learning_state.questions = questions
    
    return learning_state.to_dict()

def process_answer(state: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    """Узел для обработки ответа пользователя."""
    learning_state = LearningState.from_dict(state)
    
    # Если нет текущего вопроса, возвращаем состояние
    if not learning_state.questions or learning_state.current_question_index >= len(learning_state.questions):
        return state
    
    # Получаем текущий вопрос
    current_question = learning_state.questions[learning_state.current_question_index]
    
    # Проверяем ответ
    is_correct = check_answer(current_question["id"], learning_state.user_id, user_answer)
    
    # Получаем объяснение
    explanation = get_explanation(current_question["id"])
    
    # Сохраняем ответ
    learning_state.answers.append({
        "question_id": current_question["id"],
        "user_answer": user_answer,
        "is_correct": is_correct,
        "explanation": explanation
    })
    
    # Оцениваем уровень знаний пользователя
    agent = KnowledgeAssessmentAgent()
    assessment = agent.assess(
        current_question["text"],
        user_answer,
        current_question["correct_answer"]
    )
    
    # Обновляем уровень пользователя (среднее между текущим и новой оценкой)
    learning_state.user_level = (learning_state.user_level + assessment["score"]) // 2
    
    # Определяем, нужно ли дополнительное объяснение
    learning_state.needs_explanation = not is_correct
    
    # Переходим к следующему вопросу
    learning_state.current_question_index += 1
    
    # Проверяем, завершен ли урок
    if learning_state.current_question_index >= len(learning_state.questions):
        # Вычисляем процент успешности
        correct_answers = sum(1 for answer in learning_state.answers if answer["is_correct"])
        learning_state.success_percentage = (correct_answers / len(learning_state.questions)) * 100.0
        learning_state.completed = True
    
    return learning_state.to_dict()

def generate_explanation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Узел для генерации дополнительного объяснения."""
    learning_state = LearningState.from_dict(state)
    
    # Если не требуется объяснение, просто возвращаем состояние
    if not learning_state.needs_explanation:
        return state
    
    # Получаем текущий вопрос (предыдущий, так как индекс уже инкрементирован)
    question_index = learning_state.current_question_index - 1
    if question_index < 0 or question_index >= len(learning_state.questions):
        learning_state.needs_explanation = False
        return learning_state.to_dict()
    
    current_question = learning_state.questions[question_index]
    
    # Генерируем объяснение
    agent = ExplanationAgent()
    misconceptions = []
    
    # Выявляем заблуждения из ответов пользователя
    for answer in learning_state.answers:
        if not answer["is_correct"]:
            misconceptions.append(f"Неверный ответ на вопрос о {current_question['text']}")
    
    # Получаем объяснение
    concept = current_question["text"].lower()
    explanation = agent.explain(
        learning_state.topic,
        concept,
        learning_state.user_level,
        misconceptions
    )
    
    learning_state.explanation = explanation
    learning_state.needs_explanation = False
    
    return learning_state.to_dict()

def check_completion(state: Dict[str, Any]) -> str:
    """Узел для проверки завершения урока."""
    learning_state = LearningState.from_dict(state)
    
    # Если урок завершен, переходим к концу графа
    if learning_state.completed:
        return "completed"
    
    # Если нужно дополнительное объяснение, переходим к генерации объяснения
    if learning_state.needs_explanation:
        return "needs_explanation"
    
    # Если еще есть вопросы, переходим к следующему вопросу
    if learning_state.current_question_index < len(learning_state.questions):
        return "next_question"
    
    # По умолчанию, урок завершен
    return "completed"

# Создание графа
def create_learning_graph() -> StateGraph:
    """Создает граф обучения."""
    graph = StateGraph(LearningState)
    
    # Добавляем узлы
    graph.add_node("generate_questions", generate_questions)
    graph.add_node("process_answer", process_answer)
    graph.add_node("generate_explanation", generate_explanation)
    
    # Определяем переходы
    graph.set_entry_point("generate_questions")
    
    graph.add_conditional_edges(
        "generate_questions",
        check_completion,
        {
            "next_question": "process_answer",
            "needs_explanation": "generate_explanation",
            "completed": END
        }
    )
    
    graph.add_conditional_edges(
        "process_answer",
        check_completion,
        {
            "next_question": "process_answer",
            "needs_explanation": "generate_explanation",
            "completed": END
        }
    )
    
    graph.add_conditional_edges(
        "generate_explanation",
        check_completion,
        {
            "next_question": "process_answer",
            "needs_explanation": "generate_explanation",
            "completed": END
        }
    )
    
    return graph

# Функция для создания и запуска графа
def create_learning_session(user_id: int, lesson_id: int, topic: str) -> Any:
    """Создает сессию обучения для пользователя."""
    # Создаем граф
    graph = create_learning_graph()
    
    # Компилируем граф
    app = graph.compile()
    
    # Создаем начальное состояние
    initial_state = LearningState(
        user_id=user_id,
        lesson_id=lesson_id,
        topic=topic
    ).to_dict()
    
    # Запускаем граф
    config = {"recursion_limit": 25}  # Лимит рекурсии для безопасности
    result = app.invoke(initial_state, config)
    
    return result