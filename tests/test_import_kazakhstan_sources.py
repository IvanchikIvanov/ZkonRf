from pathlib import Path

from scripts.import_kazakhstan_sources import (
    KazakhstanSource,
    build_indexable_text,
    build_registry_file,
    split_to_sections,
    write_statement_templates,
)
from scripts.process_codexes import parse_codex_file
from bot.services.legal_scope_service import legal_scope_service


def make_source() -> KazakhstanSource:
    return KazakhstanSource(
        filename="kz_sample_consumer_law",
        title="Sample Kazakhstan Consumer Law",
        url="https://example.test/source",
        category="Consumer protection",
        note="test source",
    )


def test_split_to_sections_accepts_kazakhstan_article_variants():
    text = """
    Article 1. This Law regulates consumer rights.
    Article 35-1. The seller must provide accurate information.
    Article 12/1. A foreigner may submit documents to the competent authority.
    Section 7. A service provider must answer the complaint.
    """

    sections = split_to_sections(text)

    assert sections == [
        ("1", "This Law regulates consumer rights."),
        ("35-1", "The seller must provide accurate information."),
        ("12/1", "A foreigner may submit documents to the competent authority."),
        ("7", "A service provider must answer the complaint."),
    ]


def test_build_indexable_text_renumbers_sections_for_existing_parser(tmp_path: Path):
    source = make_source()
    text = """
    Article 35-1. Online sellers must provide accurate information.
    Article 36. Consumers may request remedies from the trader.
    """

    output = tmp_path / "kz_sample_consumer_law.txt"
    output.write_text(build_indexable_text(source, text, source.url), encoding="utf-8")

    parsed = parse_codex_file(output, tmp_path)

    assert [article["article_number"] for article in parsed] == ["1", "2"]
    assert parsed[0]["country"] == "kz"
    assert parsed[0]["codex_key"] == "consumer"
    assert "Original section/article: 35-1" in parsed[0]["text"]


def test_parser_prefers_section_format_when_adilet_text_contains_cyrillic_article_marker(tmp_path: Path):
    output = tmp_path / "kz_sample_penal_code.txt"
    output.write_text(
        """
        Kazakhstan source: Sample Penal Code
        Note: stray Cyrillic marker Статья appears in Adilet metadata.

        Section 1. Original section/article: 1. Source: Sample Penal Code.
        Criminal law provision one.

        Section 2. Original section/article: 2. Source: Sample Penal Code.
        Criminal law provision two.
        """,
        encoding="utf-8",
    )

    parsed = parse_codex_file(output, tmp_path)

    assert [article["article_number"] for article in parsed] == ["1", "2"]
    assert parsed[0]["country"] == "kz"
    assert parsed[0]["codex_key"] == "criminal"


def test_build_registry_file_lists_imported_and_failed_sources():
    source = make_source()
    failed = KazakhstanSource(
        filename="kz_failed",
        title="Failed source",
        url="https://example.test/failed",
        category="Other",
    )

    registry = build_registry_file(
        imported=[(source, "https://example.test/resolved", 2)],
        failed=[(failed, "timeout")],
    )

    assert "Kazakhstan legal sources registry" in registry
    assert "Sample Kazakhstan Consumer Law" in registry
    assert "sections: 2" in registry
    assert "Failed source" in registry
    assert "timeout" in registry


def test_kazakhstan_codes_normalize_and_country_is_detected():
    assert legal_scope_service.normalize_codex_key("kz_criminal_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("kz_civil_procedure_code") == "procedural"
    assert legal_scope_service.normalize_codex_key("kz_penal_code") == "criminal"
    assert legal_scope_service.normalize_codex_key("kz_tax_code") == "tax"

    scope = legal_scope_service.detect_scope("казахстан виза недвижимость для россиянина")
    assert scope["country"] == "kz"


def test_statement_templates_are_parser_compatible(tmp_path: Path):
    write_statement_templates(tmp_path)

    parsed = parse_codex_file(tmp_path / "kz_statement_templates.txt", tmp_path)

    assert len(parsed) == 15
    assert parsed[0]["country"] == "kz"
    assert "Consumer complaint" in parsed[0]["text"]
    assert "Visa and migration checklist for a Russian citizen" in parsed[3]["text"]
    assert "Foreign real-estate purchase due-diligence checklist" in parsed[8]["text"]
    assert "Russian-specific risk checks" in parsed[8]["text"]
    assert "Consular support request for Russian citizen" in parsed[14]["text"]
