"""
Модуль для работы с базой данных.

Этот модуль содержит компоненты для взаимодействия с базой данных:
- models.py: Определение моделей данных (ORM)
- operations.py: CRUD-операции для работы с моделями
"""

from app.database.models import (
    Base, 
    User, 
    Course, 
    Lesson, 
    Question, 
    UserProgress, 
    UserAnswer,
    init_db,
    get_db
)

from app.database.operations import (
    # Операции с пользователями
    get_user_by_telegram_id,
    create_user,
    get_or_create_user,
    update_user_activity,
    
    # Операции с курсами
    get_all_courses,
    get_course,
    create_course,
    
    # Операции с уроками
    get_lessons_by_course,
    get_lesson,
    create_lesson,
    get_next_lesson,
    
    # Операции с вопросами
    get_questions_by_lesson,
    create_question,
    get_question,
    
    # Операции с прогрессом пользователя
    get_user_progress,
    create_user_progress,
    get_or_create_user_progress,
    update_user_progress,
    get_user_lessons_progress,
    get_course_progress,
    get_available_lessons,
    
    # Операции с ответами пользователя
    create_user_answer,
    get_user_answers_by_lesson,
    calculate_lesson_success_percentage
)

__all__ = [
    # Модели
    'Base', 
    'User', 
    'Course', 
    'Lesson', 
    'Question', 
    'UserProgress', 
    'UserAnswer',
    'init_db',
    'get_db',
    
    # Операции с пользователями
    'get_user_by_telegram_id',
    'create_user',
    'get_or_create_user',
    'update_user_activity',
    
    # Операции с курсами
    'get_all_courses',
    'get_course',
    'create_course',
    
    # Операции с уроками
    'get_lessons_by_course',
    'get_lesson',
    'create_lesson',
    'get_next_lesson',
    
    # Операции с вопросами
    'get_questions_by_lesson',
    'create_question',
    'get_question',
    
    # Операции с прогрессом пользователя
    'get_user_progress',
    'create_user_progress',
    'get_or_create_user_progress',
    'update_user_progress',
    'get_user_lessons_progress',
    'get_course_progress',
    'get_available_lessons',
    
    # Операции с ответами пользователя
    'create_user_answer',
    'get_user_answers_by_lesson',
    'calculate_lesson_success_percentage'
]