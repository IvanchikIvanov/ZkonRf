"""Конфигурация приложения."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator


class Settings(BaseSettings):
    """Настройки приложения."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow"  # Разрешаем дополнительные поля из .env
    )
    
    # Telegram
    telegram_bot_token: str
    # Имя бота без @ для ссылок t.me/<username> (return_url ЮKassa и т.п.)
    telegram_bot_username: str = ""
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"
    tts_provider: str = "chatgpt"  # Поддерживаемые значения: chatgpt, elevenlabs
    max_tokens: int = 2000
    temperature: float = 0.7
    openai_proxy: str = ""  # Прокси для OpenAI API (например: http://proxy.example.com:8080)
    confirm_intent_first: bool = True  # Всегда начинать ответ с проверки понимания запроса
    
    # Grok
    grok_api_key: str = ""
    grok_model: str = "grok-beta"
    grok_proxy: str = ""  # Прокси для Grok API
    
    @field_validator("openai_proxy", "grok_proxy", mode="before")
    @classmethod
    def normalize_optional_http_proxy(cls, v):
        """
        Пусто, если прокси не нужен. Обрезает inline-комментарий (# ...) из .env.
        Некорректные значения (не http/https) — как пусто, чтобы не ломать httpx.
        """
        if v is None:
            return ""
        s = str(v).strip()
        if not s:
            return ""
        if "#" in s:
            s = s.split("#", 1)[0].strip()
        if not s:
            return ""
        low = s.lower()
        if low.startswith("http://") or low.startswith("https://"):
            return s
        return ""
    
    # ElevenLabs (для голоса девушки)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""  # ID голоса девушки из ElevenLabs
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity_boost: float = 0.75
    max_text_length: int = 5000  # Максимальная длина текста для TTS
    
    # Conversation context
    context_prompt_messages: int = 30  # Сколько последних сообщений передавать в промпт
    context_scan_messages: int = 200  # Сколько сообщений анализировать для извлечения страны/кодекса
    context_max_content_length: int = 4000  # Максимальная длина одного сообщения в истории
    
    # Database
    database_path: str = "/app/data/embeddings"
    redis_url: str = ""
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_cache_ttl: int = 3600
    
    # Vector DB backend
    vector_backend: str = "chroma"  # Поддерживаемые значения: chroma, pgvector
    
    # PostgreSQL + pgvector
    database_url: str = ""
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "zakonrff"
    postgres_user: str = "zakonrff"
    postgres_password: str = "zakonrff"
    pgvector_table: str = "codex_embeddings"
    embedding_dimensions: int = 3072  # text-embedding-3-large
    
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
    # Пока бот работает: опрос Redis payment:* и API ЮKassa, сек. 0 = автоматическая активация по карте отключена
    yookassa_poll_interval_seconds: int = 120
    
    # Payment - Crypto / EVM
    crypto_enabled_networks: str = "ethereum,bsc"  # Список включенных сетей через запятую
    crypto_master_wallet: str = ""  # Адрес кошелька для приема платежей
    
    # Whitelist
    user_whitelist: str = ""  # Список ID пользователей с бесплатным доступом через запятую (например: "123456,789012")
    
    @property
    def postgres_database_url(self) -> str:
        """Railway/managed Postgres connection URL, if provided."""
        return os.getenv("DATABASE_URL") or self.database_url
    
    @property
    def postgres_host_resolved(self) -> str:
        """Postgres host with Railway PGHOST fallback."""
        return os.getenv("POSTGRES_HOST") or os.getenv("PGHOST") or self.postgres_host
    
    @property
    def postgres_port_resolved(self) -> int:
        """Postgres port with Railway PGPORT fallback."""
        value = os.getenv("POSTGRES_PORT") or os.getenv("PGPORT")
        return int(value) if value else self.postgres_port
    
    @property
    def postgres_db_resolved(self) -> str:
        """Postgres database name with Railway PGDATABASE fallback."""
        return os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE") or self.postgres_db
    
    @property
    def postgres_user_resolved(self) -> str:
        """Postgres user with Railway PGUSER fallback."""
        return os.getenv("POSTGRES_USER") or os.getenv("PGUSER") or self.postgres_user
    
    @property
    def postgres_password_resolved(self) -> str:
        """Postgres password with Railway PGPASSWORD fallback."""
        return os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD") or self.postgres_password
    
    @property
    def redis_url_resolved(self) -> str:
        """Redis URL with Railway REDIS_URL fallback."""
        return os.getenv("REDIS_URL") or self.redis_url
    
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
    
    @property
    def telegram_bot_deeplink(self) -> str:
        """Ссылка для открытия бота в Telegram (t.me)."""
        un = (self.telegram_bot_username or "").strip().lstrip("@")
        if un:
            return f"https://t.me/{un}"
        return f"https://t.me/{self.telegram_bot_token.split(':')[0]}"


settings = Settings()

