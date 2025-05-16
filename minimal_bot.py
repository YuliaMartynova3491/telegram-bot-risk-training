import requests
import time
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "7270707347:AAFqbP-c8tGX-fIe2ZlB1NZfwiANLjcYOHM"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def get_updates(offset=None, timeout=30):
    """Получает обновления от Telegram API"""
    params = {
        "timeout": timeout
    }
    if offset:
        params["offset"] = offset
    
    logger.info(f"Получение обновлений с параметрами: {params}")
    
    try:
        response = requests.get(f"{API_URL}/getUpdates", params=params, timeout=timeout+5)
        return response.json()
    except requests.exceptions.ReadTimeout:
        logger.info("Таймаут получения обновлений (это нормально)")
        return {"ok": True, "result": []}
    except Exception as e:
        logger.error(f"Ошибка при получении обновлений: {e}")
        return None

def send_message(chat_id, text):
    """Отправляет сообщение пользователю"""
    params = {
        "chat_id": chat_id,
        "text": text
    }
    
    try:
        response = requests.post(f"{API_URL}/sendMessage", params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return None

def main():
    """Основная функция бота"""
    logger.info("Запуск минимального бота")
    
    # Проверяем подключение
    try:
        response = requests.get(f"{API_URL}/getMe")
        bot_info = response.json()
        
        if bot_info["ok"]:
            logger.info(f"Бот @{bot_info['result']['username']} успешно подключен")
        else:
            logger.error(f"Ошибка подключения: {bot_info}")
            return
    except Exception as e:
        logger.error(f"Не удалось подключиться к Telegram API: {e}")
        return
    
    # Основной цикл бота
    offset = None
    while True:
        try:
            # Получаем обновления
            updates = get_updates(offset)
            
            if updates and updates["ok"]:
                # Обрабатываем полученные сообщения
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    # Проверяем, есть ли в обновлении сообщение
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]
                        username = update["message"]["from"].get("first_name", "пользователь")
                        
                        logger.info(f"Получено сообщение от {username}: {text}")
                        
                        # Отвечаем на сообщение
                        if text.startswith("/start"):
                            send_message(chat_id, f"Привет, {username}! Я простой тестовый бот.")
                        else:
                            send_message(chat_id, f"Вы написали: {text}")
            else:
                logger.warning(f"Не удалось получить обновления: {updates}")
                time.sleep(5)  # небольшая пауза перед следующей попыткой
        
        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем")
            break
        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
            time.sleep(5)  # пауза перед повторной попыткой

if __name__ == "__main__":
    main()
