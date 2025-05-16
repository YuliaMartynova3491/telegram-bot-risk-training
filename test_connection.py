import requests
import sys
import json

# Выводим версию Python и requests
print(f"Python version: {sys.version}")
print(f"Requests version: {requests.__version__}")

# Тест подключения к Telegram API
TOKEN = "7270707347:AAFqbP-c8tGX-fIe2ZlB1NZfwiANLjcYOHM"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

print(f"\nПроверка подключения к Telegram API...")

try:
    print(f"Отправка запроса GET к {API_URL}/getMe")
    response = requests.get(f"{API_URL}/getMe", timeout=10)
    
    print(f"Код ответа: {response.status_code}")
    print(f"Заголовки ответа: {json.dumps(dict(response.headers), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Содержимое ответа: {json.dumps(result, indent=2)}")
        
        if result.get("ok"):
            print(f"\nУспешное подключение к боту @{result['result']['username']}")
        else:
            print(f"\nОшибка в ответе API: {result}")
    else:
        print(f"\nНеудачный код ответа: {response.status_code}")
        print(f"Текст ответа: {response.text}")

except requests.exceptions.Timeout:
    print("Ошибка: Превышено время ожидания ответа от API")
except requests.exceptions.ConnectionError as e:
    print(f"Ошибка подключения: {e}")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")

# Тест подключения к другим сервисам для сравнения
print("\nПроверка подключения к Google...")
try:
    response = requests.get("https://www.google.com", timeout=5)
    print(f"Код ответа Google: {response.status_code}")
except Exception as e:
    print(f"Ошибка при подключении к Google: {e}")

print("\nПроверка подключения к PyPI...")
try:
    response = requests.get("https://pypi.org", timeout=5)
    print(f"Код ответа PyPI: {response.status_code}")
except Exception as e:
    print(f"Ошибка при подключении к PyPI: {e}")
