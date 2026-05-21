from pathlib import Path

from scripts.import_thailand_sources import (
    ThailandSource,
    build_indexable_text,
    build_registry_file,
    split_to_sections,
    write_statement_templates,
)
from scripts.process_codexes import parse_codex_file
from bot.services.legal_scope_service import legal_scope_service


def make_source() -> ThailandSource:
    return ThailandSource(
        filename="thai_sample_consumer_act",
        title="Sample Thailand Consumer Act",
        url="https://example.test/source",
        category="Consumer protection",
        note="test source",
    )


def test_split_to_sections_accepts_thai_law_section_suffixes():
    text = """
    Section 1. This Act is called the Sample Act.
    Section 35 bis. Controlled contracts must protect consumers from unfair terms.
    Article 12/1. A person may file a complaint with the competent authority.
    """

    sections = split_to_sections(text)

    assert sections == [
        ("1", "This Act is called the Sample Act."),
        ("35 bis", "Controlled contracts must protect consumers from unfair terms."),
        ("12/1", "A person may file a complaint with the competent authority."),
    ]


def test_build_indexable_text_renumbers_sections_for_existing_parser(tmp_path: Path):
    source = make_source()
    text = """
    Section 35 bis. Controlled contracts must protect consumers from unfair terms.
    Section 35 ter. Missing required terms are treated as included by law.
    """

    output = tmp_path / "thai_sample_consumer_act.txt"
    output.write_text(build_indexable_text(source, text, source.url), encoding="utf-8")

    parsed = parse_codex_file(output, tmp_path)

    assert [article["article_number"] for article in parsed] == ["1", "2"]
    assert parsed[0]["country"] == "thai"
    assert parsed[0]["codex_key"] == "consumer"
    assert "Original section/article: 35 bis" in parsed[0]["text"]


def test_build_registry_file_lists_imported_and_failed_sources():
    source = make_source()
    failed = ThailandSource(
        filename="thai_failed",
        title="Failed source",
        url="https://example.test/failed",
        category="Other",
    )

    registry = build_registry_file(
        imported=[(source, "https://example.test/resolved", 2)],
        failed=[(failed, "timeout")],
    )

    assert "Thailand legal sources registry" in registry
    assert "Sample Thailand Consumer Act" in registry
    assert "sections: 2" in registry
    assert "Failed source" in registry
    assert "timeout" in registry


def test_thailand_procedure_codes_normalize_as_procedural():
    assert legal_scope_service.normalize_codex_key("thai_criminal_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("thai_civil_procedure_overview") == "procedural"
    assert legal_scope_service.normalize_codex_key("thai_civil_commercial_code_part_1") == "civil"
    assert legal_scope_service.normalize_codex_key("thai_revenue_code_income_tax") == "tax"


def test_statement_templates_are_parser_compatible(tmp_path: Path):
    write_statement_templates(tmp_path)

    parsed = parse_codex_file(tmp_path / "thai_statement_templates.txt", tmp_path)

    assert len(parsed) == 13
    assert parsed[0]["country"] == "thai"
    assert "Consumer complaint to the Office of the Consumer Protection Board" in parsed[0]["text"]
    assert "Tourist Police report" in parsed[2]["text"]
    assert "Visa application checklist for a Russian citizen" in parsed[5]["text"]
    assert "Foreign condominium purchase due-diligence checklist" in parsed[10]["text"]
    assert "Russian-specific risk checks" in parsed[10]["text"]
