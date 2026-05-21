"""Import Kyrgyzstan legal sources into bot-indexable text files."""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Iterable

import httpx


DEFAULT_OUTPUT_DIR = Path("data/codexes/kg")
API_BASE = "https://cbd.minjust.gov.kg/api/v1"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/json,application/pdf,application/xhtml+xml,*/*",
}


@dataclass(frozen=True)
class KyrgyzstanSource:
    filename: str
    title: str
    document_code: str
    category: str
    note: str = ""
    alt_urls: tuple[str, ...] = field(default_factory=tuple)

    @property
    def source_url(self) -> str:
        return f"https://cbd.minjust.gov.kg/{self.document_code}/edition/last/ru"


SOURCES: tuple[KyrgyzstanSource, ...] = (
    KyrgyzstanSource("kg_constitution", "Constitution of the Kyrgyz Republic", "1-2", "Core constitutional law", "Current official CBD Minjust text."),
    KyrgyzstanSource("kg_civil_code_part_1", "Civil Code of the Kyrgyz Republic, Part One", "3-1", "Core codes", "Civil-law basis for contracts, obligations, property and damages."),
    KyrgyzstanSource("kg_civil_code_part_2", "Civil Code of the Kyrgyz Republic, Part Two", "3-2", "Core codes", "Specific contracts, sale, lease and other obligations."),
    KyrgyzstanSource("kg_civil_procedure_code", "Civil Procedure Code of the Kyrgyz Republic", "111521", "Procedure", "Civil court procedure and procedural remedies."),
    KyrgyzstanSource("kg_criminal_code", "Criminal Code of the Kyrgyz Republic", "112309", "Core codes", "Criminal liability and offences."),
    KyrgyzstanSource("kg_criminal_procedure_code", "Criminal Procedure Code of the Kyrgyz Republic", "112308", "Procedure", "Criminal complaints, reports and investigation procedure."),
    KyrgyzstanSource("kg_offences_code", "Code of the Kyrgyz Republic on Offences", "112306", "Administrative offences", "Administrative liability, including migration and consumer-related penalties."),
    KyrgyzstanSource("kg_labour_code", "Labour Code of the Kyrgyz Republic", "570", "Labour", "Employment contracts, workers' rights and labour disputes."),
    KyrgyzstanSource("kg_tax_code", "Tax Code of the Kyrgyz Republic", "112340", "Tax", "Tax obligations, administration and taxpayer rights."),
    KyrgyzstanSource("kg_family_code", "Family Code of the Kyrgyz Republic", "1327", "Family", "Marriage, divorce, children, alimony and civil-status context."),
    KyrgyzstanSource("kg_land_code", "Land Code of the Kyrgyz Republic", "3-47", "Land and real estate", "Land rights, land-use rules and land restrictions."),
    KyrgyzstanSource("kg_housing_code", "Housing Code of the Kyrgyz Republic", "203926", "Land and real estate", "Housing rights, residential premises and housing-use rules."),
    KyrgyzstanSource("kg_citizenship_law", "Law on Citizenship of the Kyrgyz Republic", "202103", "Immigration and citizenship", "Citizenship acquisition, termination, passports and citizenship status."),
    KyrgyzstanSource("kg_foreigners_legal_status_law", "Law on Legal Status of Foreign Citizens in the Kyrgyz Republic", "772", "Immigration and visas", "Rights and duties of foreign citizens and stateless persons."),
    KyrgyzstanSource("kg_external_migration_law", "Law on External Migration", "350", "Immigration and visas", "Entry, stay, residence permits, visas and migration quotas."),
    KyrgyzstanSource("kg_external_labour_migration_law", "Law on External Labour Migration", "1792", "Labour", "Foreign labour migration and employment-related migration rules."),
    KyrgyzstanSource("kg_consumer_protection_law", "Law on Protection of Consumer Rights", "590", "Consumer protection", "Consumer complaints, refunds, defects, services and seller duties."),
    KyrgyzstanSource("kg_real_estate_registration_law", "Law on State Registration of Rights to Immovable Property and Transactions", "160", "Land and real estate", "Registration of immovable property rights and transactions."),
    KyrgyzstanSource("kg_real_estate_registration_rules", "Rules for State Registration of Rights and Encumbrances to Immovable Property", "94056", "Land and real estate", "Practical registration rules for immovable property and transactions."),
    KyrgyzstanSource("kg_personal_data_law", "Law on Personal Information", "202269", "Digital services", "Personal data collection, processing, transfer and subject-rights context."),
    KyrgyzstanSource("kg_tourism_law", "Law on Tourism", "201", "Tourism and travel complaints", "Tourism services, tour operators, guides and tourist rights context."),
    KyrgyzstanSource("kg_investments_law", "Law on Investments in the Kyrgyz Republic", "1190", "Business and investment", "Investor rights, investment guarantees and investment activity context."),
    KyrgyzstanSource("kg_ecommerce_law", "Law on Electronic Commerce", "112333", "Digital services", "E-commerce contracts, platforms, sellers and online consumer context."),
    KyrgyzstanSource("kg_advertising_law", "Law on Advertising", "4-5386", "Digital services", "Advertising duties, restrictions and online/offline advertising rules."),
    KyrgyzstanSource("kg_business_companies_law", "Law on Business Partnerships and Companies", "667", "Business and investment", "Company formation, participants, charter capital and governance."),
)


STATEMENT_TEMPLATE_TEXT = """Kyrgyzstan statement and application templates for common bot questions.
These are practical drafting/checklist templates for Russian citizens and other foreigners. They are not official forms unless a competent Kyrgyz authority publishes a specific form.

Section 1. Consumer complaint / demand letter against seller or service provider.
Use for defective goods, refund refusal, misleading service, online order, warranty dispute, delivery problem or paid service failure. Source basis: Consumer Protection Law; Civil Code; E-commerce Law; Advertising Law. Fields: consumer, seller/provider, order/payment, defect or breach, evidence, remedy and deadline.

Section 2. Tourism service complaint.
Use for hotel, tour operator, guide, transport, booking, overcharge or unsafe service problems in Kyrgyzstan. Source basis: Tourism Law; Consumer Protection Law; Civil Code. Fields: tourist identity and itinerary, provider, booking/payment, incident, evidence/witnesses, refund/replacement/compensation demand.

Section 3. Police report for theft, fraud, assault, lost passport or property.
Use when a Russian citizen or foreigner needs a written incident report for police, embassy, insurer or migration authority. Source basis: Criminal Code; Criminal Procedure Code; foreigner-status and migration laws. Fields: applicant, incident date/place, suspect if known, property/value, evidence, request for registration and case reference.

Section 4. Visa and migration checklist for a Russian citizen.
Use before entry, visa/e-visa question, registration, stay extension, temporary residence or residence planning. Source basis: External Migration Law; Law on Legal Status of Foreign Citizens; Citizenship Law. Russian-specific notes: verify visa-free/EAEU practice, registration deadlines, permitted stay, residence grounds and employment conditions separately.

Section 5. Visa / stay application or correction request.
Use for visa, invitation, migration-registration error, missing document or authority/portal question. Source basis: External Migration Law; offences procedure; appeal practice. Fields: application/registration number, passport, incorrect field, host/inviting party, attachments and evidence.

Section 6. Temporary or permanent residence checklist.
Use for longer stay, family, study, work, investment/business or residence status questions. Source basis: External Migration Law; Law on Legal Status of Foreign Citizens; Citizenship Law. Fields: current stay, residence ground, address, income/work/study documents, medical/criminal-record items if required.

Section 7. Work / employment checklist for foreigner or Russian citizen.
Use for employment contract, work authorization, employer documents or labour dispute. Source basis: Labour Code; External Labour Migration Law; External Migration Law. Fields: worker status, employer, contract terms, authorization issue, wages/dismissal/safety/migration risk and evidence.

Section 8. Administrative offence / fine response.
Use for migration, traffic, consumer, public-order or other offence notices. Source basis: Code on Offences; Criminal Procedure Code where relevant. Fields: person, protocol, authority and article, facts, objections, mitigating circumstances, requested action.

Section 9. Foreign real-estate purchase due-diligence checklist.
Use for apartment, house, land, lease, new-build, registration or seller/developer due diligence. Source basis: Civil Code; Land Code; Housing Code; real-estate registration law and rules. Russian-specific risk checks: foreign ownership and land limits, payment route from Russia, notarization/registration duty, tax and banking risk.

Section 10. Real-estate registration / correction request.
Use for registration of ownership, correction of registry error, encumbrance removal or transaction registration. Source basis: Law on State Registration of Rights to Immovable Property; registration rules; Civil Code. Fields: applicant, property identifier, requested action, basis document, attachments and payment proof.

Section 11. Civil claim / pre-trial demand.
Use for contract debt, damage, service failure, unjust enrichment, property dispute or compensation. Source basis: Civil Code; Civil Procedure Code. Fields: claimant/respondent, legal basis, timeline, amount, evidence, voluntary settlement demand.

Section 12. Tax / payment-residency checklist.
Use for tax registration, income, rental income, business income, VAT, customs/payment questions. Source basis: Tax Code; Civil Code; Investments Law. Fields: person/entity, residency facts, transaction, amounts/currency, Kyrgyz-source indicators and documents.

Section 13. Digital service / e-commerce / advertising complaint.
Use for online store, platform, electronic contract, misleading ad, blocked account or digital-service issue. Source basis: E-commerce Law; Advertising Law; Personal Information Law; Consumer Protection Law. Fields: platform, account/order/ad, screenshots, payment proof, requested correction/refund/restoration/removal.

Section 14. Appeal to Kyrgyz state body.
Use for administrative request, complaint against official action/inaction, request for information or deadline issue. Source basis: Constitution; relevant administrative and sectoral laws. Fields: applicant, authority, facts, previous applications, legal interest, requested action, attachments.

Section 15. Consular support request for Russian citizen.
Use for lost passport, detention, accident, death, emergency travel document, migration problem or document legalization. Source basis: External Migration Law; Criminal Procedure Code; foreigner-status law. Fields: Russian citizen identity, location, emergency facts, authority involved, needed support.

Section 16. Marriage / family-status checklist.
Use for marriage registration, divorce, child issues, alimony, civil-status certificates or spouse consent. Source basis: Family Code; Civil Code. Fields: parties, citizenship, passports, addresses, event, foreign documents, legalization/translation and competent body.

Section 17. Citizenship / passport / statelessness checklist.
Use for Kyrgyz citizenship, loss/termination, child citizenship, passport/documentation question or statelessness. Source basis: Citizenship Law; Constitution; foreigner-status law. Fields: citizenship history, birthplace, parents, marriage, residence, requested result, evidence and risk flags.

Section 18. Personal data complaint.
Use for unlawful data collection, publication, refusal to correct/delete data, transfer issue or platform leak. Source basis: Personal Information Law; digital-service and offence context. Fields: data subject, operator/controller, data categories, violation, evidence, access/correction/deletion/restriction demand.

Section 19. Tourism service complaint / insurance checklist.
Use for package tour, hotel, guide, transport, accident, denied service or tourist insurance issue. Source basis: Tourism Law; Consumer Protection Law; Civil Code. Fields: tourist/booking data, provider, breach/loss/incident, evidence, medical/insurance documents and remedy.

Section 20. Investment / permits / e-commerce checklist.
Use for foreign investment, company participation, online trade, advertising, permits, real estate or commercial dispute. Source basis: Investments Law; Business Partnerships and Companies Law; E-commerce Law; Tax Code. Fields: investor/business participant, transaction, company/permit/registration checks, tax/currency/payment and beneficial-owner risks.
"""


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|section|article)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_text(text)


def extract_pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)
    return normalize_text("\n\n".join(pages))


def response_to_text(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        data = response.json()
        return strip_html(data.get("contentRu") or data.get("contentKyr") or "")
    if "pdf" in content_type or response.url.path.lower().endswith(".pdf"):
        return extract_pdf_text(response.content)
    return strip_html(response.text)


def fetch_source(source: KyrgyzstanSource, timeout: float = 45.0) -> tuple[str, str]:
    last_error: Exception | None = None
    with httpx.Client(follow_redirects=True, headers=REQUEST_HEADERS, timeout=timeout) as client:
        try:
            document_response = client.get(
                f"{API_BASE}/GetDocument",
                params={"DocumentCode": source.document_code, "lang": "ru"},
            )
            document_response.raise_for_status()
            document = document_response.json()
            editions = document.get("editions") or []
            if not editions:
                raise ValueError("document has no editions")
            edition_id = editions[-1]["id"]
            edition_response = client.get(
                f"{API_BASE}/GetEdition",
                params={"editionId": edition_id, "lang": "ru"},
            )
            edition_response.raise_for_status()
            text = response_to_text(edition_response)
            if len(text) < 500:
                raise ValueError(f"downloaded text is too short ({len(text)} chars)")
            return text, f"https://cbd.minjust.gov.kg/{source.document_code}/edition/{edition_id}/ru"
        except Exception as exc:
            last_error = exc

    for url in source.alt_urls:
        try:
            response = httpx.get(url, follow_redirects=True, headers=REQUEST_HEADERS, timeout=timeout)
            text = response_to_text(response)
            if len(text) < 500:
                raise ValueError(f"downloaded text is too short ({len(text)} chars)")
            return text, str(response.url)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"failed to fetch {source.filename}: {last_error}")


def split_to_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"(?is)(?<![A-Za-zА-Яа-я])(?:"
        r"(?:Статья|СТАТЬЯ|Section|SECTION|Article|ARTICLE)\s+"
        r"([0-9]+(?:[-/][0-9]+)?(?:[a-zа-я])?)"
        r"|([0-9]+(?:[-/][0-9]+)?(?:[a-zа-я])?)\s*[-–]?\s*берене"
        r")\.?\s*"
    )
    matches = list(pattern.finditer(text))
    sections: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = normalize_text(text[start:end])
        if len(body) >= 20:
            sections.append((normalize_text(match.group(1) or match.group(2)), body))

    if sections:
        return sections

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if len(paragraph.strip()) >= 120]
    if not paragraphs:
        return [("1", text)]

    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        if current and current_len + len(paragraph) > 3200:
            chunks.append((str(len(chunks) + 1), "\n\n".join(current)))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += len(paragraph)
    if current:
        chunks.append((str(len(chunks) + 1), "\n\n".join(current)))
    return chunks


def build_indexable_text(source: KyrgyzstanSource, text: str, resolved_url: str) -> str:
    sections = split_to_sections(text)
    blocks = [
        f"Kyrgyzstan source: {source.title}",
        f"Category: {source.category}",
        f"Source URL: {resolved_url}",
        f"Note: {source.note or 'Reference text; verify against current official Kyrgyz text.'}",
        "",
    ]
    for index, (original_section, body) in enumerate(sections, start=1):
        blocks.append(
            f"Section {index}. Original section/article: {original_section}. "
            f"Source: {source.title}.\n{body}"
        )
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def build_registry_file(
    imported: Iterable[tuple[KyrgyzstanSource, str, int]],
    failed: Iterable[tuple[KyrgyzstanSource, str]],
) -> str:
    imported_list = list(imported)
    failed_list = list(failed)
    lines = [
        f"Kyrgyzstan legal sources registry ({date.today().isoformat()})",
        "Primary source is the Centralized Database of Legal Information of the Kyrgyz Republic.",
        "Verify current legal force against official Kyrgyz/Russian text before filing or court use.",
        "",
        "Imported sources:",
    ]
    for source, resolved_url, section_count in imported_list:
        lines.extend(
            [
                f"- {source.title}",
                f"  file: {source.filename}.txt",
                f"  category: {source.category}",
                f"  sections: {section_count}",
                f"  url: {resolved_url}",
                f"  note: {source.note or 'Reference text.'}",
            ]
        )

    lines.append("")
    lines.append("Failed sources:")
    if failed_list:
        for source, error in failed_list:
            lines.extend([f"- {source.title}", f"  url: {source.source_url}", f"  error: {error}"])
    else:
        lines.append("- none")

    return "\n".join(lines).strip() + "\n"


def write_statement_templates(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "kg_statement_templates.txt").write_text(STATEMENT_TEMPLATE_TEXT, encoding="utf-8")


def import_sources(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    imported: list[tuple[KyrgyzstanSource, str, int]] = []
    failed: list[tuple[KyrgyzstanSource, str]] = []

    for source in SOURCES:
        try:
            text, resolved_url = fetch_source(source)
            indexable_text = build_indexable_text(source, text, resolved_url)
            (output_dir / f"{source.filename}.txt").write_text(indexable_text, encoding="utf-8")
            imported.append((source, resolved_url, len(split_to_sections(text))))
            print(f"imported {source.filename}")
            time.sleep(0.4)
        except Exception as exc:  # pragma: no cover - exercised by integration run
            failed.append((source, str(exc)))
            print(f"failed {source.filename}: {exc}")
            time.sleep(0.4)

    registry = build_registry_file(imported, failed)
    (output_dir / "kg_sources_registry_2026.txt").write_text(registry, encoding="utf-8")
    write_statement_templates(output_dir)
    return len(imported), len(failed)


if __name__ == "__main__":
    imported_count, failed_count = import_sources()
    print(f"Done: imported={imported_count}, failed={failed_count}")
