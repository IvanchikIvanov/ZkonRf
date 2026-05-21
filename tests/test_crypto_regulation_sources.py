from pathlib import Path

from scripts.process_codexes import parse_codex_file


COUNTRY_FILES = {
    "ru": "ru_crypto_regulation.txt",
    "thai": "thai_crypto_regulation.txt",
    "vn": "vn_crypto_regulation.txt",
    "kz": "kz_crypto_regulation.txt",
    "by": "by_crypto_regulation.txt",
    "uz": "uz_crypto_regulation.txt",
    "kg": "kg_crypto_regulation.txt",
}


def test_crypto_regulation_files_exist_for_each_country():
    codexes_dir = Path("data/codexes")

    for country, filename in COUNTRY_FILES.items():
        path = codexes_dir / country / filename
        assert path.exists(), f"missing crypto regulation source for {country}"


def test_crypto_regulation_files_are_parser_compatible():
    codexes_dir = Path("data/codexes")

    for country, filename in COUNTRY_FILES.items():
        path = codexes_dir / country / filename
        parsed = parse_codex_file(path, codexes_dir)

        assert len(parsed) >= 5
        assert {article["country"] for article in parsed} == {country}
        joined = " ".join(article["text"].lower() for article in parsed)
        assert "crypto" in joined or "digital asset" in joined or "token" in joined
        assert "source:" in path.read_text(encoding="utf-8").lower()
