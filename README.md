# 🤖 Telegram Learning Bot

Умный бот для обучения рискам нарушения непрерывности деятельности с интеграцией локальных LLM моделей.

## 🎯 Возможности

- 📚 **Интерактивное обучение** - структурированные уроки по темам
- 🧪 **Тестирование знаний** - вопросы с мгновенной обратной связью
- 🤖 **AI-помощник** - ответы на вопросы с помощью локальных LLM
- 📊 **Отслеживание прогресса** - персональная статистика обучения
- 🎨 **Дружелюбный интерфейс** - стикеры, эмодзи и понятная навигация

## 🏗️ Архитектура

```
telegram-learning-bot/
├── app/
│   ├── agents/          # AI агенты для обработки запросов
│   ├── bot/            # Telegram bot логика
│   ├── database/       # Модели и операции с БД
│   ├── learning/       # Учебные материалы и логика
│   └── config.py       # Конфигурация
├── data/              # Статические данные
├── requirements.txt   # Зависимости Python
└── main.py           # Точка входа
```

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/telegram-learning-bot.git
cd telegram-learning-bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка окружения

Создайте файл `.env` и добавьте ваши настройки:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
DATABASE_URL=sqlite:///./app.db
LLM_MODEL_PATH=http://localhost:1234/v1
MIN_SUCCESS_PERCENTAGE=80
```

### 4. Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен и добавьте в `.env`
3. Настройте команды бота:
   ```
   start - Начать обучение
   help - Помощь
   progress - Мой прогресс
   ```

### 5. Настройка LM Studio (опционально)

1. Скачайте [LM Studio](https://lmstudio.ai/)
2. Загрузите модель (рекомендуется Llama 3.2 3B)
3. Запустите локальный сервер на порту 1234

### 6. Запуск бота

```bash
python main.py
```

## 📚 Структура обучения

### Темы курса:

1. **Риск нарушения непрерывности**
   - Основные понятия
   - Типы угроз непрерывности

2. **Оценка критичности процессов**
   - Категории критичности
   - Оценка экономических потерь
   - Юридические последствия

3. **Оценка риска нарушения непрерывности**
   - Компоненты оценки риска
   - Расчет величины воздействия
   - Рейтинг риска и реагирование

## 🔧 Технологии

- **Python 3.8+** - Основной язык
- **python-telegram-bot** - Telegram Bot API
- **SQLAlchemy** - ORM для работы с БД
- **SQLite** - База данных
- **LM Studio** - Локальные LLM модели
- **LangGraph** - Агенты для обработки запросов

## 📝 Конфигурация

Основные настройки в `app/config.py`:

```python
# Telegram Bot
TELEGRAM_TOKEN = "your_bot_token"

# Database
DATABASE_URL = "sqlite:///./app.db"

# Learning settings
MIN_SUCCESS_PERCENTAGE = 80
QUESTIONS_PER_LESSON = 3

# LLM settings
LLM_MODEL_PATH = "http://localhost:1234/v1"
```

## 🗄️ База данных

Бот использует SQLite с следующими основными таблицами:
- `users` - Пользователи
- `courses` - Курсы обучения
- `lessons` - Уроки
- `questions` - Вопросы для тестирования
- `user_progress` - Прогресс пользователей
- `user_answers` - Ответы пользователей

## 🤖 AI Возможности

- **Адаптивные объяснения** - подстраиваются под уровень пользователя
- **Ответы на вопросы** - по материалам курса
- **Оценка знаний** - интеллектуальная проверка ответов

## 🧪 Тестирование

```bash
# Запуск тестов
python -m pytest tests/

# Проверка стиля кода
flake8 app/

# Проверка типов
mypy app/
```

## 📦 Деплой

### Docker

```bash
# Сборка образа
docker build -t telegram-learning-bot .

# Запуск контейнера
docker run -d --name learning-bot \
  -e TELEGRAM_TOKEN=your_token \
  telegram-learning-bot
```

### Heroku

```bash
# Создание приложения
heroku create your-app-name

# Настройка переменных окружения
heroku config:set TELEGRAM_TOKEN=your_token

# Деплой
git push heroku main
```

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 📞 Поддержка

- 🐛 [Сообщить об ошибке](https://github.com/yourusername/telegram-learning-bot/issues)
- 💡 [Предложить улучшение](https://github.com/yourusername/telegram-learning-bot/issues)
- 📧 [Связаться с автором](mailto:your.email@example.com)

## 🙏 Благодарности

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - за отличную библиотеку
- [LM Studio](https://lmstudio.ai/) - за простой способ запуска локальных LLM
- [SQLAlchemy](https://sqlalchemy.org/) - за мощную ORM

---

⭐ Поставьте звездочку, если проект был полезен!