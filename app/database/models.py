"""
Модели данных для работы с базой данных.
Здесь определены все таблицы и их связи.
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from datetime import datetime
import os

from app.config import DATABASE_URL

# Создаем базовый класс для моделей
Base = declarative_base()

class User(Base):
    """Модель пользователя."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Связь с прогрессом пользователя
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    answers = relationship("UserAnswer", back_populates="user", cascade="all, delete-orphan")


class Course(Base):
    """Модель темы обучения."""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)  # Порядковый номер темы
    
    # Связь с уроками
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")


class Lesson(Base):
    """Модель урока."""
    __tablename__ = 'lessons'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)  # Порядковый номер урока в теме
    
    # Связи
    course = relationship("Course", back_populates="lessons")
    questions = relationship("Question", back_populates="lesson", cascade="all, delete-orphan")
    user_progress = relationship("UserProgress", back_populates="lesson")


class Question(Base):
    """Модель вопроса."""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(Text, nullable=True)  # JSON-строка с вариантами ответов
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)
    
    # Связи
    lesson = relationship("Lesson", back_populates="questions")
    user_answers = relationship("UserAnswer", back_populates="question")


class UserProgress(Base):
    """Модель прогресса пользователя."""
    __tablename__ = 'user_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    is_completed = Column(Boolean, default=False)
    success_percentage = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="user_progress")


class UserAnswer(Base):
    """Модель ответа пользователя на вопрос."""
    __tablename__ = 'user_answers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    answer = Column(String(255), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="user_answers")


# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL, 
    pool_size=20,  # Увеличиваем размер пула
    max_overflow=20,  # Увеличиваем максимальное переполнение
    pool_recycle=1800,  # Пересоздание соединений каждые 30 минут
    pool_pre_ping=True  # Проверка соединения перед использованием
)

# Создаем фабрику сессий с использованием scoped_session для потокобезопасности
session_factory = sessionmaker(bind=engine, autoflush=True, autocommit=False)
SessionLocal = scoped_session(session_factory)

# Функция для инициализации базы данных
def init_db():
    """Создает все таблицы в базе данных."""
    Base.metadata.create_all(bind=engine)

# Функция для получения сессии базы данных
def get_db():
    """Возвращает сессию базы данных."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()