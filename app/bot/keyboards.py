"""
Модуль для создания клавиатур и меню в Telegram.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# Главное меню
def get_main_menu_keyboard():
    """Создает клавиатуру главного меню."""
    keyboard = [
        [KeyboardButton("📚 Обучение")],
        [KeyboardButton("📊 Мой прогресс"), KeyboardButton("ℹ️ Инструкция")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню обучения
def get_courses_keyboard(courses):
    """Создает инлайн-клавиатуру с темами обучения."""
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(
            f"📘 {course.name}", 
            callback_data=f"course_{course.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_lessons_keyboard(lessons, available_lessons=None):
    """Создает инлайн-клавиатуру с уроками темы."""
    keyboard = []
    
    if available_lessons is None:
        # Делаем первый урок всегда доступным, остальные заблокированы
        available_lessons = [i == 0 for i in range(len(lessons))]
    
    for lesson, is_available in zip(lessons, available_lessons):
        status_emoji = "🔓" if is_available else "🔒"
        callback_data = f"lesson_{lesson.id}" if is_available else "lesson_locked"
        
        keyboard.append([InlineKeyboardButton(
            f"{status_emoji} {lesson.title}", 
            callback_data=callback_data
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 К темам", callback_data="back_to_courses")])
    
    return InlineKeyboardMarkup(keyboard)

def get_available_lessons_keyboard(available_lessons_data):
    """Создает инлайн-клавиатуру с доступными уроками."""
    keyboard = []
    
    current_course_id = None
    
    for lesson_data in available_lessons_data:
        lesson = lesson_data["lesson"]
        course = lesson_data["course"]
        is_available = lesson_data["is_available"]
        progress = lesson_data["progress"]
        
        # Принудительно делаем первый урок первой темы всегда доступным
        if course.order == 1 and lesson.order == 1:
            is_available = True
        
        # Добавляем заголовок темы, если это первый урок темы
        if current_course_id != course.id:
            keyboard.append([InlineKeyboardButton(
                f"📘 {course.name}", 
                callback_data=f"course_info_{course.id}"
            )])
            current_course_id = course.id
        
        # Определяем эмодзи для статуса урока
        status_emoji = "✅" if progress and progress.is_completed else "🔓" if is_available else "🔒"
        
        # Определяем callback_data
        if progress and progress.is_completed:
            callback_data = f"lesson_{lesson.id}"  # Можно повторить пройденный урок
        elif is_available:
            callback_data = f"lesson_{lesson.id}"
        else:
            callback_data = "lesson_locked"
        
        keyboard.append([InlineKeyboardButton(
            f"{status_emoji} {lesson.title}", 
            callback_data=callback_data
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

# Клавиатуры для вопросов
def get_question_options_keyboard(question):
    """Создает клавиатуру с вариантами ответов на вопрос."""
    import json
    
    keyboard = []
    options = json.loads(question.options)
    
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}. {option}", 
            callback_data=f"answer_{question.id}_{chr(65+i)}"
        )])
    
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для начала теста
def get_start_test_keyboard(lesson_id):
    """Создает клавиатуру для начала тестирования."""
    keyboard = [
        [InlineKeyboardButton("✅ Начать тест", callback_data=f"start_test_{lesson_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для продолжения обучения
def get_continue_keyboard(next_lesson_id=None):
    """Создает клавиатуру для продолжения обучения."""
    keyboard = []
    
    if next_lesson_id:
        keyboard.append([InlineKeyboardButton(
            "▶️ Продолжить обучение", 
            callback_data=f"lesson_{next_lesson_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)

# Прогресс-бар
def get_progress_bar(percentage, width=10):
    """Создает текстовый прогресс-бар."""
    filled = int(width * percentage / 100)
    bar = "■" * filled + "□" * (width - filled)
    return f"{bar} {percentage:.1f}%"