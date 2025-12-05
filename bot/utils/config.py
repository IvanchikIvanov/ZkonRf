"""Конфигурация приложения."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram
    telegram_bot_token: str
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"
    max_tokens: int = 2000
    temperature: float = 0.7
    openai_proxy: str = ""  # Прокси для OpenAI API (например: http://proxy.example.com:8080)
    
    # Database
    database_path: str = "/app/data/embeddings"
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_cache_ttl: int = 3600
    
    # Logging
    log_level: str = "INFO"
    log_path: str = "/app/logs"
    
    # Docker
    worker_count: int = 2
    
    # Payment - ЮKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_test_mode: bool = True
    
    # Payment - Настройки
    free_requests_per_day: int = 3
    # Цены подписки (Stars)
    subscription_price_stars_1month: int = 100  # Telegram Stars за 1 месяц
    subscription_price_stars_3months: int = 200  # Telegram Stars за 3 месяца
    subscription_price_stars_1year: int = 900  # Telegram Stars за 1 год
    # Цены подписки (ЮKassa, рубли)
    subscription_price_yookassa_1month: int = 100  # Рубли за 1 месяц
    subscription_price_yookassa_3months: int = 200  # Рубли за 3 месяца
    subscription_price_yookassa_1year: int = 900  # Рубли за 1 год
    webhook_url: str = ""  # URL для вебхуков ЮKassa
    webhook_port: int = 8080  # Порт для веб-сервера вебхуков
    
    # Payment - Crypto / EVM
    crypto_enabled_networks: str = "ethereum,bsc"  # Список включенных сетей через запятую
    crypto_master_wallet: str = ""  # Адрес кошелька для приема платежей
    
    # Whitelist
    user_whitelist: str = ""  # Список ID пользователей с бесплатным доступом через запятую (например: "123456,789012")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def database_path_resolved(self) -> Path:
        """Возвращает абсолютный путь к базе данных."""
        path = Path(self.database_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def log_path_resolved(self) -> Path:
        """Возвращает абсолютный путь к логам."""
        path = Path(self.log_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()

