# Document Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Telegram bot support for guided legal document drafts and `.docx` file delivery.

**Architecture:** Add a focused document-template service that detects document requests, manages per-user draft state, asks for missing fields, renders deterministic `.docx` files, and lets `text_handler` short-circuit normal RAG when a document flow is active. Draft state uses Redis through the existing cache service, with an in-memory fallback for local/degraded operation.

**Tech Stack:** Python, python-telegram-bot, python-docx, Redis cache service, pytest.

---

## File Structure

- Create `bot/services/document_templates/__init__.py`: package export.
- Create `bot/services/document_templates/models.py`: dataclasses for template fields, template definitions, draft state, and service responses.
- Create `bot/services/document_templates/templates.py`: seven deterministic template definitions and keyword rules.
- Create `bot/services/document_templates/renderer.py`: `.docx` rendering with `python-docx`.
- Create `bot/services/document_template_service.py`: high-level orchestration, draft state storage, intent detection, field collection, and file generation.
- Modify `bot/handlers/text_handler.py`: call the document service before normal validation/RAG and send generated `.docx` files.
- Create `tests/test_document_template_service.py`: service-level tests.
- Create `tests/test_document_template_renderer.py`: renderer smoke tests.
- Create `tests/test_text_handler_document_templates.py`: handler short-circuit tests.

---

### Task 1: Add Test Harness

**Files:**
- Create: `tests/conftest.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create pytest config**

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
pythonpath = .
```

- [ ] **Step 2: Create minimal test fixtures**

Create `tests/conftest.py`:

```python
import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:test-token")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("DATABASE_PATH", "data/embeddings")
```

- [ ] **Step 3: Run test discovery**

Run: `pytest --collect-only`

Expected: pytest exits 0 and reports no tests yet, or only existing tests if the repository gained any meanwhile.

- [ ] **Step 4: Commit**

```bash
git add pytest.ini tests/conftest.py
git commit -m "test: add pytest harness"
```

---

### Task 2: Define Template Models and Templates

**Files:**
- Create: `bot/services/document_templates/models.py`
- Create: `bot/services/document_templates/templates.py`
- Create: `bot/services/document_templates/__init__.py`
- Test: `tests/test_document_template_service.py`

- [ ] **Step 1: Write failing tests for template selection and required fields**

Create `tests/test_document_template_service.py`:

```python
from bot.services.document_templates.templates import (
    get_template,
    match_template,
)


def test_match_refund_claim_template():
    template = match_template("Составь претензию на возврат денег за телефон")

    assert template is not None
    assert template.template_id == "seller_refund_claim"


def test_match_rospotrebnadzor_complaint_template():
    template = match_template("Нужна жалоба в Роспотребнадзор на магазин")

    assert template is not None
    assert template.template_id == "rospotrebnadzor_complaint"


def test_lawsuit_template_has_court_fields():
    template = get_template("consumer_lawsuit")

    field_ids = [field.field_id for field in template.required_fields]
    assert "court_name" in field_ids
    assert "defendant_name" in field_ids
    assert "claim_amount" in field_ids
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_document_template_service.py -v`

Expected: FAIL with missing module `bot.services.document_templates`.

- [ ] **Step 3: Create model dataclasses**

Create `bot/services/document_templates/models.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class TemplateField:
    field_id: str
    label: str
    prompt: str
    required: bool = True


@dataclass(frozen=True)
class DocumentTemplate:
    template_id: str
    title: str
    keywords: tuple[str, ...]
    required_fields: tuple[TemplateField, ...]
    optional_fields: tuple[TemplateField, ...] = ()
    filename_prefix: str = "document"


@dataclass
class DraftState:
    user_id: int
    template_id: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentResult:
    status: Literal["not_document", "ask_fields", "ready", "error"]
    message: str
    file_path: Path | None = None
    filename: str | None = None
```

- [ ] **Step 4: Create template definitions**

Create `bot/services/document_templates/templates.py`:

