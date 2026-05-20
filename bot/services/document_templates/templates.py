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
