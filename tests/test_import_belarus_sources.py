from pathlib import Path

from scripts.import_belarus_sources import (
    BelarusSource,
    SOURCES,
    build_indexable_text,
    build_registry_file,
    split_to_sections,
    write_statement_templates,
)
from scripts.process_codexes import parse_codex_file
from bot.services.legal_scope_service import legal_scope_service


def make_source() -> BelarusSource:
    return BelarusSource(
        filename="by_sample_consumer_law",
        title="Sample Belarus Consumer Law",
        url="https://example.test/source",
        category="Consumer protection",
        note="test source",
    )


def test_split_to_sections_accepts_belarus_article_variants():
    text = """
    Статья 1. Настоящий Закон регулирует права потребителей.
    Статья 12-1. Продавец обязан предоставить достоверную информацию.
    Статья 35. Иностранный гражданин вправе обратиться в компетентный орган.
    Article 9. Fallback English reference section.
    """

    sections = split_to_sections(text)

    assert sections == [
        ("1", "Настоящий Закон регулирует права потребителей."),
        ("12-1", "Продавец обязан предоставить достоверную информацию."),
        ("35", "Иностранный гражданин вправе обратиться в компетентный орган."),
        ("9", "Fallback English reference section."),
    ]


def test_build_indexable_text_renumbers_sections_for_existing_parser(tmp_path: Path):
    source = make_source()
    text = """
    Статья 12-1. Интернет-продавец обязан предоставить достоверную информацию.
    Статья 13. Потребитель вправе требовать возмещения убытков.
    """

    output = tmp_path / "by_sample_consumer_law.txt"
    output.write_text(build_indexable_text(source, text, source.url), encoding="utf-8")

    parsed = parse_codex_file(output, tmp_path)

    assert [article["article_number"] for article in parsed] == ["1", "2"]
    assert parsed[0]["country"] == "by"
    assert parsed[0]["codex_key"] == "consumer"
    assert "Original section/article: 12-1" in parsed[0]["text"]


def test_build_registry_file_lists_imported_and_failed_sources():
    source = make_source()
    failed = BelarusSource(
        filename="by_failed",
        title="Failed source",
        url="https://example.test/failed",
        category="Other",
    )

    registry = build_registry_file(
        imported=[(source, "https://example.test/resolved", 2)],
        failed=[(failed, "timeout")],
    )

    assert "Belarus legal sources registry" in registry
    assert "Sample Belarus Consumer Law" in registry
    assert "sections: 2" in registry
    assert "Failed source" in registry
    assert "timeout" in registry


def test_belarus_codes_normalize_and_country_is_detected():
    assert legal_scope_service.normalize_codex_key("by_criminal_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("by_civil_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("by_criminal_code") == "criminal"
    assert legal_scope_service.normalize_codex_key("by_tax_code_general_part") == "tax"

    scope = legal_scope_service.detect_scope("беларусь виза недвижимость для россиянина")
    assert scope["country"] == "by"


def test_statement_templates_are_parser_compatible(tmp_path: Path):
    write_statement_templates(tmp_path)

    parsed = parse_codex_file(tmp_path / "by_statement_templates.txt", tmp_path)

    assert len(parsed) == 20
    assert parsed[0]["country"] == "by"
    assert "Consumer complaint" in parsed[0]["text"]
    assert "Visa and migration checklist for a Russian citizen" in parsed[3]["text"]
    assert "Foreign real-estate purchase due-diligence checklist" in parsed[8]["text"]
    assert "Russian-specific risk checks" in parsed[8]["text"]
    assert "Consular support request for Russian citizen" in parsed[14]["text"]
    assert "Marriage / family-status checklist" in parsed[15]["text"]
    assert "Citizenship / passport / statelessness checklist" in parsed[16]["text"]
    assert "Personal data complaint" in parsed[17]["text"]
    assert "Tourism service complaint" in parsed[18]["text"]
    assert "Investment / trade / e-commerce checklist" in parsed[19]["text"]


def test_belarus_source_list_covers_core_and_practical_gaps():
    filenames = {source.filename for source in SOURCES}

    assert "by_constitution" in filenames
    assert "by_civil_code" in filenames
    assert "by_civil_procedure_code" in filenames
    assert "by_criminal_code" in filenames
    assert "by_criminal_procedure_code" in filenames
    assert "by_administrative_offences_code" in filenames
    assert "by_family_code" in filenames
    assert "by_citizenship_law" in filenames
    assert "by_foreigners_legal_status_law" in filenames
    assert "by_external_labour_migration_law" in filenames
    assert "by_consumer_protection_law" in filenames
    assert "by_real_estate_registration_law" in filenames
    assert "by_personal_data_law" in filenames
    assert "by_tourism_law" in filenames
    assert "by_investments_law" in filenames
