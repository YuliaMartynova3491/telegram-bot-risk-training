"""
Модели базы данных для Telegram бота обучения рискам.
Исправленная версия с полной структурой.
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql import func
import logging

logger = logging.getLogger(__name__)

# Создаем базовый класс
Base = declarative_base()

class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    answers = relationship("UserAnswer", back_populates="user", cascade="all, delete-orphan")

class Course(Base):
    """Модель курса (темы обучения)."""
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")

class Lesson(Base):
    """Модель урока."""
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    order = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    course = relationship("Course", back_populates="lessons")
    questions = relationship("Question", back_populates="lesson", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="lesson")

class Question(Base):
    """Модель вопроса."""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # Список вариантов ответов или JSON строка
    correct_answer = Column(String(10), nullable=False)  # A, B, C, D
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(50), default="средний")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    lesson = relationship("Lesson", back_populates="questions")
    answers = relationship("UserAnswer", back_populates="question")

class UserProgress(Base):
    """Модель прогресса пользователя по урокам."""
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    success_percentage = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")

class UserAnswer(Base):
    """Модель ответов пользователей на вопросы."""
    __tablename__ = "user_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    answer = Column(String(10), nullable=False)  # A, B, C, D
    user_answer = Column(String(10), nullable=False)  # Дублируем для совместимости
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="answers")

# Настройки базы данных
try:
    from app.config import DATABASE_URL
    DATABASE_URL_IMPORT = DATABASE_URL
except ImportError:
    # Запасной вариант если импорт не удался
    DATABASE_URL_IMPORT = os.getenv("DATABASE_URL", "sqlite:///risk_training.db")

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL_IMPORT,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL_IMPORT else {}
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _create_default_data_internal(db: Session):
    """Внутренняя функция для создания данных по умолчанию (без импорта operations)."""
    try:
        # Проверяем, есть ли уже курсы
        existing_courses = db.query(Course).count()
        if existing_courses > 0:
            logger.info("Курсы и уроки уже существуют в базе данных")
            return
        
        # Создаем базовые курсы
        default_courses = [
            {
                "name": "Риск нарушения непрерывности",
                "description": "Тема посвящена изучению концепции риска нарушения непрерывности деятельности. Вы узнаете, что такое риск нарушения непрерывности, что такое угроза непрерывности, какие типы угроз существуют и как они оцениваются.",
                "order": 1
            },
            {
                "name": "Оценка критичности процессов",
                "description": "В этой теме вы изучите методики оценки критичности бизнес-процессов. Вы узнаете, как определять категории критичности процессов, как оценивать потери при простое процесса и какие временные интервалы используются для оценки.",
                "order": 2
            },
            {
                "name": "Оценка риска нарушения непрерывности",
                "description": "Тема посвящена методикам оценки риска нарушения непрерывности деятельности. Вы изучите, как оценивается влияние угроз на объекты окружения процесса, как рассчитывается величина воздействия риска, что такое рейтинг риска и какие существуют меры реагирования на риск.",
                "order": 3
            }
        ]
        
        for course_data in default_courses:
            course = Course(**course_data)
            db.add(course)
        
        db.commit()
        logger.info(f"Создано {len(default_courses)} курсов по умолчанию")
        
        # Создаем базовые уроки для первого курса
        default_lessons = [
            {
                "course_id": 1,
                "title": "Основные понятия",
                "description": "Основные понятия рисков нарушения непрерывности",
                "content": """# Основные понятия рисков нарушения непрерывности

## Что такое риск нарушения непрерывности?

Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций, в результате воздействия угроз непрерывности.

## Что такое угроза непрерывности?

Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы, распространения заболевания, представляющего опасность для окружающих, стихийного или иного бедствия, которые могут повлечь или повлекли за собой человеческие жертвы, ущерб здоровью людей или окружающей среде, значительные материальные потери и нарушение условий жизнедеятельности людей.

## Связь с операционным риском

Риск нарушения непрерывности является подвидом операционного риска и управляется по классической схеме (идентификация, оценка, реагирование, мониторинг), с некоторыми изменениями.""",
                "order": 1
            },
            {
                "course_id": 1,
                "title": "Типы угроз непрерывности",
                "description": "Классификация и характеристика угроз",
                "content": """# Типы угроз непрерывности

## Классификация угроз

Угрозы непрерывности делятся на 7 типов:
- Техногенные
- Природные
- Геополитические
- Социальные
- Биолого-социальные
- Экономические

## Оценка угроз

Угрозы имеют масштаб и вероятность реализации. Масштаб и вероятность определяются экспертным путем, в соответствии с Общим планом обеспечения непрерывности и восстановления деятельности (ОНиВД) и Регламентом ОНиВД.

## Рейтинг угрозы

В результате определения масштаба и уровня угрозы формируется рейтинг (уровень) угрозы непрерывности, который в дальнейшем используется при расчете рейтинга риска нарушения непрерывности.""",
                "order": 2
            }
        ]
        
        for lesson_data in default_lessons:
            lesson = Lesson(**lesson_data)
            db.add(lesson)
        
        db.commit()
        logger.info(f"Создано {len(default_lessons)} уроков по умолчанию")
        
    except Exception as e:
        logger.error(f"Ошибка при создании данных по умолчанию: {e}")
        db.rollback()
        raise

def init_db():
    """Инициализирует базу данных."""
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("База данных инициализирована успешно")
        
        # Создаем данные по умолчанию
        db = SessionLocal()
        try:
            _create_default_data_internal(db)
        except Exception as e:
            logger.warning(f"Не удалось создать данные по умолчанию: {e}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

def get_db() -> Session:
    """Получает сессию базы данных."""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        logger.error(f"Ошибка при создании сессии базы данных: {e}")
        db.close()
        raise

def close_db(db: Session):
    """Закрывает сессию базы данных."""
    try:
        db.close()
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии базы данных: {e}")

# Функция для тестирования подключения
def test_connection():
    """Тестирует подключение к базе данных."""
    try:
        db = get_db()
        # Простой запрос для проверки соединения
        db.execute("SELECT 1")
        close_db(db)
        logger.info("Подключение к базе данных успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return False