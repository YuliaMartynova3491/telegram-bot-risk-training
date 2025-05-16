"""
Модуль для работы с курсами и прогрессом обучения.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.database.models import Course, Lesson, UserProgress, get_db
from app.database.operations import (
    get_lessons_by_course,
    get_user_progress,
    create_course,
    get_all_courses,
    get_user_lessons_progress
)

# Определение тем обучения
COURSES = [
    {
        "name": "Риск нарушения непрерывности",
        "description": """
Тема посвящена изучению концепции риска нарушения непрерывности деятельности.
Вы узнаете, что такое риск нарушения непрерывности, что такое угроза непрерывности,
какие типы угроз существуют и как они оцениваются.

Эта тема является основой для понимания управления рисками непрерывности в организации.
        """,
        "order": 1
    },
    {
        "name": "Оценка критичности процессов",
        "description": """
В этой теме вы изучите методики оценки критичности бизнес-процессов.
Вы узнаете, как определять категории критичности процессов, как оценивать потери
при простое процесса и какие временные интервалы используются для оценки.

Понимание оценки критичности процессов необходимо для правильного приоритизирования
мер по обеспечению непрерывности деятельности.
        """,
        "order": 2
    },
    {
        "name": "Оценка риска нарушения непрерывности",
        "description": """
Тема посвящена методикам оценки риска нарушения непрерывности деятельности.
Вы изучите, как оценивается влияние угроз на объекты окружения процесса,
как рассчитывается величина воздействия риска, что такое рейтинг риска
и какие существуют меры реагирования на риск.

Эта тема завершает цикл обучения и дает практические инструменты
для управления рисками непрерывности в вашей работе.
        """,
        "order": 3
    }
]

def init_courses() -> List[Dict[str, Any]]:
    """Инициализирует темы обучения в базе данных."""
    db = get_db()
    
    # Получаем все существующие темы
    existing_courses = get_all_courses(db)
    
    # Если тем нет, создаем их
    if not existing_courses:
        for course_data in COURSES:
            create_course(
                db,
                name=course_data["name"],
                description=course_data["description"],
                order=course_data["order"]
            )
    
    # Получаем все темы после инициализации
    return get_all_courses(db)

def get_course_progress(db: Session, user_id: int, course_id: int) -> float:
    """Получает прогресс пользователя по теме."""
    lessons = get_lessons_by_course(db, course_id)
    progress_list = []
    
    for lesson in lessons:
        progress = get_user_progress(db, user_id, lesson.id)
        if progress:
            progress_list.append(progress)
    
    if not lessons or not progress_list:
        return 0.0
    
    completed_lessons = sum(1 for p in progress_list if p.is_completed)
    return (completed_lessons / len(lessons)) * 100.0