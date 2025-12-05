"""Сервис для ограничения частоты запросов."""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Tuple


class RateLimiter:
    """Ограничитель частоты запросов."""
    
    def __init__(self):
        self.user_requests = defaultdict(list)
        self.max_requests_per_minute = 3
        self.max_requests_per_hour = 20
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        Проверка лимита запросов для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple[bool, str]: (is_allowed, message_if_blocked)
        """
        now = datetime.now()
        user_history = self.user_requests[user_id]
        
        # Удаляем старые записи (старше часа)
        user_history[:] = [req_time for req_time in user_history 
                          if now - req_time < timedelta(hours=1)]
        
        # Проверка лимита в минуту
        recent_requests = [req_time for req_time in user_history 
                          if now - req_time < timedelta(minutes=1)]
        if len(recent_requests) >= self.max_requests_per_minute:
            return False, "⏳ Слишком много запросов. Подождите минуту."
        
        # Проверка лимита в час
        if len(user_history) >= self.max_requests_per_hour:
            return False, "⏳ Превышен лимит запросов в час. Подождите."
        
        # Добавляем текущий запрос
        user_history.append(now)
        return True, ""


# Глобальный экземпляр
rate_limiter = RateLimiter()

