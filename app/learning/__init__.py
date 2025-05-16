"""
Модуль для работы с учебными материалами.

Этот модуль содержит компоненты для работы с курсами, уроками и вопросами:
- courses.py: Описание курсов и тем
- lessons.py: Описание уроков
- questions.py: Генерация и проверка вопросов
"""

from app.learning.courses import (
    COURSES,
    init_courses,
    get_course_progress  # Добавляем функцию для расчета прогресса курса
)

from app.learning.lessons import (
    LESSONS,
    init_lessons
)

from app.learning.questions import (
    generate_questions_for_lesson,
    get_options_for_question,
    check_answer,
    get_explanation,
    check_lesson_completion,
    get_correct_answers_count
)

__all__ = [
    # Курсы
    'COURSES',
    'init_courses',
    'get_course_progress',  # Добавляем в экспорт
    
    # Уроки
    'LESSONS',
    'init_lessons',
    
    # Вопросы
    'generate_questions_for_lesson',
    'get_options_for_question',
    'check_answer',
    'get_explanation',
    'check_lesson_completion',
    'get_correct_answers_count'
]