```python
from bot.services.document_templates.models import DocumentTemplate, TemplateField


COMMON_FIELDS = (
    TemplateField("user_full_name", "ФИО", "Укажите ваше ФИО."),
    TemplateField("user_address", "Адрес", "Укажите ваш адрес."),
    TemplateField("user_contact", "Телефон или email", "Укажите телефон или email для связи."),
    TemplateField("recipient_name", "Получатель", "Кому адресовать документ? Укажите название организации или ФИО."),
    TemplateField("recipient_address", "Адрес получателя", "Укажите адрес получателя, если знаете."),
    TemplateField("event_date", "Дата события", "Укажите дату покупки, услуги или события."),
    TemplateField("amount", "Сумма", "Укажите сумму покупки, услуги или спорную сумму."),
    TemplateField("facts", "Что произошло", "Кратко опишите, что произошло."),
    TemplateField("demand", "Требование", "Что вы хотите потребовать? Например: вернуть деньги, устранить недостатки, прекратить звонки."),
)


EVIDENCE_FIELD = TemplateField(
    "evidence",
    "Доказательства",
    "Какие есть доказательства? Например: чек, договор, фото, переписка.",
    required=False,
)


TEMPLATES = {
    "seller_refund_claim": DocumentTemplate(
        template_id="seller_refund_claim",
        title="Претензия продавцу на возврат денег за товар",
        keywords=("претензи", "возврат", "товар", "продавц", "магазин", "деньг"),
        required_fields=COMMON_FIELDS,
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="pretenziya_prodavcu",
    ),
    "poor_service_claim": DocumentTemplate(
        template_id="poor_service_claim",
        title="Претензия на некачественную услугу",
        keywords=("претензи", "услуг", "некачествен", "работ", "исполнитель"),
        required_fields=COMMON_FIELDS,
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="pretenziya_usluga",
    ),
    "rospotrebnadzor_complaint": DocumentTemplate(
        template_id="rospotrebnadzor_complaint",
        title="Жалоба в Роспотребнадзор",
        keywords=("жалоб", "роспотребнадзор", "провер", "нарушен"),
        required_fields=COMMON_FIELDS,
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="zhaloba_rospotrebnadzor",
    ),
    "consumer_lawsuit": DocumentTemplate(
        template_id="consumer_lawsuit",
        title="Исковое заявление по защите прав потребителя",
        keywords=("иск", "суд", "исков", "заявлен", "ответчик"),
        required_fields=COMMON_FIELDS
        + (
            TemplateField("court_name", "Суд", "Укажите наименование суда."),
            TemplateField("defendant_name", "Ответчик", "Укажите ответчика."),
            TemplateField("claim_amount", "Цена иска", "Укажите цену иска."),
            TemplateField("pretrial_claim", "Досудебная претензия", "Досудебная претензия направлялась? Если да, когда?"),
        ),
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="isk_zpp",
    ),
    "bank_mfo_collector_claim": DocumentTemplate(
        template_id="bank_mfo_collector_claim",
        title="Заявление в банк, МФО или коллекторам",
        keywords=("банк", "мфо", "коллектор", "кредит", "займ", "списан", "звон"),
        required_fields=COMMON_FIELDS
        + (
            TemplateField("contract_number", "Номер договора", "Укажите номер договора или займа, если знаете."),
            TemplateField("disputed_amount", "Спорная сумма", "Укажите спорную сумму."),
        ),
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="zayavlenie_bank_mfo",
    ),
    "transport_complaint": DocumentTemplate(
        template_id="transport_complaint",
        title="Жалоба на авиаперевозчика или РЖД",
        keywords=("авиа", "самолет", "рейс", "ржд", "поезд", "перевозчик", "багаж", "билет"),
        required_fields=COMMON_FIELDS,
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="zhaloba_perevozchik",
    ),
    "education_refund_claim": DocumentTemplate(
        template_id="education_refund_claim",
        title="Заявление о возврате денег за онлайн-курс или обучение",
        keywords=("курс", "обучен", "онлайн", "школ", "образован", "возврат"),
        required_fields=COMMON_FIELDS,
        optional_fields=(EVIDENCE_FIELD,),
        filename_prefix="vozvrat_obuchenie",
    ),
}


def get_template(template_id: str) -> DocumentTemplate:
    return TEMPLATES[template_id]


def list_templates() -> tuple[DocumentTemplate, ...]:
    return tuple(TEMPLATES.values())


def match_template(text: str) -> DocumentTemplate | None:
    normalized = text.lower()
    best_template = None
    best_score = 0

    for template in TEMPLATES.values():
        score = sum(1 for keyword in template.keywords if keyword in normalized)
        if score > best_score:
            best_template = template
            best_score = score

    return best_template if best_score > 0 else None
```

