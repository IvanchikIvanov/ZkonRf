"""Сервис кэширования с Redis."""
import json
import hashlib
from typing import Optional, Any
import redis.asyncio as redis
from bot.utils.config import settings
from bot.utils.logger import log


class CacheService:
    """Сервис для работы с Redis кэшем."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    @property
    def is_available(self) -> bool:
        return self.redis_client is not None
    
    async def connect(self):
        """Подключение к Redis."""
        try:
            redis_url = settings.redis_url_resolved
            if redis_url:
                self.redis_client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True
                )
            else:
                redis_kwargs = {
                    "host": settings.redis_host,
                    "port": settings.redis_port,
                    "db": settings.redis_db,
                    "decode_responses": True
                }
                
                # Добавляем пароль если указан
                if settings.redis_password:
                    redis_kwargs["password"] = settings.redis_password
                
                self.redis_client = redis.Redis(**redis_kwargs)
            await self.redis_client.ping()
            log.info("Подключение к Redis установлено")
        except Exception as e:
            log.error(f"Ошибка подключения к Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Отключение от Redis."""
        if self.redis_client:
            await self.redis_client.close()
            log.info("Отключение от Redis")
    
    def _get_key(self, prefix: str, value: str) -> str:
        """Генерация ключа кэша."""
        hash_value = hashlib.md5(value.encode()).hexdigest()
        return f"{prefix}:{hash_value}"
    
    async def delete(self, key: str) -> bool:
        """Получение значения из кэша."""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            log.error(f"Ошибка получения из кэша: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранение значения в кэш."""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or settings.redis_cache_ttl
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, ensure_ascii=False)
            )
            return True
        except Exception as e:
            log.error(f"Ошибка сохранения в кэш: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        func,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """Получить из кэша или выполнить функцию и сохранить."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        result = await func(*args, **kwargs) if callable(func) else func
        await self.set(key, result, ttl)
        return result
    
    async def delete(self, key: str) -> bool:
        """Удаление ключа из кэша."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            log.error(f"Ошибка удаления из кэша: {e}")
            return False
    
    async def incr_expire(self, key: str, ttl_seconds: int) -> Optional[int]:
        """
        INCR с EXPIRE при первой установке ключа (окна rate limit).
        Возвращает новое значение счётчика или None, если Redis недоступен/ошибка.
        """
        if not self.redis_client:
            return None
        try:
            n = await self.redis_client.incr(key)
            if n == 1:
                await self.redis_client.expire(key, ttl_seconds)
            return int(n)
        except Exception as e:
            log.error(f"Ошибка incr_expire для ключа {key}: {e}")
            return None
    
    async def acquire_lock(self, key: str, ttl_seconds: int) -> bool:
        """Простой распределённый lock (SET NX EX)."""
        if not self.redis_client:
            return False
        try:
            return bool(await self.redis_client.set(key, "1", nx=True, ex=ttl_seconds))
        except Exception as e:
            log.error(f"Ошибка acquire_lock {key}: {e}")
            return False
    
    async def extend_ttl(self, key: str, ttl: int) -> bool:
        """
        Продлить время жизни ключа в кэше.
        
        Args:
            key: Ключ кэша
            ttl: Время жизни в секундах
            
        Returns:
            True если успешно, False если ключ не существует или ошибка
        """
        if not self.redis_client:
            return False
        
        try:
            # Проверяем существование ключа перед продлением TTL
            exists = await self.redis_client.exists(key)
            if exists:
                await self.redis_client.expire(key, ttl)
                return True
            return False
        except Exception as e:
            log.error(f"Ошибка продления TTL для ключа {key}: {e}")
            return False
    
    async def scan_keys(self, pattern: str) -> list:
        """Все ключи по шаблону (для служебных скриптов, например опрос ЮKassa)."""
        if not self.redis_client:
            return []
        keys: list = []
        try:
            async for k in self.redis_client.scan_iter(match=pattern, count=200):
                keys.append(k)
        except Exception as e:
            log.error(f"Ошибка scan_keys {pattern}: {e}")
        return keys
    
    async def cache_query(self, query: str, func, *args, **kwargs) -> Any:
        """Кэширование результата запроса."""
        cache_key = self._get_key("query", query)
        return await self.get_or_set(cache_key, func, *args, **kwargs)


cache_service = CacheService()

