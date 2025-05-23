"""
Модуль для работы с LM Studio.
Обеспечивает надежное подключение и обработку ошибок.
Исправленная версия с совместимостью urllib3.
"""
import logging
import time
import requests
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class LMStudioClient:
    """Клиент для работы с LM Studio."""
    
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        """
        Инициализация клиента LM Studio.
        
        Args:
            base_url: Базовый URL LM Studio (например, http://localhost:1234/v1)
            timeout: Таймаут для запросов
            max_retries: Максимальное количество попыток
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.available_models = []
        self.current_model = None
        
        # Простая сессия без retry для избежания проблем совместимости
        self.session = requests.Session()
        
        # Проверяем доступность при инициализации
        self.is_available = self._check_connection()
        if self.is_available:
            self._load_models()
    
    def _check_connection(self) -> bool:
        """Проверяет подключение к LM Studio."""
        try:
            logger.info(f"Проверка подключения к LM Studio: {self.base_url}")
            
            # Проверяем models endpoint с коротким таймаутом
            models_url = f"{self.base_url}/models"
            response = self.session.get(models_url, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ LM Studio models endpoint доступен")
                return True
            
            logger.warning(f"❌ LM Studio недоступен (статус: {response.status_code})")
            return False
            
        except requests.exceptions.ConnectionError:
            logger.warning("❌ LM Studio недоступен (ошибка соединения)")
            return False
        except requests.exceptions.Timeout:
            logger.warning("❌ LM Studio недоступен (таймаут)")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке LM Studio: {e}")
            return False
    
    def _load_models(self) -> None:
        """Загружает список доступных моделей."""
        try:
            models_url = f"{self.base_url}/models"
            response = self.session.get(models_url, timeout=self.timeout)
            
            if response.status_code == 200:
                models_data = response.json()
                self.available_models = models_data.get('data', [])
                
                if self.available_models:
                    self.current_model = self.available_models[0]['id']
                    logger.info(f"✅ Загружено {len(self.available_models)} моделей")
                    logger.info(f"📌 Активная модель: {self.current_model}")
                    
                    # Выводим все доступные модели
                    for model in self.available_models:
                        logger.info(f"   - {model.get('id', 'unknown')}")
                else:
                    logger.warning("⚠️ Модели не найдены в LM Studio")
            else:
                logger.error(f"❌ Не удалось получить модели (статус: {response.status_code})")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке моделей: {e}")
    
    def test_chat(self) -> bool:
        """Тестирует работу чата с моделью."""
        if not self.is_available or not self.current_model:
            return False
        
        try:
            test_message = "Привет! Это тест."
            response = self.generate_response(test_message, max_tokens=10)
            
            if response and len(response.strip()) > 0:
                logger.info(f"✅ Тест чата успешен: {response[:50]}...")
                return True
            else:
                logger.warning("⚠️ Тест чата: получен пустой ответ")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка теста чата: {e}")
            return False
    
    def _make_request_with_retry(self, url: str, data: dict, headers: dict) -> Optional[requests.Response]:
        """Выполняет запрос с повторными попытками."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(url, headers=headers, json=data, timeout=self.timeout)
                return response
            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут при попытке {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Экспоненциальная задержка
                continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"Ошибка соединения при попытке {attempt + 1}/{self.max_retries}")
                self.is_available = False
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
            except Exception as e:
                logger.error(f"Неожиданная ошибка при попытке {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                continue
        
        return None
    
    def generate_response(
        self, 
        message: str, 
        temperature: float = 0.7, 
        max_tokens: int = 1500,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Генерирует ответ от LM Studio.
        
        Args:
            message: Сообщение пользователя
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            system_prompt: Системный промпт
            
        Returns:
            Ответ модели или None при ошибке
        """
        if not self.is_available or not self.current_model:
            logger.warning("LM Studio недоступен или модель не загружена")
            return None
        
        try:
            # Формируем сообщения
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": message})
            
            # Подготавливаем данные запроса
            data = {
                "model": self.current_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            headers = {"Content-Type": "application/json"}
            chat_url = f"{self.base_url}/chat/completions"
            
            logger.debug(f"Отправка запроса в LM Studio: {message[:50]}...")
            
            # Отправляем запрос с повторными попытками
            response = self._make_request_with_retry(chat_url, data, headers)
            
            if response and response.status_code == 200:
                response_data = response.json()
                content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if content.strip():
                    logger.debug(f"Получен ответ от LM Studio: {content[:50]}...")
                    return content.strip()
                else:
                    logger.warning("LM Studio вернул пустой ответ")
                    return None
            elif response:
                logger.error(f"Ошибка LM Studio: {response.status_code} - {response.text[:200]}")
                return None
            else:
                logger.error("Не удалось получить ответ от LM Studio после всех попыток")
                return None
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обращении к LM Studio: {e}")
            return None
    
    def answer_question(self, question: str, context: str = "") -> str:
        """
        Отвечает на вопрос пользователя о рисках непрерывности.
        
        Args:
            question: Вопрос пользователя
            context: Контекст (материалы урока)
            
        Returns:
            Ответ на вопрос
        """
        if not self.is_available:
            return self._get_fallback_answer(question)
        
        # Системный промпт для экспертной системы
        system_prompt = """Ты - эксперт по рискам нарушения непрерывности деятельности кредитных организаций. 
Отвечай на вопросы четко, профессионально и понятно. 
Если в контексте есть информация, используй её. 
Если информации недостаточно, дай общий ответ на основе своих знаний о рисках непрерывности."""
        
        # Формируем промпт
        if context:
            user_prompt = f"""Контекст урока:
{context}

Вопрос студента: {question}

Дай подробный и понятный ответ на основе контекста урока и твоих знаний о рисках непрерывности деятельности."""
        else:
            user_prompt = f"""Вопрос студента о рисках нарушения непрерывности деятельности: {question}

Дай подробный и понятный ответ на основе твоих знаний по этой теме."""
        
        # Генерируем ответ
        response = self.generate_response(
            user_prompt, 
            temperature=0.3,  # Низкая температура для более точных ответов
            max_tokens=1000,
            system_prompt=system_prompt
        )
        
        if response:
            return response
        else:
            return self._get_fallback_answer(question)
    
    def _get_fallback_answer(self, question: str) -> str:
        """Возвращает базовый ответ при недоступности LM Studio."""
        question_lower = question.lower()
        
        # Простые правила для базовых ответов
        if "риск нарушения непрерывности" in question_lower:
            return """Риск нарушения непрерывности деятельности - это риск нарушения способности кредитной организации поддерживать операционную устойчивость, включающую обеспечение непрерывности осуществления критически важных процессов и операций, в результате воздействия угроз непрерывности.

Этот риск является подвидом операционного риска и управляется по классической схеме: идентификация, оценка, реагирование, мониторинг."""
        
        elif "угроза непрерывности" in question_lower:
            return """Угроза непрерывности (чрезвычайная ситуация) - это обстановка на определенной территории, сложившаяся в результате аварии, опасного природного явления, катастрофы, распространения заболевания и других бедствий.

Угрозы делятся на типы: техногенные, природные, геополитические, социальные, биолого-социальные, экономические."""
        
        elif "rto" in question_lower or "время восстановления" in question_lower:
            return """RTO (Recovery Time Objective) - время восстановления процесса - это период времени, установленный для возобновления работы процесса после его прерывания в результате воздействия угрозы непрерывности."""
        
        elif "mtpd" in question_lower or "максимально допустимый" in question_lower:
            return """MTPD (Maximum Tolerable Period of Disruption) - максимально допустимый период простоя - это период времени, по истечении которого неблагоприятные последствия становятся неприемлемыми."""
        
        elif "объект риска" in question_lower or "объектом риска" in question_lower:
            return """Объектом риска нарушения непрерывности деятельности является процесс, категорированный как 'Критически важный', а также его атрибуты: RTO, MTPD, автоматизированные системы, офисы, персонал, процедуры реагирования, аутсорсинг и другие элементы окружения процесса."""
        
        elif "сценарий угроз" in question_lower or "сценарии угроз" in question_lower:
            return """Сценарий угрозы непрерывности – это последовательность событий, которые могут привести к реализации риска. Сценарии формируются на основе типов угроз и включают описание угрозы, возможные последствия для Банка и влияние на критически важные процессы."""
        
        elif "рейтинг риска" in question_lower:
            return """Рейтинг риска – это характеристика риска, определяющая приоритет мероприятий по его минимизации. Рейтинг определяется с использованием матриц, где учитывается воздействие риска и вероятность реализации угрозы."""
        
        else:
            return f"""Спасибо за ваш вопрос о рисках нарушения непрерывности деятельности.

К сожалению, сейчас я не могу дать подробный ответ на этот вопрос. Рекомендую:

1. Обратиться к материалам урока
2. Изучить основные понятия: риск нарушения непрерывности, угрозы непрерывности, RTO, MTPD
3. Пройти тест для закрепления знаний

Если у вас есть более конкретный вопрос, попробуйте переформулировать его."""
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус клиента."""
        return {
            "available": self.is_available,
            "base_url": self.base_url,
            "current_model": self.current_model,
            "models_count": len(self.available_models),
            "timeout": self.timeout
        }


# Создаем глобальный экземпляр клиента
def create_lm_studio_client(base_url: str = None, timeout: int = 30) -> LMStudioClient:
    """Создает экземпляр клиента LM Studio."""
    if base_url is None:
        from app.config import LLM_MODEL_PATH
        base_url = LLM_MODEL_PATH
    
    return LMStudioClient(base_url, timeout)