- [ ] **Step 5: Export package**

Create `bot/services/document_templates/__init__.py`:

```python
from bot.services.document_templates.models import (
    DocumentResult,
    DocumentTemplate,
    DraftState,
    TemplateField,
)

__all__ = [
    "DocumentResult",
    "DocumentTemplate",
    "DraftState",
    "TemplateField",
]
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_document_template_service.py -v`

Expected: PASS for 3 tests.

- [ ] **Step 7: Commit**

```bash
git add bot/services/document_templates tests/test_document_template_service.py
git commit -m "feat: define document templates"
```

---

### Task 3: Add Draft State and Field Collection Service

**Files:**
- Create: `bot/services/document_template_service.py`
- Modify: `tests/test_document_template_service.py`

- [ ] **Step 1: Add failing tests for draft start and continuation**

Append to `tests/test_document_template_service.py`:

```python
import pytest

from bot.services.document_template_service import DocumentTemplateService


@pytest.mark.asyncio
async def test_start_document_flow_asks_for_missing_fields(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    result = await service.handle_text(42, "Составь претензию на возврат денег за телефон")

    assert result.status == "ask_fields"
    assert "Сделаю документ" in result.message
    assert "ФИО" in result.message


@pytest.mark.asyncio
async def test_active_draft_collects_plain_field_input(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    await service.handle_text(42, "Составь претензию на возврат денег за телефон")
    result = await service.handle_text(42, "Иванов Иван Иванович")

    assert result.status == "ask_fields"
    assert "Адрес" in result.message
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_document_template_service.py -v`

Expected: FAIL with missing `bot.services.document_template_service`.

- [ ] **Step 3: Implement service skeleton and in-memory fallback**

Create `bot/services/document_template_service.py`:

```python
from pathlib import Path
from tempfile import gettempdir

from bot.services.cache_service import cache_service
from bot.services.document_templates.models import DocumentResult, DraftState
from bot.services.document_templates.templates import get_template, match_template
from bot.utils.logger import log


class DocumentTemplateService:
    def __init__(self, output_dir: Path | None = None, draft_ttl_seconds: int = 60 * 60 * 24):
        self.output_dir = output_dir or Path(gettempdir()) / "zakonrff_documents"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.draft_ttl_seconds = draft_ttl_seconds
        self._memory_drafts: dict[int, DraftState] = {}

    def _draft_key(self, user_id: int) -> str:
        return f"document_draft:{user_id}"

    async def _load_draft(self, user_id: int) -> DraftState | None:
        cached = await cache_service.get(self._draft_key(user_id))
        if cached:
            return DraftState(
                user_id=user_id,
                template_id=cached["template_id"],
                fields=dict(cached.get("fields", {})),
            )
        return self._memory_drafts.get(user_id)

    async def _save_draft(self, draft: DraftState) -> None:
        payload = {"template_id": draft.template_id, "fields": draft.fields}
        saved = await cache_service.set(self._draft_key(draft.user_id), payload, ttl=self.draft_ttl_seconds)
        if not saved:
            log.warning("Redis unavailable for document drafts; using in-memory fallback")
            self._memory_drafts[draft.user_id] = draft

    async def clear_draft(self, user_id: int) -> None:
        await cache_service.delete(self._draft_key(user_id))
        self._memory_drafts.pop(user_id, None)

    def _missing_required_field_ids(self, draft: DraftState) -> list[str]:
        template = get_template(draft.template_id)
        return [field.field_id for field in template.required_fields if not draft.fields.get(field.field_id)]

    def _next_missing_field(self, draft: DraftState):
        template = get_template(draft.template_id)
        missing = set(self._missing_required_field_ids(draft))
        for field in template.required_fields:
            if field.field_id in missing:
                return field
        return None

    def _ask_message(self, draft: DraftState, intro: bool = False) -> str:
        template = get_template(draft.template_id)
        next_field = self._next_missing_field(draft)
        prefix = f"Сделаю документ: {template.title}.\n\n" if intro else ""
        if not next_field:
            return prefix + "Все обязательные данные заполнены."
        return prefix + f"Уточните поле «{next_field.label}».\n{next_field.prompt}"

    async def handle_text(self, user_id: int, text: str) -> DocumentResult:
        draft = await self._load_draft(user_id)
        if draft:
            next_field = self._next_missing_field(draft)
            if not next_field:
                return DocumentResult(status="error", message="Черновик уже заполнен, но документ не был создан.")
            draft.fields[next_field.field_id] = text.strip()
            await self._save_draft(draft)
            if self._missing_required_field_ids(draft):
                return DocumentResult(status="ask_fields", message=self._ask_message(draft))
            return DocumentResult(status="ready", message="Данные собраны. Документ можно сформировать.")

        template = match_template(text)
        if not template:
            return DocumentResult(status="not_document", message="")

        draft = DraftState(user_id=user_id, template_id=template.template_id, fields={"facts": text.strip()})
        await self._save_draft(draft)
        return DocumentResult(status="ask_fields", message=self._ask_message(draft, intro=True))


document_template_service = DocumentTemplateService()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_document_template_service.py -v`

