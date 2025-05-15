"""
Операции с базой данных.
Функции для взаимодействия с моделями данных.
"""
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.database.models import User, Course, Lesson, Question, UserProgress, UserAnswer

# Операции с пользователями

def get_user_by_telegram_id(db: Session, telegram_id: int):
    """Получает пользователя по Telegram ID."""
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def create_user(db: Session, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Создает нового пользователя."""
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_or_create_user(db: Session, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Получает существующего пользователя или создает нового."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = create_user(db, telegram_id, username, first_name, last_name)
    return user

def update_user_activity(db: Session, user_id: int):
    """Обновляет время последней активности пользователя."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.last_activity = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user

# Операции с курсами

def get_all_courses(db: Session):
    """Получает все темы обучения."""
    return db.query(Course).order_by(Course.order).all()

def get_course(db: Session, course_id: int):
    """Получает тему обучения по ID."""
    return db.query(Course).filter(Course.id == course_id).first()

def create_course(db: Session, name: str, description: str, order: int):
    """Создает новую тему обучения."""
    course = Course(
        name=name,
        description=description,
        order=order
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

# Операции с уроками

def get_lessons_by_course(db: Session, course_id: int):
    """Получает все уроки темы."""
    return db.query(Lesson).filter(Lesson.course_id == course_id).order_by(Lesson.order).all()

def get_lesson(db: Session, lesson_id: int):
    """Получает урок по ID."""
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()

def create_lesson(db: Session, course_id: int, title: str, content: str, order: int):
    """Создает новый урок."""
    lesson = Lesson(
        course_id=course_id,
        title=title,
        content=content,
        order=order
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson

def get_next_lesson(db: Session, current_lesson_id: int):
    """Получает следующий урок после текущего."""
    current_lesson = get_lesson(db, current_lesson_id)
    if not current_lesson:
        return None
    
    # Получаем следующий урок в той же теме
    next_lesson = db.query(Lesson).filter(
        Lesson.course_id == current_lesson.course_id,
        Lesson.order > current_lesson.order
    ).order_by(Lesson.order).first()
    
    if not next_lesson:
        # Если нет следующего урока в текущей теме, ищем первый урок следующей темы
        next_course = db.query(Course).filter(
            Course.order > db.query(Course).filter(Course.id == current_lesson.course_id).first().order
        ).order_by(Course.order).first()
        
        if next_course:
            next_lesson = db.query(Lesson).filter(
                Lesson.course_id == next_course.id
            ).order_by(Lesson.order).first()
    
    return next_lesson

# Операции с вопросами

def get_questions_by_lesson(db: Session, lesson_id: int):
    """Получает все вопросы урока."""
    return db.query(Question).filter(Question.lesson_id == lesson_id).all()

def create_question(db: Session, lesson_id: int, text: str, options: list, correct_answer: str, explanation: str = None):
    """Создает новый вопрос."""
    options_json = json.dumps(options, ensure_ascii=False)
    question = Question(
        lesson_id=lesson_id,
        text=text,
        options=options_json,
        correct_answer=correct_answer,
        explanation=explanation
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question

def get_question(db: Session, question_id: int):
    """Получает вопрос по ID."""
    return db.query(Question).filter(Question.id == question_id).first()

# Операции с прогрессом пользователя

def get_user_progress(db: Session, user_id: int, lesson_id: int):
    """Получает прогресс пользователя по уроку."""
    return db.query(UserProgress).filter(
        UserProgress.user_id == user_id, 
        UserProgress.lesson_id == lesson_id
    ).first()

def create_user_progress(db: Session, user_id: int, lesson_id: int):
    """Создает новую запись о прогрессе пользователя."""
    progress = UserProgress(
        user_id=user_id,
        lesson_id=lesson_id,
        is_completed=False,
        success_percentage=0.0,
        started_at=datetime.utcnow()
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress

def get_or_create_user_progress(db: Session, user_id: int, lesson_id: int):
    """Получает существующий прогресс или создает новый."""
    progress = get_user_progress(db, user_id, lesson_id)
    if not progress:
        progress = create_user_progress(db, user_id, lesson_id)
    return progress

def update_user_progress(db: Session, user_id: int, lesson_id: int, is_completed: bool, success_percentage: float):
    """Обновляет прогресс пользователя."""
    progress = get_user_progress(db, user_id, lesson_id)
    if progress:
        progress.is_completed = is_completed
        progress.success_percentage = success_percentage
        if is_completed:
            progress.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(progress)
    return progress

def get_user_lessons_progress(db: Session, user_id: int):
    """Получает прогресс по всем урокам пользователя."""
    return db.query(UserProgress).filter(UserProgress.user_id == user_id).all()

def get_course_progress(db: Session, user_id: int, course_id: int):
    """Получает прогресс пользователя по теме."""
    lessons = get_lessons_by_course(db, course_id)
    progress_list = []
    
    for lesson in lessons:
        progress = get_user_progress(db, user_id, lesson.id)
        if progress:
            progress_list.append(progress)
    
    if not progress_list:
        return 0.0
    
    completed_lessons = sum(1 for p in progress_list if p.is_completed)
    return (completed_lessons / len(lessons)) * 100.0

def get_available_lessons(db: Session, user_id: int):
    """Получает список доступных уроков для пользователя."""
    available_lessons = []
    
    # Получаем все курсы
    courses = get_all_courses(db)
    
    for course_idx, course in enumerate(courses):
        lessons = get_lessons_by_course(db, course.id)
        
        for lesson_idx, lesson in enumerate(lessons):
            progress = get_user_progress(db, user_id, lesson.id)
            
            # Первый урок первой темы всегда доступен
            if course_idx == 0 and lesson_idx == 0:
                available_lessons.append({
                    "lesson": lesson,
                    "course": course,
                    "progress": progress,
                    "is_available": True
                })
                continue
            
            # Проверяем доступность текущего урока
            is_available = False
            
            # Если это первый урок в теме (не первой)
            if lesson_idx == 0 and course_idx > 0:
                # Проверяем, завершен ли последний урок предыдущей темы
                prev_course = courses[course_idx - 1]
                prev_lessons = get_lessons_by_course(db, prev_course.id)
                
                if prev_lessons:
                    last_prev_lesson = prev_lessons[-1]
                    last_prev_progress = get_user_progress(db, user_id, last_prev_lesson.id)
                    
                    if last_prev_progress and last_prev_progress.is_completed:
                        is_available = True
            else:
                # Проверяем, завершен ли предыдущий урок в этой теме
                prev_lesson = lessons[lesson_idx - 1]
                prev_progress = get_user_progress(db, user_id, prev_lesson.id)
                
                if prev_progress and prev_progress.is_completed:
                    is_available = True
            
            available_lessons.append({
                "lesson": lesson,
                "course": course,
                "progress": progress,
                "is_available": is_available
            })
    
    return available_lessons

# Операции с ответами пользователя

def create_user_answer(db: Session, user_id: int, question_id: int, answer: str, is_correct: bool):
    """Создает новый ответ пользователя."""
    user_answer = UserAnswer(
        user_id=user_id,
        question_id=question_id,
        answer=answer,
        is_correct=is_correct
    )
    db.add(user_answer)
    db.commit()
    db.refresh(user_answer)
    return user_answer

def get_user_answers_by_lesson(db: Session, user_id: int, lesson_id: int):
    """Получает все ответы пользователя на вопросы урока."""
    lesson_questions = get_questions_by_lesson(db, lesson_id)
    question_ids = [q.id for q in lesson_questions]
    
    return db.query(UserAnswer).filter(
        UserAnswer.user_id == user_id,
        UserAnswer.question_id.in_(question_ids)
    ).all()

def calculate_lesson_success_percentage(db: Session, user_id: int, lesson_id: int):
    """Вычисляет процент успешности прохождения урока."""
    lesson_questions = get_questions_by_lesson(db, lesson_id)
    user_answers = get_user_answers_by_lesson(db, user_id, lesson_id)
    
    if not lesson_questions or not user_answers:
        return 0.0
    
    correct_answers = sum(1 for a in user_answers if a.is_correct)
    return (correct_answers / len(lesson_questions)) * 100.0