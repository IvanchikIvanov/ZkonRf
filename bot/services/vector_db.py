"""Сервис для работы с векторной базой данных."""
from typing import List, Dict, Optional, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from bot.utils.config import settings
from bot.utils.logger import log

try:
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None  # type: ignore
    sql = None  # type: ignore
    dict_row = None  # type: ignore


class ChromaVectorDBService:
    """Vector backend на ChromaDB (обратная совместимость)."""
    
    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None
        self.collection_name = "codexes"
    
    def initialize(self):
        try:
            db_path = settings.database_path_resolved
            self.client = chromadb.PersistentClient(
                path=str(db_path),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                log.info(f"Коллекция '{self.collection_name}' загружена (chroma)")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Кодексы и НПА"}
                )
                log.info(f"Коллекция '{self.collection_name}' создана (chroma)")
            
            log.info("Векторная БД инициализирована (chroma)")
        except Exception as e:
            log.error(f"Ошибка инициализации ChromaDB: {e}")
            raise
    
    def add_articles(self, articles: List[Dict[str, Any]]):
        if not self.collection:
            raise RuntimeError("Векторная БД (chroma) не инициализирована")
        
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
                    "link": article.get("link", ""),
                    "codex_key": article.get("codex_key", "unknown"),
                    "source_type": article.get("source_type", "code"),
                    "topic_tags": article.get("topic_tags", ""),
                }
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
            log.info(f"Добавлено {len(articles)} статей в ChromaDB")
        except Exception as e:
            log.error(f"Ошибка добавления статей в ChromaDB: {e}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        country_filter: Optional[str] = None,
        codex_filter: Optional[str] = None,
        source_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.collection:
            raise RuntimeError("Векторная БД (chroma) не инициализирована")
        
        try:
            filters = []
            if country_filter:
                filters.append({"country": country_filter})
            if codex_filter:
                filters.append({"codex_key": codex_filter})
            if source_type_filter:
                filters.append({"source_type": source_type_filter})
            
            if len(filters) == 1:
                where_filter = filters[0]
            elif len(filters) > 1:
                where_filter = {"$and": filters}
            else:
                where_filter = None
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
                        "codex_key": metadata.get("codex_key", ""),
                        "source_type": metadata.get("source_type", ""),
                        "topic_tags": metadata.get("topic_tags", ""),
                        "distance": results["distances"][0][i] if "distances" in results else None
                    }
                    if "chunk_number" in metadata:
                        article["chunk_number"] = metadata.get("chunk_number")
                        article["total_chunks"] = metadata.get("total_chunks")
                    articles.append(article)
            
            return articles
        except Exception as e:
            log.error(f"Ошибка поиска в ChromaDB: {e}")
            return []
    
    def get_existing_ids(self) -> set:
        if not self.collection:
            return set()
        
        try:
            results = self.collection.get()
            if results and "ids" in results:
                return set(results["ids"])
            return set()
        except Exception as e:
            log.error(f"Ошибка получения существующих ID из ChromaDB: {e}")
            return set()
    
    def get_count(self) -> int:
        if not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            log.error(f"Ошибка получения количества статей из ChromaDB: {e}")
            return 0


