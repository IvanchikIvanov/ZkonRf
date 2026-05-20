from pathlib import Path
from tempfile import gettempdir

from bot.services.document_templates.models import DocumentResult, DraftState
from bot.services.document_templates.renderer import render_document
from bot.services.document_templates.templates import get_template, list_templates, match_template
from bot.utils.logger import log

try:
    from bot.services.cache_service import cache_service
except ModuleNotFoundError:
    cache_service = None


class DocumentTemplateService:
    def __init__(self, output_dir: Path | None = None, draft_ttl_seconds: int = 60 * 60 * 24):
        self.output_dir = output_dir or Path(gettempdir()) / "zakonrff_documents"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.draft_ttl_seconds = draft_ttl_seconds
        self._memory_drafts: dict[int, DraftState] = {}

    def _draft_key(self, user_id: int) -> str:
        return f"document_draft:{user_id}"

    async def _load_draft(self, user_id: int) -> DraftState | None:
        cached = await cache_service.get(self._draft_key(user_id)) if cache_service else None
        if cached:
            return DraftState(
                user_id=user_id,
                template_id=cached["template_id"],
                fields=dict(cached.get("fields", {})),
            )
        return self._memory_drafts.get(user_id)

    async def _save_draft(self, draft: DraftState) -> None:
        payload = {"template_id": draft.template_id, "fields": draft.fields}
        saved = await cache_service.set(self._draft_key(draft.user_id), payload, ttl=self.draft_ttl_seconds) if cache_service else False
        if not saved:
            log.warning("Redis unavailable for document drafts; using in-memory fallback")
            self._memory_drafts[draft.user_id] = draft

    async def clear_draft(self, user_id: int) -> None:
        if cache_service:
            await cache_service.delete(self._draft_key(user_id))
        self._memory_drafts.pop(user_id, None)

    def template_list_text(self) -> str:
        lines = ["Доступные шаблоны документов:"]
        for template in list_templates():
            lines.append(f"- {template.title}")
        lines.append("")
        lines.append("Напишите, например: «Составь претензию на возврат денег за товар».")
        return "\n".join(lines)

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
        normalized = text.strip().lower()
        if normalized in {"/cancel_doc", "отмена документа", "отмени документ"}:
            await self.clear_draft(user_id)
            return DocumentResult(status="ask_fields", message="Черновик удален. Можно начать новый документ.")

        draft = await self._load_draft(user_id)
        if draft:
            next_field = self._next_missing_field(draft)
            if not next_field:
                return DocumentResult(status="error", message="Черновик уже заполнен, но документ не был создан.")
            draft.fields[next_field.field_id] = text.strip()
            await self._save_draft(draft)
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

        template = match_template(text)
        if not template:
            return DocumentResult(status="not_document", message="")

        draft = DraftState(user_id=user_id, template_id=template.template_id, fields={"facts": text.strip()})
        await self._save_draft(draft)
        return DocumentResult(status="ask_fields", message=self._ask_message(draft, intro=True))


document_template_service = DocumentTemplateService()
