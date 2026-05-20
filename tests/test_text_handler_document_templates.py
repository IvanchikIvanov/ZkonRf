import asyncio
from unittest.mock import AsyncMock, patch

from bot.handlers.text_handler import handle_text_message
from bot.services.document_templates.models import DocumentResult


class FakeUser:
    id = 42
    username = "tester"


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []
        self.documents = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)

    async def reply_document(self, document, filename=None, caption=None):
        self.documents.append((document, filename, caption))


class FakeUpdate:
    def __init__(self, text):
        self.effective_user = FakeUser()
        self.message = FakeMessage(text)


def test_text_handler_starts_document_flow_before_rag():
    update = FakeUpdate("Составь претензию на возврат денег")
    context = object()

    with patch(
        "bot.handlers.text_handler.document_template_service.handle_text",
        new=AsyncMock(return_value=DocumentResult(status="ask_fields", message="Укажите ФИО.")),
    ), patch(
        "bot.handlers.text_handler.embeddings_service.generate_embedding",
        new=AsyncMock(side_effect=AssertionError("RAG should not run")),
    ):
        asyncio.run(handle_text_message(update, context))

    assert update.message.replies == ["Укажите ФИО."]


def test_text_handler_sends_ready_document(tmp_path):
    path = tmp_path / "draft.docx"
    path.write_bytes(b"docx")
    update = FakeUpdate("Иванов Иван Иванович")
    context = object()

    with patch(
        "bot.handlers.text_handler.document_template_service.handle_text",
        new=AsyncMock(
            return_value=DocumentResult(
                status="ready",
                message="Документ готов.",
                file_path=path,
                filename="draft.docx",
            )
        ),
    ):
        asyncio.run(handle_text_message(update, context))

    assert update.message.replies == ["Документ готов."]
    assert update.message.documents[0][1] == "draft.docx"
