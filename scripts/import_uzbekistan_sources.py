"""Import Uzbekistan legal sources into bot-indexable text files."""
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


DEFAULT_OUTPUT_DIR = Path("data/codexes/uz")
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*",
}


@dataclass(frozen=True)
class UzbekistanSource:
    filename: str
    title: str
    url: str
    category: str
    note: str = ""
    alt_urls: tuple[str, ...] = field(default_factory=tuple)


def lex_url(doc_id: int | str, lang: str = "docs") -> str:
    return f"https://lex.uz/{lang}/{doc_id}"


SOURCES: tuple[UzbekistanSource, ...] = (
    UzbekistanSource(
        filename="uz_constitution",
        title="Constitution of the Republic of Uzbekistan",
        url=lex_url(6451070),
        category="Core constitutional law",
        note="Official LexUz page; English tab is marked as unofficial translation.",
        alt_urls=(lex_url(6445147),),
    ),
    UzbekistanSource(
        filename="uz_civil_code_part_1",
        title="Civil Code of the Republic of Uzbekistan, Part One",
        url=lex_url(111181),
        category="Core codes",
        note="Contracts, property, obligations and civil-law remedies.",
    ),
    UzbekistanSource(
        filename="uz_civil_code_part_2",
        title="Civil Code of the Republic of Uzbekistan, Part Two",
        url=lex_url(180550),
        category="Core codes",
        note="Special part of civil law, including specific contracts and IP context.",
    ),
    UzbekistanSource(
        filename="uz_civil_procedure_code",
        title="Civil Procedure Code of the Republic of Uzbekistan",
        url=lex_url(3517334),
        category="Procedure",
        note="Civil court procedure and procedural remedies.",
    ),
    UzbekistanSource(
        filename="uz_criminal_code",
        title="Criminal Code of the Republic of Uzbekistan",
        url=lex_url(111457),
        category="Core codes",
        note="Criminal liability and offences.",
    ),
    UzbekistanSource(
        filename="uz_criminal_procedure_code",
        title="Criminal Procedure Code of the Republic of Uzbekistan",
        url=lex_url(111463),
        category="Procedure",
        note="Criminal complaints, reports and investigation procedure.",
    ),
    UzbekistanSource(
        filename="uz_administrative_responsibility_code",
        title="Code of Administrative Responsibility of the Republic of Uzbekistan",
        url=lex_url(97661),
        category="Administrative offences",
        note="Administrative liability, including migration and consumer-related penalties.",
    ),
    UzbekistanSource(
        filename="uz_labour_code",
        title="Labour Code of the Republic of Uzbekistan",
        url=lex_url(6257291, "ru/docs"),
        category="Labour",
        note="Employment contracts, workers' rights and labour disputes.",
        alt_urls=(lex_url(6229963),),
    ),
    UzbekistanSource(
        filename="uz_tax_code",
        title="Tax Code of the Republic of Uzbekistan",
        url=lex_url(4674893, "ru/docs"),
        category="Tax",
        note="Tax obligations, administration and taxpayer rights.",
    ),
    UzbekistanSource(
        filename="uz_family_code",
        title="Family Code of the Republic of Uzbekistan",
        url=lex_url(104723),
        category="Family",
        note="Marriage, divorce, children, alimony and civil-status context.",
    ),
    UzbekistanSource(
        filename="uz_land_code",
        title="Land Code of the Republic of Uzbekistan",
        url=lex_url(149947),
        category="Land and real estate",
        note="Land rights, land-use rules and land restrictions.",
    ),
    UzbekistanSource(
        filename="uz_housing_code",
        title="Housing Code of the Republic of Uzbekistan",
        url=lex_url(106134),
        category="Land and real estate",
        note="Housing rights, residential premises and housing-use rules.",
    ),
    UzbekistanSource(
        filename="uz_citizenship_law",
        title="Law on Citizenship of the Republic of Uzbekistan",
        url=lex_url(4761986),
        category="Immigration and citizenship",
        note="Citizenship acquisition, termination, passports and citizenship status.",
    ),
    UzbekistanSource(
        filename="uz_foreigners_legal_status_law",
        title="Law on Legal Status of Foreign Citizens and Stateless Persons",
        url=lex_url(5443901),
        category="Immigration and visas",
        note="Entry, stay, residence, registration and rights of foreigners.",
    ),
    UzbekistanSource(
        filename="uz_consumer_protection_law",
        title="Law on Protection of Consumer Rights",
        url="https://www.lex.uz/acts/14643",
        category="Consumer protection",
        note="Consumer complaints, refunds, defects, services and seller duties.",
        alt_urls=(lex_url(14643),),
    ),
    UzbekistanSource(
        filename="uz_real_estate_registration_law",
        title="Law on State Registration of Rights to Immovable Property",
        url=lex_url(6297080, "ru/docs"),
        category="Land and real estate",
        note="Registration of immovable property rights and related transactions.",
    ),
    UzbekistanSource(
        filename="uz_personal_data_law",
        title="Law on Personal Data",
        url=lex_url(4396428),
        category="Digital services",
        note="Personal data processing, localization, consent, subject rights and complaints.",
    ),
    UzbekistanSource(
        filename="uz_tourism_law",
        title="Law on Tourism",
        url=lex_url(4428101),
        category="Tourism and travel complaints",
        note="Tourism services, tour operators, guides and tourist rights context.",
    ),
    UzbekistanSource(
        filename="uz_investments_law",
        title="Law on Investments and Investment Activity",
        url=lex_url(4664144, "ru/docs"),
        category="Business and investment",
        note="Investor rights, investment guarantees and investment activity context.",
        alt_urls=(lex_url(4664142),),
    ),
    UzbekistanSource(
        filename="uz_ecommerce_law",
        title="Law on Electronic Commerce",
        url=lex_url(6213428, "ru/docs"),
        category="Digital services",
        note="E-commerce contracts, platforms, sellers and online consumer context.",
    ),
    UzbekistanSource(
        filename="uz_advertising_law",
        title="Law on Advertising",
        url=lex_url(6052633, "ru/docs"),
        category="Digital services",
        note="Advertising duties, restrictions and online/offline advertising rules.",
    ),
    UzbekistanSource(
        filename="uz_entrepreneurship_guarantees_law",
        title="Law on Guarantees of Freedom of Entrepreneurial Activity",
        url=lex_url(2006777),
        category="Business and investment",
        note="Business rights, state guarantees and entrepreneur protections.",
    ),
    UzbekistanSource(
        filename="uz_llc_law",
        title="Law on Limited and Additional Liability Companies",
        url=lex_url(18793),
        category="Business and investment",
        note="Company formation, participants, charter capital and governance.",
    ),
    UzbekistanSource(
        filename="uz_notariat_law",
        title="Law on Notariat",
        url=lex_url(57043),
        category="Land and real estate",
        note="Notarial actions, useful for real-estate and power-of-attorney questions.",
    ),
    UzbekistanSource(
        filename="uz_appeals_law",
        title="Law on Appeals of Individuals and Legal Entities",
        url=lex_url(3336169),
        category="Administrative complaints",
        note="Administrative complaint/request format, deadlines and competent bodies.",
    ),
)


