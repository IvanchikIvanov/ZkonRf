"""Сервис для ограничения частоты запросов."""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Tuple


class RateLimiter:
    """Ограничитель частоты запросов."""
    
    def __init__(self):
        self.user_requests = defaultdict(list)
        self.user_last_seen = {}
        self.max_requests_per_minute = 3
        self.max_requests_per_hour = 20
        # Защита от бесконечного роста памяти при большом количестве пользователей.
        self.max_tracked_users = 200000
        self._cleanup_every_n_checks = 1000
        self._checks_counter = 0
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        Проверка лимита запросов для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Tuple[bool, str]: (is_allowed, message_if_blocked)
        """
        now = datetime.now()
        self._checks_counter += 1
        self.user_last_seen[user_id] = now
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
        
        if self._checks_counter % self._cleanup_every_n_checks == 0:
            self._cleanup_inactive_users(now)
        
        return True, ""
    
    def _cleanup_inactive_users(self, now: datetime):
        """Удаляет пользователей, которые давно не активны."""
        if len(self.user_requests) <= self.max_tracked_users:
            return
        
        inactive_before = now - timedelta(hours=2)
        users_to_remove = [
            uid for uid, last_seen in self.user_last_seen.items()
            if last_seen < inactive_before
        ]
        
        for uid in users_to_remove:
            self.user_requests.pop(uid, None)
            self.user_last_seen.pop(uid, None)


# Глобальный экземпляр
rate_limiter = RateLimiter()

