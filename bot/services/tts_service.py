"""Сервис для преобразования текста в речь (TTS)."""
import os
import tempfile
from typing import Optional, List
from pathlib import Path
from openai import OpenAI
from bot.utils.config import settings
from bot.utils.logger import log
from bot.services.cache_service import cache_service


class TTSService:
    """Сервис для работы с OpenAI TTS API."""
    
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
        self.max_chars = 4096  # Лимит OpenAI TTS
    
    async def synthesize(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Преобразование текста в аудио."""
        try:
            # Проверка кэша
            import hashlib
            import base64
            cache_key = f"tts:{hashlib.md5(text.encode()).hexdigest()}"
            cached = await cache_service.get(cache_key)
            if cached:
                log.debug("TTS результат из кэша")
                # Кэш хранит base64 строку
                return base64.b64decode(cached)
            
            # Обрезка текста если превышает лимит
            if len(text) > self.max_chars:
                text = text[:self.max_chars]
                log.warning(f"Текст обрезан до {self.max_chars} символов")
            
            response = self.client.audio.speech.create(
                model=settings.openai_tts_model,
                voice=settings.openai_tts_voice,
                input=text
            )
            
            audio_bytes = response.content
            
            # Сохранение в кэш (сохраняем как base64 для JSON)
            import base64
            await cache_service.set(cache_key, base64.b64encode(audio_bytes).decode(), ttl=3600)
            
            # Сохранение в файл если указан путь
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
            
            log.info(f"TTS успешно: {len(text)} символов -> {len(audio_bytes)} байт")
            return audio_bytes
        except Exception as e:
            log.error(f"Ошибка TTS: {e}")
            raise
    
    def split_text(self, text: str) -> List[str]:
        """Разбивка длинного текста на части."""
        if len(text) <= self.max_chars:
            return [text]
        
        parts = []
        sentences = text.split(". ")
        current_part = ""
        
        for sentence in sentences:
            if len(current_part) + len(sentence) + 2 <= self.max_chars:
                current_part += sentence + ". "
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = sentence + ". "
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts


tts_service = TTSService()