STATEMENT_TEMPLATE_TEXT = """Uzbekistan statement and application templates for common bot questions.
These are practical drafting/checklist templates for Russian citizens and other foreigners. They are not official forms unless a competent Uzbekistan authority publishes a specific form.

Section 1. Consumer complaint / demand letter against seller or service provider.
Use for defective goods, refund refusal, misleading service, online order, warranty dispute, delivery problem or paid service failure.
Source basis: Consumer Protection Law; Civil Code; E-commerce Law; Advertising Law.
Template fields: consumer identity and contacts; seller/service provider; order and payment details; defect or breach; evidence; refund, replacement, repair, compensation or written-response demand.

Section 2. Tourism service complaint.
Use for hotel, tour operator, guide, transport, booking, overcharge or unsafe service problems in Uzbekistan.
Source basis: Tourism Law; Consumer Protection Law; Civil Code.
Template fields: tourist identity, passport and itinerary; provider; booking/payment; incident; evidence/witnesses; requested refund, replacement service, compensation or authority complaint.

Section 3. Police report for theft, fraud, assault, lost passport or property.
Use when a Russian citizen or foreigner needs a written incident report for police, embassy, insurer or migration authority.
Source basis: Criminal Code; Criminal Procedure Code; Law on Legal Status of Foreign Citizens and Stateless Persons.
Template fields: applicant; incident date/place; suspect if known; property/value; evidence; requested registration, case reference and copy for embassy/insurer.

Section 4. Visa and migration checklist for a Russian citizen.
Use before entry, visa/e-visa question, registration, stay extension, temporary residence or residence planning.
Source basis: Law on Legal Status of Foreign Citizens and Stateless Persons; Constitution; citizenship and passport context.
Template fields: passport; arrival/departure and address; host; purpose; entry/stay basis; registration duty; residence/work/study grounds.
Russian-specific notes: Russian citizens may have simplified practical entry/stay routes compared with visa nationals, but registration, permitted-stay, residence and employment conditions still need separate checks.

Section 5. Visa / stay application or correction request.
Use for visa, invitation, registration error, missing document or authority/portal question.
Source basis: Law on Legal Status of Foreign Citizens and Stateless Persons; Appeals Law; administrative liability rules.
Template fields: application or registration number; applicant passport; incorrect or missing field; host/inviting party; attachments and payment/portal evidence.

Section 6. Temporary or permanent residence checklist.
Use for longer stay, family, study, work, investment/business or residence status questions.
Source basis: Law on Legal Status of Foreign Citizens and Stateless Persons; Citizenship Law; Constitution.
Template fields: current stay deadline; residence ground; address and housing proof; income/work/study documents; medical/criminal-record/insurance items if required; prior entries and offences.

Section 7. Work / employment checklist for foreigner or Russian citizen.
Use for employment contract, work authorization, employer documents or labour dispute.
Source basis: Labour Code; Law on Legal Status of Foreign Citizens and Stateless Persons.
Template fields: worker citizenship and status; employer; contract terms; permit/authorization issue if any; wages, dismissal, safety or migration risk; evidence.

Section 8. Administrative offence / fine response.
Use for migration, traffic, consumer, public-order or other administrative offence notices.
Source basis: Code of Administrative Responsibility; procedural rules; Appeals Law.
Template fields: person; protocol/notice; authority and article; facts and objections; mitigating circumstances; request to terminate, reclassify, reduce fine, restore deadline or provide copies.

Section 9. Foreign real-estate purchase due-diligence checklist.
Use for apartment, house, land, lease, new-build, registration or seller/developer due diligence.
Source basis: Civil Code; Land Code; Housing Code; Law on State Registration of Rights to Immovable Property; Notariat Law.
Template fields: buyer citizenship/passport/marital status; property and cadastral data; seller/developer title; encumbrances; contract price and payment route; notary/registration steps.
Russian-specific risk checks: verify foreign ownership restrictions, land-right limits, payment/banking route from Russia, notarization and registration duty, tax/residency consequences, sanctions/bank compliance risk.

Section 10. Real-estate registration / correction request.
Use for registration of ownership, correction of registry error, encumbrance removal or transaction registration.
Source basis: Law on State Registration of Rights to Immovable Property; Civil Code; Notariat Law.
Template fields: applicant and representative; property identifier; requested registration/correction/removal; basis document; attachments and payment proof.

Section 11. Civil claim / pre-trial demand.
Use for contract debt, damage, service failure, unjust enrichment, property dispute or compensation.
Source basis: Civil Code; Civil Procedure Code.
Template fields: claimant/respondent; contract/legal basis; timeline; amount and calculation; evidence; voluntary settlement demand and deadline.

Section 12. Tax / payment-residency checklist.
Use for tax registration, income, rental income, business income, VAT, customs/payment questions.
Source basis: Tax Code; Civil Code; Investments Law.
Template fields: person/entity and residency facts; income or transaction type; amounts/currency; Uzbekistan-source indicators; contracts, invoices, bank statements and notices.

Section 13. Digital service / e-commerce / advertising complaint.
Use for online store, platform, electronic contract, misleading ad, blocked account or digital-service issue.
Source basis: E-commerce Law; Advertising Law; Personal Data Law; Consumer Protection Law.
Template fields: platform/service; account/order/ad details; issue; screenshots/logs/emails/payment proof; requested correction, refund, account restoration, ad removal or record preservation.

Section 14. Appeal to Uzbekistan state body.
Use for administrative request, complaint against official action/inaction, request for information or deadline issue.
Source basis: Appeals Law; Constitution.
Template fields: applicant; authority/addressee; facts and previous applications; legal interest; requested action; attachments and preferred response channel.

Section 15. Consular support request for Russian citizen.
Use for lost passport, detention, accident, death, emergency travel document, migration problem or document legalization.
Source basis: Law on Legal Status of Foreign Citizens and Stateless Persons; Criminal Procedure Code; citizenship/passport context.
Template fields: Russian citizen identity; location and emergency facts; Uzbekistan authority involved; needed support; attachments and contact person.

Section 16. Marriage / family-status checklist.
Use for marriage registration, divorce, child issues, alimony, civil-status certificates or spouse consent.
Source basis: Family Code; Civil Code; Appeals Law.
Template fields: parties, citizenship, passports and addresses; event; foreign documents; legalization/translation; competent body; Russian-specific marital-status and passport documents.

Section 17. Citizenship / passport / statelessness checklist.
Use for Uzbekistan citizenship, loss/termination, child citizenship, passport/documentation question or statelessness.
Source basis: Citizenship Law; Constitution; Law on Legal Status of Foreign Citizens and Stateless Persons.
Template fields: citizenship history; birthplace/parents/marriage/residence; existing foreign citizenship; requested result; evidence and risk flags.

Section 18. Personal data complaint.
Use for unlawful data collection, publication, refusal to correct/delete data, localization issue or platform leak.
Source basis: Personal Data Law; Information/digital-service context; administrative liability context.
Template fields: data subject; operator/controller; data categories; violation; evidence; demand for access, correction, deletion, restriction, explanation or authority complaint.

Section 19. Tourism service complaint / insurance checklist.
Use for package tour, hotel, guide, transport, accident, denied service or tourist insurance issue.
Source basis: Tourism Law; Consumer Protection Law; Civil Code.
Template fields: tourist and booking data; provider; breach/loss/incident; evidence and medical/insurance documents; remedy and authority complaint.

Section 20. Investment / permits / e-commerce checklist.
Use for foreign investment, LLC/business participation, online trade, advertising, permits, real estate or commercial dispute.
Source basis: Investments Law; Entrepreneurship Guarantees Law; LLC Law; E-commerce Law; Tax Code.
Template fields: investor/business participant and citizenship/residence; transaction; company/permit/registration checks; tax, currency/payment and beneficial-owner risk checks; documents and correspondence.
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
    url_path = response.url.path.lower()
    if "pdf" in content_type or url_path.endswith(".pdf"):
        return extract_pdf_text(response.content)
    return strip_html(response.text)


def fetch_source(source: UzbekistanSource, timeout: float = 45.0) -> tuple[str, str]:
    urls = (source.url, *source.alt_urls)
    last_error: Exception | None = None

    for url in urls:
        for verify in (True, False):
            try:
                with httpx.Client(
                    follow_redirects=True,
                    headers=REQUEST_HEADERS,
                    timeout=timeout,
                    verify=verify,
                ) as client:
                    response = client.get(url)

                text = response_to_text(response)
                if response.is_error and len(text) < 500:
                    response.raise_for_status()
                if "404" in text[:500] and "Страница не найдена" in text[:1000]:
                    raise ValueError("official page returned 404")
                if len(text) < 500:
                    raise ValueError(f"downloaded text is too short ({len(text)} chars)")
                return text, str(response.url)
            except Exception as exc:  # pragma: no cover - exercised by integration run
                last_error = exc

    raise RuntimeError(f"failed to fetch {source.filename}: {last_error}")


def split_to_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"(?is)(?<![A-Za-zА-Яа-я])(?:"
        r"(?:Статья|СТАТЬЯ|Section|SECTION|Article|ARTICLE)\s+"
        r"([0-9]+(?:[-/][0-9]+)?(?:[a-zа-я])?)"
        r"|([0-9]+(?:[-/][0-9]+)?(?:[a-zа-я])?)\s*[-–]?\s*модда"
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


def build_indexable_text(source: UzbekistanSource, text: str, resolved_url: str) -> str:
    sections = split_to_sections(text)
    blocks = [
        f"Uzbekistan source: {source.title}",
        f"Category: {source.category}",
        f"Source URL: {resolved_url}",
        f"Note: {source.note or 'Reference text; verify against current official Uzbekistan text.'}",
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
    imported: Iterable[tuple[UzbekistanSource, str, int]],
    failed: Iterable[tuple[UzbekistanSource, str]],
) -> str:
    imported_list = list(imported)
    failed_list = list(failed)
    lines = [
        f"Uzbekistan legal sources registry ({date.today().isoformat()})",
        "Primary source is LexUz, the National Database of Legislation of the Republic of Uzbekistan.",
        "Verify current legal force against official Uzbekistan text before filing or court use.",
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
            lines.extend([f"- {source.title}", f"  url: {source.url}", f"  error: {error}"])
    else:
        lines.append("- none")

    return "\n".join(lines).strip() + "\n"


def write_statement_templates(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "uz_statement_templates.txt").write_text(STATEMENT_TEMPLATE_TEXT, encoding="utf-8")


def import_sources(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    imported: list[tuple[UzbekistanSource, str, int]] = []
    failed: list[tuple[UzbekistanSource, str]] = []

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
    (output_dir / "uz_sources_registry_2026.txt").write_text(registry, encoding="utf-8")
    write_statement_templates(output_dir)
    return len(imported), len(failed)


if __name__ == "__main__":
    imported_count, failed_count = import_sources()
    print(f"Done: imported={imported_count}, failed={failed_count}")
