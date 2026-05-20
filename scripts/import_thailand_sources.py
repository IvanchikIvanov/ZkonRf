"""Import Thailand legal sources into bot-indexable text files."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Iterable

import httpx


DEFAULT_OUTPUT_DIR = Path("data/codexes/thai")
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*",
}


@dataclass(frozen=True)
class ThailandSource:
    filename: str
    title: str
    url: str
    category: str
    note: str = ""
    alt_urls: tuple[str, ...] = field(default_factory=tuple)


SOURCES: tuple[ThailandSource, ...] = (
    ThailandSource(
        filename="thai_penal_code",
        title="Thailand Criminal/Penal Code B.E. 2499 (1956)",
        url="https://www.icnl.org/wp-content/uploads/Thailand_CrimCodeThai.pdf",
        category="Core codes",
        note="English reference translation hosted by ICNL.",
    ),
    ThailandSource(
        filename="thai_criminal_procedure_code",
        title="Thailand Criminal Procedure Code B.E. 2477 (1934), updated 2008",
        url="https://www.icj.org/wp-content/uploads/2012/12/Thailand-Criminal-Procedure-Code-1934-2008-eng.pdf",
        category="Core codes",
        note="English full text hosted by the International Commission of Jurists.",
    ),
    ThailandSource(
        filename="thai_civil_commercial_code_part_1",
        title="Thailand Civil and Commercial Code, part I",
        url="https://www.samuiforsale.com/law-texts/thailand-civil-code-part-1.html",
        category="Core codes",
        note="English reference translation; official Thai text prevails.",
        alt_urls=("https://www.icnl.org/wp-content/uploads/thaicivthai.pdf",),
    ),
    ThailandSource(
        filename="thai_civil_commercial_code_part_2",
        title="Thailand Civil and Commercial Code, part II",
        url="https://www.samuiforsale.com/law-texts/thailand-civil-code-part-2.html",
        category="Core codes",
        note="English reference translation; official Thai text prevails.",
    ),
    ThailandSource(
        filename="thai_civil_commercial_code_part_3",
        title="Thailand Civil and Commercial Code, part III",
        url="https://www.samuiforsale.com/law-texts/thailand-civil-code-part-3.html",
        category="Core codes",
        note="English reference translation; official Thai text prevails.",
    ),
    ThailandSource(
        filename="thai_civil_procedure_overview",
        title="Thailand civil procedure guide, Thai/English court reference",
        url="https://hrm.m-society.go.th/wp-content/uploads/2021/08/%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%94%E0%B8%B3%E0%B9%80%E0%B8%99%E0%B8%B4%E0%B8%99%E0%B8%84%E0%B8%94%E0%B8%B5%E0%B9%81%E0%B8%9E%E0%B9%88%E0%B8%87-%E0%B8%89%E0%B8%9A%E0%B8%B1%E0%B8%9A%E0%B9%84%E0%B8%97%E0%B8%A2-%E0%B8%AD%E0%B8%B1%E0%B8%87%E0%B8%81%E0%B8%A4%E0%B8%A9.pdf",
        category="Procedure",
        note="Court-oriented Thai/English civil procedure reference.",
    ),
    ThailandSource(
        filename="thai_consumer_protection_act",
        title="Consumer Protection Act B.E. 2522 (1979)",
        url="https://www.wipo.int/wipolex/en/legislation/details/6820",
        category="Consumer protection",
        note="WIPO Lex page with English full text and PDF link.",
    ),
    ThailandSource(
        filename="thai_product_liability_act",
        title="Liability for Damages Arising from Unsafe Products Act B.E. 2551 (2008)",
        url="https://www.thailawforum.com/laws/Liability%20for%20Damages%20Arising%20from%20Unsafe%20Products%20Act.pdf",
        category="Consumer protection",
        note="English reference translation.",
        alt_urls=("https://thailawforum.com/database1/Thailand-Product-Liability-Act-2.html",),
    ),
    ThailandSource(
        filename="thai_unfair_contract_terms_act",
        title="Unfair Contract Terms Act B.E. 2540 (1997)",
        url="https://www.samuiforsale.com/law-texts/unfair-contract-terms-act.html",
        category="Consumer protection",
        note="English reference translation.",
    ),
    ThailandSource(
        filename="thai_trade_competition_act",
        title="Trade Competition Act B.E. 2560 (2017)",
        url="https://www.asean-competition.org/file/pdf_file/Thailand%20Trade%20Competition%20Act%202017.pdf",
        category="Commerce",
        note="English unofficial translation distributed through ASEAN Competition.",
        alt_urls=("https://law.dit.go.th/Upload/Document/2b20e8bf-0178-46e4-9b2e-4903de67891f.pdf",),
    ),
    ThailandSource(
        filename="thai_electronic_transactions_act",
        title="Electronic Transactions Act B.E. 2544 (2001)",
        url="https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2551/EngPDF/25510316.pdf",
        category="Digital services",
        note="English unofficial translation hosted by Bank of Thailand.",
    ),
    ThailandSource(
        filename="thai_personal_data_protection_act",
        title="Personal Data Protection Act B.E. 2562 (2019)",
        url="https://data.opendevelopmentmekong.net/dataset/78c90118-6671-4c19-afe1-7bfbace4d46a/resource/ec616be5-9fbf-4071-b4b5-cb1f3e46e826/download/entranslation_of_the_personal_data_protection_act_0.pdf",
        category="Digital services",
        note="English version; Open Development Thailand identifies Office of the Council of State as issuing agency.",
    ),
    ThailandSource(
        filename="thai_ocpb_complaint_portal",
        title="Office of the Consumer Protection Board online complaint portal",
        url="https://complaint.ocpb.go.th/",
        category="Complaint templates",
        note="Official OCPB consumer complaint portal and practical filing channel.",
    ),
    ThailandSource(
        filename="thai_tourism_complaint_product_services",
        title="Tourism Authority of Thailand complaint: product and services",
        url="https://complaint-center.tourismthailand.org/en/p/complaint-about-product-and-services",
        category="Complaint templates",
        note="Official tourism complaint category page referencing OCPB for consumer/product/service complaints.",
    ),
    ThailandSource(
        filename="thai_tourism_complaint_robbery_fraud",
        title="Tourism Authority of Thailand complaint: robbery, pickpocketing, assault, fraud",
        url="https://complaint-center.tourismthailand.org/en/p/complaint-about-robbery",
        category="Complaint templates",
        note="Official tourism complaint category page referencing Tourist Police contacts.",
    ),
    ThailandSource(
        filename="thai_tourism_complaint_tour_agency",
        title="Tourism Authority of Thailand complaint: tour agency, travel company, tour guide",
        url="https://complaint-center.tourismthailand.org/en/p/complaint-about-a-tour-agency",
        category="Complaint templates",
        note="Official tourism complaint category page referencing Department of Tourism contacts.",
    ),
    ThailandSource(
        filename="thai_tourism_complaint_tourist_damage",
        title="Tourism Authority of Thailand complaint: tourist damage and tourism safety",
        url="https://complaint-center.tourismthailand.org/en/p/complaint-about-tourist-suffer-damage",
        category="Complaint templates",
        note="Official tourism complaint category page referencing Tourism Safety and Security Standards Bureau.",
    ),
    ThailandSource(
        filename="thai_tourism_complaint_transportation",
        title="Tourism Authority of Thailand complaint: transportation, taxi, bus, minibus",
        url="https://complaint-center.tourismthailand.org/en/p/other-complaints",
        category="Complaint templates",
        note="Official tourism complaint category page referencing Department of Land Transport complaint contacts.",
    ),
)


STATEMENT_TEMPLATE_TEXT = """Thailand practical statement templates for bot drafting
Source basis:
- OCPB online complaint system: https://complaint.ocpb.go.th/
- OCPB help/FAQ: https://complaint.ocpb.go.th/help
- TAT complaint center: https://complaint-center.tourismthailand.org/en
- Tourist Police Bureau: https://www.touristpolice.go.th/en/main

