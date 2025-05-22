"""
Операции для работы с базой данных.
"""
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional, List
import logging
from datetime import datetime

# Локальные импорты для избежания циклических зависимостей
from .models import Base, User, Lesson, Question, UserProgress, UserAnswer

logger = logging.getLogger(__name__)

def get_or_create_user(db: Session, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
    """Получает существующего пользователя или создает нового."""
    try:
        # Ищем пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            # Обновляем информацию если она изменилась
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if last_name and user.last_name != last_name:
                user.last_name = last_name
            db.commit()
            return user
        
        # Создаем нового пользователя
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Создан новый пользователь: {telegram_id}")
        return user
        
    except Exception as e:
        logger.error(f"Ошибка при работе с пользователем {telegram_id}: {e}")
        db.rollback()
        raise

def update_user_activity(db: Session, user_id: int):
    """Обновляет время последней активности пользователя."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.commit()
        return user
    except Exception as e:
        logger.error(f"Ошибка при обновлении активности пользователя {user_id}: {e}")
        db.rollback()
        return None

def get_all_courses(db: Session):
    """Получает все курсы (заглушка для совместимости)."""
    # В упрощенной версии возвращаем список с одним курсом
    class Course:
        def __init__(self, id, name, description):
            self.id = id
            self.name = name
            self.description = description
    
    return [Course(1, "Риски непрерывности деятельности", "Основы управления рисками непрерывности")]

def get_course(db: Session, course_id: int):
    """Получает курс по ID (заглушка для совместимости)."""
    courses = get_all_courses(db)
    for course in courses:
        if course.id == course_id:
            return course
    return None

def get_lessons_by_course(db: Session, course_id: int) -> List[Lesson]:
    """Получает все уроки курса."""
    try:
        return db.query(Lesson).filter(Lesson.course_id == course_id).order_by(Lesson.order).all()
    except Exception as e:
        logger.error(f"Ошибка при получении уроков курса {course_id}: {e}")
        # Возвращаем все уроки, если нет поля course_id
        return db.query(Lesson).order_by(Lesson.order).all()

def get_next_lesson(db: Session, current_lesson_id: int):
    """Получает следующий урок."""
    try:
        current_lesson = get_lesson_by_id(db, current_lesson_id)
        if not current_lesson:
            return None
        
        return db.query(Lesson).filter(
            Lesson.order > current_lesson.order
        ).order_by(Lesson.order).first()
    except Exception as e:
        logger.error(f"Ошибка при получении следующего урока после {current_lesson_id}: {e}")
        return None

def get_available_lessons(db: Session, user_id: int):
    """Получает список доступных уроков для пользователя."""
    try:
        lessons = get_all_lessons(db)
        available_lessons = []
        
        for lesson in lessons:
            progress = get_user_progress(db, user_id, lesson.id)
            is_available = True  # Упрощенная логика - все уроки доступны
            
            # Создаем курс-заглушку
            class Course:
                def __init__(self):
                    self.id = 1
                    self.name = "Риски непрерывности деятельности"
            
            available_lessons.append({
                "lesson": lesson,
                "course": Course(),
                "progress": progress,
                "is_available": is_available
            })
        
        return available_lessons
    except Exception as e:
        logger.error(f"Ошибка при получении доступных уроков для пользователя {user_id}: {e}")
        return []

def get_course_progress(db: Session, user_id: int, course_id: int) -> float:
    """Получает прогресс пользователя по курсу."""
    try:
        lessons = get_lessons_by_course(db, course_id)
        if not lessons:
            return 0.0
        
        completed_lessons = 0
        for lesson in lessons:
            progress = get_user_progress(db, user_id, lesson.id)
            if progress and progress.is_completed:
                completed_lessons += 1
        
        return (completed_lessons / len(lessons)) * 100.0
    except Exception as e:
        logger.error(f"Ошибка при получении прогресса курса {course_id} для пользователя {user_id}: {e}")
        return 0.0

def get_or_create_user_progress(db: Session, user_id: int, lesson_id: int) -> UserProgress:
    """Получает существующий прогресс или создает новый."""
    try:
        progress = get_user_progress(db, user_id, lesson_id)
        if not progress:
            progress = UserProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                questions_answered=0,
                correct_answers=0,
                is_completed=False
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)
        return progress
    except Exception as e:
        logger.error(f"Ошибка при получении/создании прогресса пользователя {user_id}, урок {lesson_id}: {e}")
        db.rollback()
        raise

def calculate_lesson_success_percentage(db: Session, user_id: int, lesson_id: int) -> float:
    """Вычисляет процент успешности прохождения урока."""
    try:
        answers = get_user_answers_for_lesson(db, user_id, lesson_id)
        questions = get_questions_by_lesson(db, lesson_id)
        
        if not questions or not answers:
            return 0.0
        
        correct_count = sum(1 for answer in answers if answer.is_correct)
        return (correct_count / len(questions)) * 100.0
    except Exception as e:
        logger.error(f"Ошибка при расчете успешности урока {lesson_id} для пользователя {user_id}: {e}")
        return 0.0

def create_user_answer(db: Session, user_id: int, question_id: int, answer: str, is_correct: bool):
    """Создает новый ответ пользователя."""
    try:
        # Получаем вопрос для определения урока
        question = get_question_by_id(db, question_id)
        lesson_id = question.lesson_id if question else None
        
        user_answer = UserAnswer(
            user_id=user_id,
            question_id=question_id,
            user_answer=answer,
            is_correct=is_correct,
            lesson_id=lesson_id
        )
        db.add(user_answer)
        db.commit()
        db.refresh(user_answer)
        return user_answer
    except Exception as e:
        logger.error(f"Ошибка при создании ответа пользователя {user_id}, вопрос {question_id}: {e}")
        db.rollback()
        raise

def get_user_answers_by_lesson(db: Session, user_id: int, lesson_id: int) -> List[UserAnswer]:
    """Получает все ответы пользователя на вопросы урока."""
    try:
        return db.query(UserAnswer).filter(
            UserAnswer.user_id == user_id,
            UserAnswer.lesson_id == lesson_id
        ).all()
    except Exception as e:
        logger.error(f"Ошибка при получении ответов пользователя {user_id} для урока {lesson_id}: {e}")
        return []

def create_question(db: Session, lesson_id: int, text: str, options: str, correct_answer: str, explanation: str = None):
    """Создает новый вопрос."""
    try:
        question = Question(
            lesson_id=lesson_id,
            text=text,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation or ""
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса для урока {lesson_id}: {e}")
        db.rollback()
        raise

def create_lesson(db: Session, course_id: int, title: str, content: str, order: int):
    """Создает новый урок."""
    try:
        lesson = Lesson(
            title=title,
            content=content,
            order=order
        )
        # Добавляем course_id только если поле существует
        if hasattr(Lesson, 'course_id'):
            lesson.course_id = course_id
            
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson
    except Exception as e:
        logger.error(f"Ошибка при создании урока: {e}")
        db.rollback()
        raise

def create_course(db: Session, name: str, description: str, order: int):
    """Создает новый курс (заглушка для совместимости)."""
    # В упрощенной версии просто возвращаем объект-заглушку
    class Course:
        def __init__(self, id, name, description, order):
            self.id = id
            self.name = name
            self.description = description
            self.order = order
    
    return Course(1, name, description, order)

def get_user_progress(db: Session, user_id: int, lesson_id: int) -> Optional[UserProgress]:
    """Получает прогресс пользователя по уроку."""
    try:
        return db.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.lesson_id == lesson_id
        ).first()
    except Exception as e:
        logger.error(f"Ошибка при получении прогресса пользователя {user_id}, урок {lesson_id}: {e}")
        return None

def update_user_progress(
    db: Session,
    user_id: int,
    lesson_id: int,
    is_completed: bool = False,
    success_percentage: float = 0.0,
    questions_answered: int = 0,
    correct_answers: int = 0
) -> UserProgress:
    """Обновляет или создает прогресс пользователя."""
    try:
        # Ищем существующий прогресс
        progress = get_user_progress(db, user_id, lesson_id)
        
        if progress:
            # Обновляем существующий
            progress.questions_answered = questions_answered
            progress.correct_answers = correct_answers
            progress.is_completed = is_completed
            if hasattr(progress, 'success_percentage'):
                progress.success_percentage = success_percentage
        else:
            # Создаем новый
            progress = UserProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                questions_answered=questions_answered,
                correct_answers=correct_answers,
                is_completed=is_completed
            )
            if hasattr(progress, 'success_percentage'):
                progress.success_percentage = success_percentage
            db.add(progress)
        
        db.commit()
        db.refresh(progress)
        return progress
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении прогресса пользователя {user_id}, урок {lesson_id}: {e}")
        db.rollback()
        raise

def save_user_answer(
    db: Session,
    user_id: int,
    question_id: int,
    user_answer: str,
    is_correct: bool,
    lesson_id: int = None
) -> UserAnswer:
    """Сохраняет ответ пользователя."""
    try:
        answer = UserAnswer(
            user_id=user_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            lesson_id=lesson_id
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)
        return answer
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении ответа пользователя {user_id}, вопрос {question_id}: {e}")
        db.rollback()
        raise

def get_all_lessons(db: Session) -> List[Lesson]:
    """Получает все уроки."""
    try:
        return db.query(Lesson).order_by(Lesson.order).all()
    except Exception as e:
        logger.error(f"Ошибка при получении всех уроков: {e}")
        return []

def get_lesson_by_id(db: Session, lesson_id: int) -> Optional[Lesson]:
    """Получает урок по ID."""
    try:
        return db.query(Lesson).filter(Lesson.id == lesson_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении урока {lesson_id}: {e}")
        return None

def get_lesson(db: Session, lesson_id: int) -> Optional[Lesson]:
    """Алиас для get_lesson_by_id для совместимости."""
    return get_lesson_by_id(db, lesson_id)

def get_questions_by_lesson(db: Session, lesson_id: int) -> List[Question]:
    """Получает все вопросы урока."""
    try:
        return db.query(Question).filter(Question.lesson_id == lesson_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении вопросов урока {lesson_id}: {e}")
        return []

def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
    """Получает вопрос по ID."""
    try:
        return db.query(Question).filter(Question.id == question_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении вопроса {question_id}: {e}")
        return None

def get_question(db: Session, question_id: int) -> Optional[Question]:
    """Алиас для get_question_by_id для совместимости."""
    return get_question_by_id(db, question_id)

def get_user_statistics(db: Session, user_id: int) -> dict:
    """Получает статистику пользователя."""
    try:
        # Общая статистика по урокам
        total_lessons = db.query(Lesson).count()
        completed_lessons = db.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.is_completed == True
        ).count()
        
        # Статистика по ответам
        total_answers = db.query(UserAnswer).filter(UserAnswer.user_id == user_id).count()
        correct_answers = db.query(UserAnswer).filter(
            UserAnswer.user_id == user_id,
            UserAnswer.is_correct == True
        ).count()
        
        accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
        
        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "completion_rate": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0,
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "accuracy": accuracy
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователя {user_id}: {e}")
        return {
            "total_lessons": 0,
            "completed_lessons": 0,
            "completion_rate": 0,
            "total_answers": 0,
            "correct_answers": 0,
            "accuracy": 0
        }

def create_default_lessons(db: Session):
    """Создает уроки по умолчанию, если их нет."""
    try:
        # Проверяем, есть ли уже уроки
        existing_lessons = db.query(Lesson).count()
        if existing_lessons > 0:
            logger.info("Уроки уже существуют в базе данных")
            return
        
        # Создаем базовые уроки
        default_lessons = [
            {
                "title": "Введение в риск нарушения непрерывности деятельности",
                "content": "Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость.",
                "order": 1
            },
            {
                "title": "Угрозы непрерывности деятельности",
                "content": "Угрозы непрерывности делятся на 7 типов: техногенные, природные, геополитические, социальные, биолого-социальные, экономические.",
                "order": 2
            },
            {
                "title": "Оценка критичности процессов",
                "content": "Оценка критичности процессов - это процедура, в результате которой процессам присваивается категория критичности.",
                "order": 3
            }
        ]
        
        for lesson_data in default_lessons:
            lesson = Lesson(**lesson_data)
            db.add(lesson)
        
        db.commit()
        logger.info(f"Создано {len(default_lessons)} уроков по умолчанию")
        
    except Exception as e:
        logger.error(f"Ошибка при создании уроков по умолчанию: {e}")
        db.rollback()
        raise

def add_question_to_lesson(
    db: Session,
    lesson_id: int,
    text: str,
    options: List[str],
    correct_answer: str,
    explanation: str = "",
    difficulty: str = "средний"
) -> Question:
    """Добавляет вопрос к уроку."""
    try:
        question = Question(
            lesson_id=lesson_id,
            text=text,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation
        )
        if hasattr(question, 'difficulty'):
            question.difficulty = difficulty
        db.add(question)
        db.commit()
        db.refresh(question)
        logger.info(f"Добавлен вопрос к уроку {lesson_id}")
        return question
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении вопроса к уроку {lesson_id}: {e}")
        db.rollback()
        raise

def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    """Получает пользователя по Telegram ID."""
    try:
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
        return None

def get_user_answers_for_lesson(db: Session, user_id: int, lesson_id: int) -> List[UserAnswer]:
    """Получает все ответы пользователя для конкретного урока."""
    try:
        return db.query(UserAnswer).filter(
            UserAnswer.user_id == user_id,
            UserAnswer.lesson_id == lesson_id
        ).all()
    except Exception as e:
        logger.error(f"Ошибка при получении ответов пользователя {user_id} для урока {lesson_id}: {e}")
        return []

def get_user_lessons_progress(db: Session, user_id: int) -> List[UserProgress]:
    """Получает прогресс пользователя по всем урокам."""
    try:
        return db.query(UserProgress).filter(UserProgress.user_id == user_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении прогресса всех уроков для пользователя {user_id}: {e}")
        return []