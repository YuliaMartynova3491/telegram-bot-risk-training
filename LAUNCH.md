# Инструкция по запуску бота

## Подготовка окружения

1. **Установка и настройка LM Studio**

   - Скачайте и установите [LM Studio](https://lmstudio.ai/) с официального сайта
   - Запустите LM Studio
   - Выберите и загрузите модель (рекомендуется Mistral-7B или Llama-2)
   - Запустите модель (Settings → Server → Start Server)
   - Убедитесь, что модель доступна по адресу http://localhost:1234/v1

2. **Активация виртуального окружения**

   ```bash
   # Для macOS/Linux
   source venv/bin/activate

   # Для Windows
   venv\Scripts\activate