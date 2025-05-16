import requests
import sys

# Токен вашего бота
TOKEN = "7270707347:AAFqbP-c8tGX-fIe2ZlB1NZfwiANLjcYOHM"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def delete_webhook():
    """Удаляет webhook бота."""
    print("Удаление webhook...")
    
    try:
        # Сначала проверим информацию о текущем webhook
        webhook_info_url = f"{API_URL}/getWebhookInfo"
        response = requests.get(webhook_info_url)
        
        if response.status_code == 200:
            info = response.json()
            print(f"Текущая информация о webhook: {info}")
            
            if info.get('ok') and 'result' in info:
                if info['result'].get('url'):
                    print(f"Обнаружен активный webhook URL: {info['result']['url']}")
                else:
                    print("Webhook не установлен.")
                    return True
        
        # Удаляем webhook
        delete_url = f"{API_URL}/deleteWebhook"
        response = requests.get(delete_url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Результат удаления webhook: {result}")
            
            if result.get('ok'):
                print("Webhook успешно удален!")
                return True
            else:
                print(f"Ошибка при удалении webhook: {result}")
                return False
        else:
            print(f"Ошибка HTTP при удалении webhook: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"Ошибка при удалении webhook: {e}")
        return False

if __name__ == "__main__":
    success = delete_webhook()
    sys.exit(0 if success else 1)