Expected: PASS for all service tests.

- [ ] **Step 5: Commit**

```bash
git add bot/services/document_template_service.py tests/test_document_template_service.py
git commit -m "feat: manage document draft state"
```

---

### Task 4: Render `.docx` Files

**Files:**
- Create: `bot/services/document_templates/renderer.py`
- Modify: `bot/services/document_template_service.py`
- Create: `tests/test_document_template_renderer.py`
- Modify: `tests/test_document_template_service.py`

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_document_template_renderer.py`:

```python
from docx import Document

from bot.services.document_templates.models import DraftState
from bot.services.document_templates.renderer import render_document


def test_render_document_creates_docx(tmp_path):
    draft = DraftState(
        user_id=42,
        template_id="seller_refund_claim",
        fields={
            "user_full_name": "Иванов Иван Иванович",
            "user_address": "г. Москва, ул. Тестовая, д. 1",
            "user_contact": "+7 900 000-00-00",
            "recipient_name": "ООО Ромашка",
            "recipient_address": "г. Москва, ул. Магазинная, д. 2",
            "event_date": "10 мая 2026",
            "amount": "50 000 руб.",
            "facts": "Телефон сломался через неделю после покупки.",
            "demand": "Вернуть деньги.",
        },
    )

    path = render_document(draft, tmp_path)

    assert path.exists()
    assert path.suffix == ".docx"
    text = "\n".join(p.text for p in Document(str(path)).paragraphs)
    assert "ПРЕТЕНЗИЯ" in text
    assert "Иванов Иван Иванович" in text
    assert "ООО Ромашка" in text
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_document_template_renderer.py -v`

Expected: FAIL with missing renderer module.

- [ ] **Step 3: Implement renderer**

Create `bot/services/document_templates/renderer.py`:

```python
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from bot.services.document_templates.models import DraftState
from bot.services.document_templates.templates import get_template


HEADINGS = {
    "seller_refund_claim": "ПРЕТЕНЗИЯ\nо возврате денежных средств за товар",
    "poor_service_claim": "ПРЕТЕНЗИЯ\nпо договору оказания услуг",
    "rospotrebnadzor_complaint": "ЖАЛОБА\nо нарушении прав потребителя",
    "consumer_lawsuit": "ИСКОВОЕ ЗАЯВЛЕНИЕ\nо защите прав потребителя",
    "bank_mfo_collector_claim": "ЗАЯВЛЕНИЕ\nо защите прав заемщика/потребителя финансовых услуг",
    "transport_complaint": "ЖАЛОБА\nна нарушение прав пассажира",
    "education_refund_claim": "ЗАЯВЛЕНИЕ\nо возврате денежных средств за обучение",
}


