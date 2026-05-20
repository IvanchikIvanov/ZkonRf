import asyncio

from bot.services.document_templates.templates import get_template, match_template
from bot.services.document_template_service import DocumentTemplateService


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


def test_start_document_flow_asks_for_missing_fields(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    result = asyncio.run(service.handle_text(42, "Составь претензию на возврат денег за телефон"))

    assert result.status == "ask_fields"
    assert "Сделаю документ" in result.message
    assert "ФИО" in result.message


def test_active_draft_collects_plain_field_input(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    asyncio.run(service.handle_text(42, "Составь претензию на возврат денег за телефон"))
    result = asyncio.run(service.handle_text(42, "Иванов Иван Иванович"))

    assert result.status == "ask_fields"
    assert "Адрес" in result.message


def test_service_renders_file_when_required_fields_complete(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    result = asyncio.run(service.handle_text(42, "Составь претензию на возврат денег за телефон"))
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
        result = asyncio.run(service.handle_text(42, value))

    assert result.status == "ready"
    assert result.file_path is not None
    assert result.file_path.exists()


def test_cancel_draft(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    asyncio.run(service.handle_text(42, "Составь претензию на возврат денег"))
    result = asyncio.run(service.handle_text(42, "/cancel_doc"))

    assert result.status == "ask_fields"
    assert "Черновик удален" in result.message


def test_template_list_mentions_all_first_release_templates(tmp_path):
    service = DocumentTemplateService(output_dir=tmp_path)

    text = service.template_list_text()

    assert "Претензия продавцу" in text
    assert "Роспотребнадзор" in text
    assert "Исковое заявление" in text
