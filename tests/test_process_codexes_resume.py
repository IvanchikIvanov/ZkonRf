import asyncio

from scripts import process_codexes


class FakeVectorDB:
    def __init__(self):
        self.saved = []

    def add_articles(self, articles):
        self.saved.extend(articles)


class FlakyEmbeddingsService:
    def __init__(self):
        self.calls = 0

    async def generate_embeddings(self, texts):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary proxy failure")
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_save_indexed_article_updates_existing_ids(monkeypatch):
    fake_db = FakeVectorDB()
    monkeypatch.setattr(process_codexes, "vector_db", fake_db)
    existing_ids = set()
    article = {"id": "ru_test_article_1", "embedding": [0.1], "text": "text"}

    assert process_codexes.save_indexed_article(article, existing_ids) is True
    assert process_codexes.save_indexed_article(article, existing_ids) is False

    assert existing_ids == {"ru_test_article_1"}
    assert fake_db.saved == [article]


def test_generate_embeddings_with_retries_continues_after_transient_failure(monkeypatch):
    service = FlakyEmbeddingsService()
    monkeypatch.setattr(process_codexes, "embeddings_service", service)
    monkeypatch.setenv("EMBEDDING_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("EMBEDDING_RETRY_BASE_DELAY", "0")

    embeddings = asyncio.run(process_codexes.generate_embeddings_with_retries(["text"]))

    assert embeddings == [[0.1, 0.2, 0.3]]
    assert service.calls == 2
