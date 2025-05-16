import urllib.request
import urllib.error
import json
import sys

print(f"Python version: {sys.version}")

# Тест подключения к Telegram API
TOKEN = "7270707347:AAFqbP-c8tGX-fIe2ZlB1NZfwiANLjcYOHM"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

print(f"\nПроверка подключения к Telegram API...")

try:
    print(f"Отправка запроса GET к {API_URL}/getMe")
    
    with urllib.request.urlopen(f"{API_URL}/getMe", timeout=10) as response:
        status_code = response.getcode()
        headers = dict(response.getheaders())
        
        print(f"Код ответа: {status_code}")
        print(f"Заголовки ответа: {json.dumps(headers, indent=2)}")
        
        if status_code == 200:
            data = response.read().decode("utf-8")
            result = json.loads(data)
            print(f"Содержимое ответа: {json.dumps(result, indent=2)}")
            
            if result.get("ok"):
                print(f"\nУспешное подключение к боту @{result['result']['username']}")
            else:
                print(f"\nОшибка в ответе API: {result}")
        else:
            print(f"\nНеудачный код ответа: {status_code}")

except urllib.error.URLError as e:
    print(f"Ошибка URL: {e}")
except urllib.error.HTTPError as e:
    print(f"HTTP ошибка: {e} ({e.code})")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")

# Тест подключения к другим сервисам для сравнения
print("\nПроверка подключения к Google...")
try:
    with urllib.request.urlopen("https://www.google.com", timeout=5) as response:
        print(f"Код ответа Google: {response.getcode()}")
except Exception as e:
    print(f"Ошибка при подключении к Google: {e}")

print("\nПроверка подключения к PyPI...")
try:
    with urllib.request.urlopen("https://pypi.org", timeout=5) as response:
        print(f"Код ответа PyPI: {response.getcode()}")
except Exception as e:
    print(f"Ошибка при подключении к PyPI: {e}")
