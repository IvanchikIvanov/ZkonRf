"""Сервис для преобразования речи в текст (STT)."""
import os
import tempfile
from typing import Optional
from pathlib import Path
from openai import OpenAI
from bot.utils.config import settings
from bot.utils.logger import log
from bot.services.cache_service import cache_service


class STTService:
    """Сервис для работы с OpenAI Whisper API."""
    
    def __init__(self):
        client_kwargs = {"api_key": settings.openai_api_key}
        
        # Добавляем прокси если указан
        if settings.openai_proxy:
            import httpx
            proxy_url = settings.openai_proxy
            proxies = {
                "http://": proxy_url,
                "https://": proxy_url
            }
            client_kwargs["http_client"] = httpx.Client(
                proxies=proxies,
                timeout=60.0,
                verify=True
            )
        
        self.client = OpenAI(**client_kwargs)
    
    async def transcribe(self, audio_file_path: str, language: str = "ru") -> str:
        """Преобразование аудио в текст."""
        try:
            # Проверка кэша
            cache_key = f"stt:{os.path.basename(audio_file_path)}"
            cached = await cache_service.get(cache_key)
            if cached:
                log.debug("STT результат из кэша")
                return cached
            
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            
            text = transcript.strip() if isinstance(transcript, str) else ""
            
            # Сохранение в кэш
            await cache_service.set(cache_key, text, ttl=3600)
            
            log.info(f"STT успешно: {len(text)} символов")
            return text
        except Exception as e:
            log.error(f"Ошибка STT: {e}")
            raise
    
    async def transcribe_from_bytes(self, audio_bytes: bytes, language: str = "ru") -> str:
        """Преобразование аудио из bytes в текст."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            return await self.transcribe(tmp_path, language)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


stt_service = STTService()

