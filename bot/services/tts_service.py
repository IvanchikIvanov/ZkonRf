"""Сервис для преобразования текста в речь (TTS) через переключаемый провайдер."""
import base64
import hashlib
from typing import Optional, List
import httpx
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from bot.utils.config import settings
from bot.utils.logger import log
from bot.services.cache_service import cache_service


class TTSService:
    """Сервис для работы с ElevenLabs/OpenAI TTS API."""
    
    def __init__(self):
        self.provider = settings.tts_provider.strip().lower()
        self.max_chars = settings.max_text_length
        
        self.elevenlabs_client: Optional[ElevenLabs] = None
        self.openai_client: Optional[OpenAI] = None
        
        if self.provider == "elevenlabs":
            if not settings.elevenlabs_api_key:
                raise ValueError("TTS provider 'elevenlabs' требует ELEVENLABS_API_KEY")
            if not settings.elevenlabs_voice_id:
                raise ValueError("TTS provider 'elevenlabs' требует ELEVENLABS_VOICE_ID")
            
            self.elevenlabs_client = ElevenLabs(api_key=settings.elevenlabs_api_key)
            self.voice_id = settings.elevenlabs_voice_id
            self.model = settings.elevenlabs_model
            self.output_format = settings.elevenlabs_output_format
        
        elif self.provider in {"chatgpt", "openai"}:
            if not settings.openai_api_key:
                raise ValueError("TTS provider 'chatgpt' требует OPENAI_API_KEY")
            
            client_kwargs = {"api_key": settings.openai_api_key}
            if settings.openai_proxy:
                proxy_url = settings.openai_proxy
                client_kwargs["http_client"] = httpx.Client(
                    proxies={
                        "http://": proxy_url,
                        "https://": proxy_url
                    },
                    timeout=60.0,
                    verify=True
                )
            
            self.openai_client = OpenAI(**client_kwargs)
            self.model = settings.openai_tts_model
            self.voice_id = settings.openai_tts_voice
        
        else:
            raise ValueError(
                f"Неподдерживаемый TTS_PROVIDER='{settings.tts_provider}'. "
                "Допустимые значения: elevenlabs, chatgpt"
            )
    
    async def synthesize(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Преобразование текста в аудио через выбранный TTS-провайдер."""
        try:
            cache_key = self._build_cache_key(text)
            cached = await cache_service.get(cache_key)
            if cached:
                log.debug("TTS результат из кэша")
                return base64.b64decode(cached)
            
            # Обрезка текста если превышает лимит
            if len(text) > self.max_chars:
                text = text[:self.max_chars]
                log.warning(f"Текст обрезан до {self.max_chars} символов")
            
            if self.provider == "elevenlabs":
                if self.elevenlabs_client is None:
                    raise RuntimeError("ElevenLabs клиент не инициализирован")
                
                audio_stream = self.elevenlabs_client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    model_id=self.model,
                    text=text,
                    output_format=self.output_format,
                    voice_settings=VoiceSettings(
                        stability=settings.elevenlabs_stability,
                        similarity_boost=settings.elevenlabs_similarity_boost
                    )
                )
                audio_bytes = b"".join(audio_stream)
            else:
                if self.openai_client is None:
                    raise RuntimeError("OpenAI клиент не инициализирован")
                
                response = self.openai_client.audio.speech.create(
                    model=self.model,
                    voice=self.voice_id,
                    input=text
                )
                audio_bytes = response.content
            
            if not audio_bytes:
                raise RuntimeError("TTS провайдер вернул пустой аудио-ответ")
            
            # Сохранение в кэш
            await cache_service.set(cache_key, base64.b64encode(audio_bytes).decode(), ttl=3600)
            
            # Сохранение в файл если указан путь
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
            
            log.info(f"TTS успешно ({self.provider}): {len(text)} символов -> {len(audio_bytes)} байт")
            return audio_bytes
        except Exception as e:
            log.error(f"Ошибка TTS ({self.provider}): {e}")
            raise
    
    def _build_cache_key(self, text: str) -> str:
        """Формирует ключ кэша с учетом провайдера и модели."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        provider_signature = f"{self.provider}:{self.model}:{self.voice_id}"
        return f"tts:{provider_signature}:{text_hash}"
    
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

