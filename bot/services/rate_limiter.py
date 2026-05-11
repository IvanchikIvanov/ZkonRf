"""Сервис для ограничения частоты запросов."""
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Tuple

from bot.services.cache_service import cache_service


class RateLimiter:
    """Ограничитель частоты запросов."""
    
    def __init__(self):
        self.user_requests = defaultdict(list)
        self.user_last_seen = {}
        self.max_requests_per_minute = 3
        self.max_requests_per_hour = 20
        self.max_tracked_users = 200000
        self._cleanup_every_n_checks = 1000
        self._checks_counter = 0
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        Проверка лимита (in-process fallback, если Redis недоступен).
        """
        now = datetime.now()
        self._checks_counter += 1
        self.user_last_seen[user_id] = now
        user_history = self.user_requests[user_id]
        
        user_history[:] = [req_time for req_time in user_history 
                          if now - req_time < timedelta(hours=1)]
        
        recent_requests = [req_time for req_time in user_history 
                          if now - req_time < timedelta(minutes=1)]
        if len(recent_requests) >= self.max_requests_per_minute:
            return False, "⏳ Слишком много запросов. Подождите минуту."
        
        if len(user_history) >= self.max_requests_per_hour:
            return False, "⏳ Превышен лимит запросов в час. Подождите."
        
        user_history.append(now)
        
        if self._checks_counter % self._cleanup_every_n_checks == 0:
            self._cleanup_inactive_users(now)
        
        return True, ""
    
    async def check_rate_limit_async(self, user_id: int) -> Tuple[bool, str]:
        """
        Проверка лимита с Redis (общая для нескольких реплик), иначе fallback в память.
        """
        if cache_service.is_available:
            now = int(time.time())
            minute_bucket = now // 60
            hour_bucket = now // 3600
            k_min = f"rl:1m:{user_id}:{minute_bucket}"
            k_h = f"rl:1h:{user_id}:{hour_bucket}"
            n_min = await cache_service.incr_expire(k_min, 120)
            n_h = await cache_service.incr_expire(k_h, 7200)
            if n_min is None or n_h is None:
                return self.check_rate_limit(user_id)
            if n_min > self.max_requests_per_minute:
                return False, "⏳ Слишком много запросов. Подождите минуту."
            if n_h > self.max_requests_per_hour:
                return False, "⏳ Превышен лимит запросов в час. Подождите."
            return True, ""
        
        return self.check_rate_limit(user_id)
    
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


rate_limiter = RateLimiter()