class PGVectorDBService:
    """Vector backend на PostgreSQL + pgvector."""
    
    def __init__(self):
        self.conn = None
        self.table_name = settings.pgvector_table
        self.dimensions = settings.embedding_dimensions
    
    @staticmethod
    def _embedding_to_vector_literal(embedding: List[float]) -> str:
        return "[" + ",".join(str(float(v)) for v in embedding) + "]"
    
    def initialize(self):
        if psycopg is None:
            raise RuntimeError(
                "Для pgvector backend не установлен psycopg. "
                "Добавьте зависимость `psycopg[binary]`."
            )
        
        try:
            database_url = settings.postgres_database_url
            if database_url:
                self.conn = psycopg.connect(database_url, connect_timeout=10)
            else:
                self.conn = psycopg.connect(
                    host=settings.postgres_host_resolved,
                    port=settings.postgres_port_resolved,
                    dbname=settings.postgres_db_resolved,
                    user=settings.postgres_user_resolved,
                    password=settings.postgres_password_resolved,
                    connect_timeout=10
                )
            self.conn.autocommit = True
            
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                if cur.fetchone() is None:
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    except Exception as ext_err:
                        if isinstance(ext_err, psycopg.errors.InsufficientPrivilege):
                            cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                            if cur.fetchone() is None:
                                raise RuntimeError(
                                    "Нет прав на CREATE EXTENSION vector (нужен суперпользователь PostgreSQL). "
                                    "Один раз: sudo -u postgres psql -d ИМЯ_БД -c \"CREATE EXTENSION vector\" "
                                    "(ИМЯ_БД — как в DATABASE_URL / POSTGRES_DB)."
                                ) from ext_err
                        else:
                            raise
                cur.execute(
                    sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {} (
                            id TEXT PRIMARY KEY,
                            codex_name TEXT NOT NULL,
                            article_number TEXT NOT NULL,
                            country TEXT NOT NULL,
                            link TEXT NOT NULL DEFAULT '',
                            text TEXT NOT NULL,
                            embedding vector({}) NOT NULL,
                            codex_key TEXT NOT NULL DEFAULT 'unknown',
                            source_type TEXT NOT NULL DEFAULT 'code',
                            topic_tags TEXT NOT NULL DEFAULT '',
                            chunk_number INTEGER NULL,
                            total_chunks INTEGER NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(
                        sql.Identifier(self.table_name),
                        sql.SQL(str(int(self.dimensions)))
                    )
                )
                cur.execute(
                    sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS codex_key TEXT NOT NULL DEFAULT 'unknown'").format(
                        sql.Identifier(self.table_name)
                    )
                )
                cur.execute(
                    sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'code'").format(
                        sql.Identifier(self.table_name)
                    )
                )
                cur.execute(
                    sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS topic_tags TEXT NOT NULL DEFAULT ''").format(
                        sql.Identifier(self.table_name)
                    )
                )
                cur.execute(
                    sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (country)").format(
                        sql.Identifier(f"{self.table_name}_country_idx"),
                        sql.Identifier(self.table_name)
                    )
                )
                cur.execute(
                    sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (codex_key)").format(
                        sql.Identifier(f"{self.table_name}_codex_key_idx"),
                        sql.Identifier(self.table_name)
                    )
                )
                # HNSW в pgvector < 0.7 ограничен 2000 измерениями; для 3072 (text-embedding-3-large) — IVFFlat.
                try:
                    if self.dimensions <= 2000:
                        cur.execute(
                            sql.SQL(
                                "CREATE INDEX IF NOT EXISTS {} ON {} USING hnsw (embedding vector_cosine_ops)"
                            ).format(
                                sql.Identifier(f"{self.table_name}_embedding_hnsw_idx"),
                                sql.Identifier(self.table_name)
                            )
                        )
                    else:
                        cur.execute(
                            sql.SQL(
                                "CREATE INDEX IF NOT EXISTS {} ON {} USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                            ).format(
                                sql.Identifier(f"{self.table_name}_embedding_ivfflat_idx"),
                                sql.Identifier(self.table_name)
                            )
                        )
                        log.info(
                            "Векторный индекс pgvector: IVFFlat (размерность > 2000, HNSW недоступен)"
                        )
                except Exception as idx_error:
                    log.warning(f"Не удалось создать векторный индекс pgvector: {idx_error}")
            
            connection_label = (
                "DATABASE_URL"
                if database_url
                else (
                    f"{settings.postgres_host_resolved}:{settings.postgres_port_resolved}/"
                    f"{settings.postgres_db_resolved}"
                )
            )
            log.info(
                f"Векторная БД инициализирована (pgvector): "
                f"{connection_label}, table={self.table_name}"
            )
        except Exception as e:
            log.error(f"Ошибка инициализации pgvector: {e}")
            raise
    
    def add_articles(self, articles: List[Dict[str, Any]]):
        if not self.conn:
            raise RuntimeError("Векторная БД (pgvector) не инициализирована")
        if not articles:
            return
        
        try:
            insert_query = sql.SQL(
                """
                INSERT INTO {} (
                    id, codex_name, article_number, country, link, text, embedding,
                    codex_key, source_type, topic_tags, chunk_number, total_chunks
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    codex_name = EXCLUDED.codex_name,
                    article_number = EXCLUDED.article_number,
                    country = EXCLUDED.country,
                    link = EXCLUDED.link,
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    codex_key = EXCLUDED.codex_key,
                    source_type = EXCLUDED.source_type,
                    topic_tags = EXCLUDED.topic_tags,
                    chunk_number = EXCLUDED.chunk_number,
                    total_chunks = EXCLUDED.total_chunks
                """
            ).format(sql.Identifier(self.table_name))
            
            payload = []
            for article in articles:
                chunk_number = article.get("chunk_number")
                total_chunks = article.get("total_chunks")
                payload.append(
                    (
                        article["id"],
                        article["codex_name"],
                        str(article["article_number"]),
                        article.get("country", "ru"),
                        article.get("link", ""),
                        article["text"],
                        self._embedding_to_vector_literal(article["embedding"]),
                        article.get("codex_key", "unknown"),
                        article.get("source_type", "code"),
                        article.get("topic_tags", ""),
                        int(chunk_number) if chunk_number is not None else None,
                        int(total_chunks) if total_chunks is not None else None,
                    )
                )
            
            with self.conn.cursor() as cur:
                cur.executemany(insert_query, payload)
            log.info(f"Добавлено/обновлено {len(articles)} статей в pgvector")
        except Exception as e:
            log.error(f"Ошибка добавления статей в pgvector: {e}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        country_filter: Optional[str] = None,
        codex_filter: Optional[str] = None,
        source_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.conn:
            raise RuntimeError("Векторная БД (pgvector) не инициализирована")
        
        try:
            query_vector = self._embedding_to_vector_literal(query_embedding)
            where_clauses = []
            params: List[Any] = [query_vector]
            
            if country_filter:
                where_clauses.append(sql.SQL("country = %s"))
                params.append(country_filter)
            if codex_filter:
                where_clauses.append(sql.SQL("codex_key = %s"))
                params.append(codex_filter)
            if source_type_filter:
                where_clauses.append(sql.SQL("source_type = %s"))
                params.append(source_type_filter)
            
            where_sql = (
                sql.SQL("WHERE ") + sql.SQL(" AND ").join(where_clauses)
                if where_clauses
                else sql.SQL("")
            )
            params.extend([query_vector, n_results])
            
            query = sql.SQL(
                """
                SELECT
                    id, text, codex_name, article_number, country, link,
                    codex_key, source_type, topic_tags,
                    chunk_number, total_chunks,
                    embedding <=> %s::vector AS distance
                FROM {}
                {}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """
            ).format(sql.Identifier(self.table_name), where_sql)
            
            with self.conn.transaction():
                with self.conn.cursor(row_factory=dict_row) as cur:
                    if self.dimensions > 2000:
                        cur.execute("SET LOCAL ivfflat.probes = 10")
                    cur.execute(query, params)
                    rows = cur.fetchall()
            
            articles = []
            for row in rows:
                article = {
                    "id": row["id"],
                    "text": row["text"],
                    "codex_name": row["codex_name"],
                    "article_number": row["article_number"],
                    "country": row["country"],
                    "link": row["link"],
                    "codex_key": row["codex_key"],
                    "source_type": row["source_type"],
                    "topic_tags": row["topic_tags"],
                    "distance": float(row["distance"]) if row["distance"] is not None else None,
                }
                if row.get("chunk_number") is not None:
                    article["chunk_number"] = row["chunk_number"]
                if row.get("total_chunks") is not None:
                    article["total_chunks"] = row["total_chunks"]
                articles.append(article)
            
            return articles
        except Exception as e:
            log.error(f"Ошибка поиска в pgvector: {e}")
            return []
    
    def get_existing_ids(self) -> set:
        if not self.conn:
            return set()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT id FROM {}").format(sql.Identifier(self.table_name)))
                return {row[0] for row in cur.fetchall()}
        except Exception as e:
            log.error(f"Ошибка получения существующих ID из pgvector: {e}")
            return set()
    
    def get_count(self) -> int:
        if not self.conn:
            return 0
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.table_name)))
                row = cur.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            log.error(f"Ошибка получения количества статей из pgvector: {e}")
            return 0


class VectorDBService:
    """Фасад для работы с выбранным backend векторной БД."""
    
    def __init__(self):
        backend_name = settings.vector_backend.strip().lower()
        if backend_name in {"pgvector", "postgres"}:
            self.backend = PGVectorDBService()
            self.backend_name = "pgvector"
        elif backend_name == "chroma":
            self.backend = ChromaVectorDBService()
            self.backend_name = "chroma"
        else:
            raise ValueError(
                f"Неподдерживаемый VECTOR_BACKEND='{settings.vector_backend}'. "
                "Допустимые значения: chroma, pgvector"
            )
    
    def initialize(self):
        self.backend.initialize()
    
    def add_articles(self, articles: List[Dict[str, Any]]):
        self.backend.add_articles(articles)
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        country_filter: Optional[str] = None,
        codex_filter: Optional[str] = None,
        source_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.backend.search(
            query_embedding=query_embedding,
            n_results=n_results,
            country_filter=country_filter,
            codex_filter=codex_filter,
            source_type_filter=source_type_filter,
        )
    
    def get_existing_ids(self) -> set:
        return self.backend.get_existing_ids()
    
    def get_count(self) -> int:
        return self.backend.get_count()


vector_db = VectorDBService()

