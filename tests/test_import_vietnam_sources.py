from pathlib import Path

from scripts.import_vietnam_sources import (
    VietnamSource,
    build_indexable_text,
    build_registry_file,
    split_to_sections,
    write_statement_templates,
)
from scripts.process_codexes import parse_codex_file
from bot.services.legal_scope_service import legal_scope_service


def make_source() -> VietnamSource:
    return VietnamSource(
        filename="vn_sample_consumer_law",
        title="Sample Vietnam Consumer Law",
        url="https://example.test/source",
        category="Consumer protection",
        note="test source",
    )


def test_split_to_sections_accepts_vietnam_law_article_variants():
    text = """
    Article 1. This Law regulates consumer rights.
    Article 35a. Online sellers must provide accurate information.
    Article 12/1. A foreigner may submit documents to the competent authority.
    Điều 7. Vietnamese article heading is also accepted.
    """

    sections = split_to_sections(text)

    assert sections == [
        ("1", "This Law regulates consumer rights."),
        ("35a", "Online sellers must provide accurate information."),
        ("12/1", "A foreigner may submit documents to the competent authority."),
        ("7", "Vietnamese article heading is also accepted."),
    ]


def test_build_indexable_text_renumbers_sections_for_existing_parser(tmp_path: Path):
    source = make_source()
    text = """
    Article 35a. Online sellers must provide accurate information.
    Article 36. Consumers may request remedies from the trader.
    """

    output = tmp_path / "vn_sample_consumer_law.txt"
    output.write_text(build_indexable_text(source, text, source.url), encoding="utf-8")

    parsed = parse_codex_file(output, tmp_path)

    assert [article["article_number"] for article in parsed] == ["1", "2"]
    assert parsed[0]["country"] == "vn"
    assert parsed[0]["codex_key"] == "consumer"
    assert "Original section/article: 35a" in parsed[0]["text"]


def test_build_registry_file_lists_imported_and_failed_sources():
    source = make_source()
    failed = VietnamSource(
        filename="vn_failed",
        title="Failed source",
        url="https://example.test/failed",
        category="Other",
    )

    registry = build_registry_file(
        imported=[(source, "https://example.test/resolved", 2)],
        failed=[(failed, "timeout")],
    )

    assert "Vietnam legal sources registry" in registry
    assert "Sample Vietnam Consumer Law" in registry
    assert "sections: 2" in registry
    assert "Failed source" in registry
    assert "timeout" in registry


def test_vietnam_codes_normalize_and_country_is_detected():
    assert legal_scope_service.normalize_codex_key("vn_criminal_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("vn_civil_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("vn_penal_code_2015") == "criminal"
    assert legal_scope_service.normalize_codex_key("vn_tax_administration_law") == "tax"

    scope = legal_scope_service.detect_scope("вьетнам виза и недвижимость для россиянина")
    assert scope["country"] == "vn"


def test_statement_templates_are_parser_compatible(tmp_path: Path):
    write_statement_templates(tmp_path)

    parsed = parse_codex_file(tmp_path / "vn_statement_templates.txt", tmp_path)

    assert len(parsed) == 15
    assert parsed[0]["country"] == "vn"
    assert "Consumer complaint" in parsed[0]["text"]
    assert "E-visa application checklist for a Russian citizen" in parsed[3]["text"]
    assert "Foreign residential property purchase due-diligence checklist" in parsed[8]["text"]
    assert "Russian-specific risk checks" in parsed[8]["text"]
    assert "Embassy / consular support request for Russian citizen" in parsed[14]["text"]
