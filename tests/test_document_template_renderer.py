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
