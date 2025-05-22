"""
Инициализация модуля базы данных.
"""

# Импортируем модели
from .models import (
    Base,
    User,
    Lesson,
    Question,
    UserProgress,
    UserAnswer,
    init_db,
    get_db,
    close_db,
    test_connection,
    engine,
    SessionLocal
)

# Импортируем операции
from .operations import (
    get_or_create_user,
    get_user_progress,
    update_user_progress,
    save_user_answer,
    get_all_lessons,
    get_lesson_by_id,
    get_lesson,
    get_course,
    get_questions_by_lesson,
    get_question_by_id,
    get_user_statistics,
    create_default_lessons,
    add_question_to_lesson,
    get_user_by_telegram_id,
    get_user_answers_for_lesson
)

# Алиасы для совместимости
create_user = get_or_create_user  # Алиас для старых импортов
create_user_progress = update_user_progress  # Алиас
get_or_create_user_progress = update_user_progress  # Алиас
create_user_answer = save_user_answer  # Алиас

# Функции создания объектов для совместимости
def create_course():
    """Заглушка для создания курса (используйте create_default_lessons)."""
    pass

def create_lesson(db, **kwargs):
    """Создает урок."""
    lesson = Lesson(**kwargs)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson

def create_question(db, **kwargs):
    """Создает вопрос."""
    question = Question(**kwargs)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question

# Экспортируемые элементы
__all__ = [
    # Модели
    'Base',
    'User',
    'Lesson',
    'Question',
    'UserProgress',
    'UserAnswer',
    
    # Функции работы с БД
    'init_db',
    'get_db',
    'close_db',
    'test_connection',
    'engine',
    'SessionLocal',
    
    # Операции с пользователями
    'get_or_create_user',
    'create_user',  # алиас
    'get_user_by_telegram_id',
    'get_user_statistics',
    
    # Операции с прогрессом
    'get_user_progress',
    'update_user_progress',
    'create_user_progress',  # алиас
    'get_or_create_user_progress',  # алиас
    
    # Операции с ответами
    'save_user_answer',
    'create_user_answer',  # алиас
    'get_user_answers_for_lesson',
    
    # Операции с уроками
    'get_all_lessons',
    'get_lesson_by_id',
    'get_lesson',
    'get_course',
    'create_default_lessons',
    'create_lesson',
    'create_course',
    
    # Операции с вопросами
    'get_questions_by_lesson',
    'get_question_by_id',
    'add_question_to_lesson',
    'create_question'
]