These are drafting templates derived from official complaint intake fields and complaint-category pages.
They are not court forms and must be reviewed before filing.

Section 1. Consumer complaint to the Office of the Consumer Protection Board (OCPB).
Use for purchased goods, services, restaurants, entertainment venues, shops, non-standard products or services.
Recipient: Office of the Consumer Protection Board.
Channels: OCPB online complaint system https://complaint.ocpb.go.th/, hotline 1166, Line @ocpbconnect, provincial complaint channels.
Template fields:
1. Complainant: full name, passport or ID number, date of birth, mobile phone, email, current address for contact.
2. Respondent/business: company/shop/person name, address or online platform, phone/email/website/social account if known.
3. Transaction: product or service, date, place or website, order/reservation number, amount paid in THB, payment method.
4. Facts: chronological description of purchase, defect/non-performance/misrepresentation, attempts to contact the business, responses received.
5. Evidence: receipts, contract, warranty, chat records, photos/videos, delivery documents, bank or card proof, advertisement or label.
6. Requested remedy: refund, replacement, repair, cancellation, compensation amount, correction of advertisement/label, inspection of operator.
7. Fasttrack consent if offered: whether the complaint may be forwarded directly to a participating business.

Draft wording:
I request the Office of the Consumer Protection Board to accept this consumer complaint, review the attached evidence, contact the business, and assist with the remedy described above. I confirm that the facts and documents submitted are true to the best of my knowledge.

Section 2. Tourism product or service complaint.
Use for tourism-related product/service issues, restaurants, entertainment venues, purchased goods, shops, or non-standard services.
Recipient: Tourism Complaint and Suggestion Coordination Centre / responsible agency indicated by TAT; for consumer goods/services, OCPB may be the responsible agency.
Template fields:
1. Tourist/complainant details: full name, nationality, passport number, phone, email, address or accommodation.
2. Business/provider details: name, location, booking/order number, guide/driver/staff name if known.
3. Incident details: date, time, place, service/product, amount paid, what was promised and what happened.
4. Harm/damage: financial loss, safety issue, health issue, delay, denial of service, property damage.
5. Evidence and witnesses.
6. Requested action: refund, compensation, investigation, warning, referral to competent agency, written response.

