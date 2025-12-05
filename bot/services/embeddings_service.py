"""Сервис для генерации embeddings."""
from typing import List, Optional
from openai import OpenAI
from bot.utils.config import settings
from bot.utils.logger import log


class EmbeddingsService:
    """Сервис для работы с OpenAI Embeddings."""
    
    def __init__(self):
        client_kwargs = {"api_key": settings.openai_api_key}
        
        # Добавляем прокси если указан
        if settings.openai_proxy:
            import httpx
            # Настройка прокси для HTTP и HTTPS
            proxy_url = settings.openai_proxy
            proxies = {
                "http://": proxy_url,
                "https://": proxy_url
            }
            client_kwargs["http_client"] = httpx.Client(
                proxies=proxies,
                timeout=60.0,
                verify=True  # Проверка SSL сертификата
            )
            log.info(f"Используется прокси для OpenAI: {settings.openai_proxy}")
        
        self.client = OpenAI(**client_kwargs)
        self.model = settings.openai_embedding_model
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Генерация embeddings для списка текстов."""
        try:
            # Проверка размера батча - если слишком большой, разбиваем на части
            max_batch_size = 10  # Безопасный размер батча
            
            if len(texts) > max_batch_size:
                log.warning(f"Батч слишком большой ({len(texts)}), разбиваем на части...")
                all_embeddings = []
                for i in range(0, len(texts), max_batch_size):
                    batch = texts[i:i + max_batch_size]
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=batch
                    )
                    embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(embeddings)
                log.info(f"Сгенерировано {len(all_embeddings)} embeddings")
                return all_embeddings
            
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            log.info(f"Сгенерировано {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            log.error(f"Ошибка генерации embeddings: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Генерация embedding для одного текста."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]


embeddings_service = EmbeddingsService()

