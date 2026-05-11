"""Миграция векторных данных из ChromaDB в pgvector."""
from typing import List, Dict, Any

from bot.services.vector_db import ChromaVectorDBService, PGVectorDBService
from bot.utils.logger import log


def _normalize_rows(
    ids: List[str],
    documents: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, item_id in enumerate(ids):
        meta = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        row: Dict[str, Any] = {
            "id": item_id,
            "text": documents[idx],
            "embedding": embeddings[idx],
            "codex_name": meta.get("codex_name", ""),
            "article_number": str(meta.get("article_number", "")),
            "country": meta.get("country", "ru"),
            "link": meta.get("link", ""),
        }
        if meta.get("chunk_number") is not None:
            row["chunk_number"] = int(meta["chunk_number"])
        if meta.get("total_chunks") is not None:
            row["total_chunks"] = int(meta["total_chunks"])
        rows.append(row)
    return rows


def migrate(batch_size: int = 500) -> None:
    """Переносит embeddings из Chroma в pgvector."""
    chroma = ChromaVectorDBService()
    chroma.initialize()
    if chroma.collection is None:
        raise RuntimeError("Chroma коллекция не инициализирована")
    
    target = PGVectorDBService()
    target.initialize()
    
    total = chroma.collection.count()
    if total == 0:
        log.warning("Chroma коллекция пустая, миграция не требуется")
        return
    
    log.info(f"Старт миграции Chroma -> pgvector. Записей: {total}")
    
    migrated = 0
    for offset in range(0, total, batch_size):
        chunk = chroma.collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "embeddings", "metadatas"],
        )
        
        ids = chunk.get("ids", [])
        documents = chunk.get("documents", [])
        embeddings = chunk.get("embeddings", [])
        metadatas = chunk.get("metadatas", [])
        
        if not ids:
            continue
        
        rows = _normalize_rows(ids, documents, embeddings, metadatas)
        target.add_articles(rows)
        migrated += len(rows)
        log.info(f"Перенесено {migrated}/{total}")
    
    log.info(f"Миграция завершена. Всего перенесено: {migrated}")


if __name__ == "__main__":
    migrate()