def _value(draft: DraftState, field_id: str, default: str = "") -> str:
    return draft.fields.get(field_id, default).strip()


def _add_paragraph(document: Document, text: str, bold: bool = False, center: bool = False) -> None:
    paragraph = document.add_paragraph()
    if center:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.bold = bold


def render_document(draft: DraftState, output_dir: Path) -> Path:
    template = get_template(draft.template_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    document = Document()
    _add_paragraph(document, f"Кому: {_value(draft, 'recipient_name')}", bold=True)
    if _value(draft, "recipient_address"):
        _add_paragraph(document, f"Адрес: {_value(draft, 'recipient_address')}")
    _add_paragraph(document, f"От: {_value(draft, 'user_full_name')}", bold=True)
    _add_paragraph(document, f"Адрес: {_value(draft, 'user_address')}")
    _add_paragraph(document, f"Контакт: {_value(draft, 'user_contact')}")
    document.add_paragraph()

    _add_paragraph(document, HEADINGS.get(draft.template_id, template.title).upper(), bold=True, center=True)
    document.add_paragraph()

    _add_paragraph(document, f"Дата события: {_value(draft, 'event_date')}")
    if _value(draft, "amount"):
        _add_paragraph(document, f"Сумма: {_value(draft, 'amount')}")

    if draft.template_id == "consumer_lawsuit":
        _add_paragraph(document, f"Суд: {_value(draft, 'court_name')}")
        _add_paragraph(document, f"Ответчик: {_value(draft, 'defendant_name')}")
        _add_paragraph(document, f"Цена иска: {_value(draft, 'claim_amount')}")
        _add_paragraph(document, f"Досудебная претензия: {_value(draft, 'pretrial_claim')}")

    if draft.template_id == "bank_mfo_collector_claim":
        _add_paragraph(document, f"Номер договора/займа: {_value(draft, 'contract_number')}")
        _add_paragraph(document, f"Спорная сумма: {_value(draft, 'disputed_amount')}")

    document.add_paragraph()
    _add_paragraph(document, "Обстоятельства", bold=True)
    _add_paragraph(document, _value(draft, "facts"))

    document.add_paragraph()
    _add_paragraph(document, "Требования", bold=True)
    _add_paragraph(document, _value(draft, "demand"))

    if _value(draft, "evidence"):
        document.add_paragraph()
        _add_paragraph(document, "Доказательства", bold=True)
        _add_paragraph(document, _value(draft, "evidence"))

    document.add_paragraph()
    _add_paragraph(document, "Приложения: копии подтверждающих документов при наличии.")
    _add_paragraph(document, "Дата: ____________________")
    _add_paragraph(document, "Подпись: ____________________")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{template.filename_prefix}_{draft.user_id}_{timestamp}.docx"
    path = output_dir / filename
    document.save(str(path))
    return path
```

- [ ] **Step 4: Wire renderer into service**

In `bot/services/document_template_service.py`, import renderer:

```python
from bot.services.document_templates.renderer import render_document
```

Replace the final ready branch in `handle_text` with:

```python
            if self._missing_required_field_ids(draft):
                return DocumentResult(status="ask_fields", message=self._ask_message(draft))
            file_path = render_document(draft, self.output_dir)
            await self.clear_draft(user_id)
            return DocumentResult(
                status="ready",
                message="Документ готов. Проверьте данные и при необходимости покажите документ юристу перед подачей.",
                file_path=file_path,
                filename=file_path.name,
            )
```

- [ ] **Step 5: Add service ready test**

Append to `tests/test_document_template_service.py`:

```python
@pytest.mark.asyncio
async def test_service_renders_file_when_required_fields_complete(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    result = await service.handle_text(42, "Составь претензию на возврат денег за телефон")
    assert result.status == "ask_fields"

    for value in [
        "Иванов Иван Иванович",
        "г. Москва, ул. Тестовая, д. 1",
        "+7 900 000-00-00",
        "ООО Ромашка",
        "г. Москва, ул. Магазинная, д. 2",
        "10 мая 2026",
        "50 000 руб.",
        "Вернуть деньги.",
    ]:
        result = await service.handle_text(42, value)

    assert result.status == "ready"
    assert result.file_path is not None
    assert result.file_path.exists()
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_document_template_service.py tests/test_document_template_renderer.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add bot/services/document_templates/renderer.py bot/services/document_template_service.py tests/test_document_template_service.py tests/test_document_template_renderer.py
git commit -m "feat: render legal document drafts"
```

---

### Task 5: Integrate With Telegram Text Handler

**Files:**
- Modify: `bot/handlers/text_handler.py`
- Create: `tests/test_text_handler_document_templates.py`

- [ ] **Step 1: Write failing handler test**

Create `tests/test_text_handler_document_templates.py`:

```python
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.mark.asyncio
async def test_text_handler_starts_document_flow_before_rag():
    update = FakeUpdate("Составь претензию на возврат денег")
    context = object()

    with patch(
        "bot.handlers.text_handler.document_template_service.handle_text",
        new=AsyncMock(return_value=DocumentResult(status="ask_fields", message="Укажите ФИО.")),
    ), patch(
        "bot.handlers.text_handler.embeddings_service.generate_embedding",
        new=AsyncMock(side_effect=AssertionError("RAG should not run")),
    ):
        await handle_text_message(update, context)

    assert update.message.replies == ["Укажите ФИО."]


@pytest.mark.asyncio
async def test_text_handler_sends_ready_document(tmp_path):
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
        await handle_text_message(update, context)

    assert update.message.replies == ["Документ готов."]
    assert update.message.documents[0][1] == "draft.docx"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_text_handler_document_templates.py -v`

Expected: FAIL because `text_handler` does not import or call `document_template_service`.

- [ ] **Step 3: Import service in text handler**

In `bot/handlers/text_handler.py`, add:

```python
from bot.services.document_template_service import document_template_service
```

- [ ] **Step 4: Add document short-circuit near the top of `handle_text_message`**

After `question = message.text.strip()` and the empty-question guard, add:

```python
        document_result = await document_template_service.handle_text(user_id, question)
        if document_result.status != "not_document":
            await message.reply_text(document_result.message)
            if document_result.status == "ready" and document_result.file_path:
                with open(document_result.file_path, "rb") as document_file:
                    await message.reply_document(
                        document=document_file,
                        filename=document_result.filename or document_result.file_path.name,
                        caption="Файл создан как черновик. Проверьте данные перед подачей.",
                    )
            return
```

- [ ] **Step 5: Run handler tests**

Run: `pytest tests/test_text_handler_document_templates.py -v`

Expected: PASS.

- [ ] **Step 6: Run service and renderer tests**

Run: `pytest tests/test_document_template_service.py tests/test_document_template_renderer.py tests/test_text_handler_document_templates.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add bot/handlers/text_handler.py tests/test_text_handler_document_templates.py
git commit -m "feat: send document drafts from text handler"
```

---

### Task 6: Add Cancel and Template List Commands

**Files:**
- Modify: `bot/services/document_template_service.py`
- Modify: `bot/handlers/text_handler.py`
- Modify: `bot/main.py`
- Modify: `tests/test_document_template_service.py`

- [ ] **Step 1: Add failing tests for cancel and template list**

Append to `tests/test_document_template_service.py`:

```python
@pytest.mark.asyncio
async def test_cancel_draft(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    await service.handle_text(42, "Составь претензию на возврат денег")
    result = await service.handle_text(42, "/cancel_doc")

    assert result.status == "ask_fields"
    assert "Черновик удален" in result.message


def test_template_list_mentions_all_first_release_templates(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    text = service.template_list_text()

    assert "Претензия продавцу" in text
    assert "Роспотребнадзор" in text
    assert "Исковое заявление" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_document_template_service.py -v`

Expected: FAIL because cancel and list methods do not exist.

- [ ] **Step 3: Add methods to service**

In `bot/services/document_template_service.py`, import `list_templates`:

```python
from bot.services.document_templates.templates import get_template, list_templates, match_template
```

Add inside `DocumentTemplateService`:

```python
    def template_list_text(self) -> str:
        lines = ["Доступные шаблоны документов:"]
        for template in list_templates():
            lines.append(f"- {template.title}")
        lines.append("")
        lines.append("Напишите, например: «Составь претензию на возврат денег за товар».")
        return "\n".join(lines)
```

Add at the start of `handle_text`:

```python
        if text.strip().lower() in {"/cancel_doc", "отмена документа", "отмени документ"}:
            await self.clear_draft(user_id)
            return DocumentResult(status="ask_fields", message="Черновик удален. Можно начать новый документ.")
```

- [ ] **Step 4: Add command handlers**

In `bot/handlers/text_handler.py`, add:

```python
async def handle_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(document_template_service.template_list_text())


async def handle_cancel_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    result = await document_template_service.handle_text(user_id, "/cancel_doc")
    await update.message.reply_text(result.message)
```

In `bot/main.py`, import:

```python
    handle_templates,
    handle_cancel_doc,
```

Register:

```python
    application.add_handler(CommandHandler("templates", handle_templates))
    application.add_handler(CommandHandler("cancel_doc", handle_cancel_doc))
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_document_template_service.py tests/test_text_handler_document_templates.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bot/services/document_template_service.py bot/handlers/text_handler.py bot/main.py tests/test_document_template_service.py
git commit -m "feat: add document template commands"
```

---

### Task 7: Final Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest tests/test_document_template_service.py tests/test_document_template_renderer.py tests/test_text_handler_document_templates.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Compile changed Python files**

Run:

```bash
python -m py_compile bot/services/document_template_service.py bot/services/document_templates/models.py bot/services/document_templates/templates.py bot/services/document_templates/renderer.py bot/handlers/text_handler.py bot/main.py
```

Expected: exit code 0.

- [ ] **Step 3: Manual smoke test with bot disabled**

Run a local script in PowerShell:

```powershell
@'
import asyncio
from pathlib import Path
from bot.services.document_template_service import DocumentTemplateService

async def main():
    service = DocumentTemplateService(output_dir=Path("C:/tmp/zakonrff-doc-smoke"))
    result = await service.handle_text(123, "Составь претензию на возврат денег за телефон")
    print(result.status, result.message[:80])
    for value in [
        "Иванов Иван Иванович",
        "г. Москва, ул. Тестовая, д. 1",
        "+7 900 000-00-00",
        "ООО Ромашка",
        "г. Москва, ул. Магазинная, д. 2",
        "10 мая 2026",
        "50 000 руб.",
        "Вернуть деньги",
    ]:
        result = await service.handle_text(123, value)
    print(result.status)
    print(result.file_path)

asyncio.run(main())
'@ | python -
```

Expected: prints `ready` and an existing `.docx` path under `C:/tmp/zakonrff-doc-smoke`.

- [ ] **Step 4: Check git status**

Run: `git status --short`

Expected: only intended document-template files and existing unrelated user changes are present.

- [ ] **Step 5: Commit final verification updates if any**

Only if verification required small fixes:

```bash
git add bot tests docs
git commit -m "fix: polish document template flow"
```

---

## Self-Review

Spec coverage:

- Detect document-generation intent: Task 2 and Task 3.
- Choose template: Task 2.
- Ask missing fields: Task 3.
- Store draft session: Task 3.
- Generate `.docx`: Task 4.
- Send file through Telegram: Task 5.
- Redis with fallback: Task 3.
- Error and cancel behavior: Task 6.
- Tests: Tasks 1 through 7.

Placeholder scan:

- No placeholder markers remain.
- Every code-touching task includes exact files, code, commands, and expected results.

Type consistency:

- `DocumentResult.status` values are consistently `not_document`, `ask_fields`, `ready`, and `error`.
- `DraftState`, `DocumentTemplate`, and `TemplateField` names match across models, templates, renderer, and service tasks.