Section 3. Tourist Police report for robbery, pickpocketing, assault, fraud, or similar incident.
Recipient: Tourist Police Bureau.
Contacts referenced by TAT pages include call center 1155 and Tourist Police channels.
Template fields:
1. Reporter/victim: full name, nationality, passport number, phone, email, accommodation address.
2. Incident: date, time, exact location, type of incident, persons involved, vehicle/license plate if any.
3. Loss or injury: stolen property, money amount, documents, injuries, medical treatment.
4. Suspect/description: appearance, names/accounts/phone numbers, photos/videos if available.
5. Evidence: CCTV location, receipts, chats, bank transfers, witness contacts.
6. Requested action: register the report, investigate, issue report confirmation if available, assist with documents/embassy/insurance.

Section 4. Tour agency, travel company, or tour guide complaint.
Recipient: Department of Tourism, Ministry of Tourism and Sports / TAT complaint channel.
Template fields:
1. Complainant and booking details.
2. Tour agency/company/guide name, license number if known, contact details.
3. Package/tour description: dates, itinerary, price, payment method, contract/advertisement.
4. Breach: cancelled tour, changed itinerary, unsafe service, unlicensed guide, overcharge, refusal to refund.
5. Evidence and requested remedy.

Section 5. Transportation complaint: taxi, bus, minibus, motorcycle taxi, tuk-tuk, ticket reservation.
Recipient: Department of Land Transport / public passenger protection complaint channels referenced by TAT.
Template fields:
1. Passenger details.
2. Transport type, route, date/time, pickup/drop-off place.
3. Vehicle details: license plate, driver name/ID, company, ticket or booking number.
4. Problem: overcharge, refusal, unsafe driving, accident, lost property, ticket/reservation issue, misconduct.
5. Evidence: receipt, ticket, photos, GPS route, video, witnesses.
6. Requested action: investigation, refund, penalty/disciplinary action, assistance recovering property, written response.
"""


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|section|article)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_text(text)


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def fetch_source(source: ThailandSource, timeout: float = 45.0) -> tuple[str, str]:
    urls = (source.url, *source.alt_urls)
    last_error: Exception | None = None
    verify_options = (True, False)

    for url in urls:
        for verify in verify_options:
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
                if len(text) < 500:
                    raise ValueError(f"downloaded text is too short ({len(text)} chars)")
                return text, str(response.url)
            except Exception as exc:  # pragma: no cover - exercised by integration run
                last_error = exc

    raise RuntimeError(f"failed to fetch {source.filename}: {last_error}")


def split_to_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"(?is)(?<![A-Za-z])(?:Section|SECTION|Article|ARTICLE)\s+"
        r"([0-9]+(?:/[0-9]+)?(?:\s*(?:bis|ter|quarter|quinque|sex|septem|octo|novem))?)"
        r"\.?\s*"
    )
    matches = list(pattern.finditer(text))
    sections: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = normalize_text(text[start:end])
        if len(body) >= 20:
            sections.append((normalize_text(match.group(1)), body))

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


def build_indexable_text(source: ThailandSource, text: str, resolved_url: str) -> str:
    sections = split_to_sections(text)
    blocks = [
        f"Thailand source: {source.title}",
        f"Category: {source.category}",
        f"Source URL: {resolved_url}",
        f"Note: {source.note or 'English reference text; verify against current Thai official text.'}",
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
    imported: Iterable[tuple[ThailandSource, str, int]],
    failed: Iterable[tuple[ThailandSource, str]],
) -> str:
    imported_list = list(imported)
    failed_list = list(failed)
    lines = [
        f"Thailand legal sources registry ({date.today().isoformat()})",
        "English translations are reference materials unless the source explicitly says otherwise.",
        "For legal force in Thailand, verify against the Thai text published in the Royal Gazette or competent agency source.",
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
                f"  note: {source.note or 'Reference translation.'}",
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
    (output_dir / "thai_statement_templates.txt").write_text(STATEMENT_TEMPLATE_TEXT, encoding="utf-8")


def import_sources(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    imported: list[tuple[ThailandSource, str, int]] = []
    failed: list[tuple[ThailandSource, str]] = []

    for source in SOURCES:
        try:
            text, resolved_url = fetch_source(source)
            indexable_text = build_indexable_text(source, text, resolved_url)
            (output_dir / f"{source.filename}.txt").write_text(indexable_text, encoding="utf-8")
            imported.append((source, resolved_url, len(split_to_sections(text))))
            print(f"imported {source.filename}")
        except Exception as exc:  # pragma: no cover - exercised by integration run
            failed.append((source, str(exc)))
            print(f"failed {source.filename}: {exc}")

    registry = build_registry_file(imported, failed)
    (output_dir / "thai_sources_registry_2026.txt").write_text(registry, encoding="utf-8")
    write_statement_templates(output_dir)
    return len(imported), len(failed)


if __name__ == "__main__":
    imported_count, failed_count = import_sources()
    print(f"Done: imported={imported_count}, failed={failed_count}")
