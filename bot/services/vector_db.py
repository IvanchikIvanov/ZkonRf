"""Сервис для работы с векторной базой данных."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Any
from bot.utils.config import settings
from bot.utils.logger import log


class VectorDBService:
    """Сервис для работы с ChromaDB."""
    
    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None
        self.collection_name = "codexes"
    
    def initialize(self):
        """Инициализация векторной БД."""
        try:
            db_path = settings.database_path_resolved
            self.client = chromadb.PersistentClient(
                path=str(db_path),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Получение или создание коллекции
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                log.info(f"Коллекция '{self.collection_name}' загружена")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Кодексы РФ"}
                )
                log.info(f"Коллекция '{self.collection_name}' создана")
            
            log.info("Векторная БД инициализирована")
        except Exception as e:
            log.error(f"Ошибка инициализации векторной БД: {e}")
            raise
    
    def add_articles(
        self,
        articles: List[Dict[str, Any]]
    ):
        """Добавление статей в векторную БД."""
        if not self.collection:
            raise RuntimeError("Векторная БД не инициализирована")
        
        try:
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for article in articles:
                ids.append(article["id"])
                documents.append(article["text"])
                embeddings.append(article["embedding"])
                metadata = {
                    "codex_name": article["codex_name"],
                    "article_number": article["article_number"],
                    "country": article.get("country", "ru"),
                    "link": article.get("link", "")
                }
                # Добавляем информацию о чанках если есть
                if "chunk_number" in article:
                    metadata["chunk_number"] = str(article["chunk_number"])
                    metadata["total_chunks"] = str(article["total_chunks"])
                
                metadatas.append(metadata)
            
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            log.info(f"Добавлено {len(articles)} статей в векторную БД")
        except Exception as e:
            log.error(f"Ошибка добавления статей: {e}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        country_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Поиск релевантных статей.
        
        Args:
            query_embedding: Векторное представление запроса
            n_results: Количество результатов
            country_filter: Фильтр по коду страны (например, 'ru', 'kz'). Если None - поиск по всем странам.
        """
        if not self.collection:
            raise RuntimeError("Векторная БД не инициализирована")
        
        try:
            # Если указан фильтр по стране, используем where фильтр
            where_filter = None
            if country_filter:
                where_filter = {"country": country_filter}
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            articles = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i]
                    article = {
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "codex_name": metadata.get("codex_name", ""),
                        "article_number": metadata.get("article_number", ""),
                        "country": metadata.get("country", "ru"),
                        "link": metadata.get("link", ""),
                        "distance": results["distances"][0][i] if "distances" in results else None
                    }
                    # Добавляем информацию о чанках если есть
                    if "chunk_number" in metadata:
                        article["chunk_number"] = metadata.get("chunk_number")
                        article["total_chunks"] = metadata.get("total_chunks")
                    
                    articles.append(article)
            
            return articles
        except Exception as e:
            log.error(f"Ошибка поиска в векторной БД: {e}")
            return []
    
    def get_existing_ids(self) -> set:
        """Получить множество существующих ID в коллекции."""
        if not self.collection:
            return set()
        
        try:
            # Получаем все ID из коллекции
            results = self.collection.get()
            if results and "ids" in results:
                return set(results["ids"])
            return set()
        except Exception as e:
            log.error(f"Ошибка получения существующих ID: {e}")
            return set()
    
    def get_count(self) -> int:
        """Получить количество статей в БД."""
        if not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            log.error(f"Ошибка получения количества статей: {e}")
            return 0


vector_db = VectorDBService()

