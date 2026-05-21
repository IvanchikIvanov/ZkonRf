"""Import Vietnam legal sources into bot-indexable text files."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Iterable

import httpx


DEFAULT_OUTPUT_DIR = Path("data/codexes/vn")
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*",
}


@dataclass(frozen=True)
class VietnamSource:
    filename: str
    title: str
    url: str
    category: str
    note: str = ""
    alt_urls: tuple[str, ...] = field(default_factory=tuple)


SOURCES: tuple[VietnamSource, ...] = (
    VietnamSource(
        filename="vn_civil_code_2015",
        title="Vietnam Civil Code No. 91/2015/QH13",
        url="https://www.wipo.int/wipolex/edocs/lexdocs/laws/en/vn/vn079en_1.pdf",
        category="Core codes",
        note="WIPO Lex English reference text; Vietnamese official text prevails.",
    ),
    VietnamSource(
        filename="vn_civil_procedure_code_2015",
        title="Vietnam Civil Procedure Code No. 92/2015/QH13",
        url="https://www.wipo.int/wipolex/edocs/lexdocs/laws/en/vn/vn015en.pdf",
        category="Procedure",
        note="WIPO Lex English reference text.",
    ),
    VietnamSource(
        filename="vn_criminal_procedure_code_2015",
        title="Vietnam Criminal Procedure Code No. 101/2015/QH13",
        url="https://english.luatvietnam.vn/law-no-101-2015-qh13-dated-november-27-2015-of-the-national-assembly-on-criminal-procedure-code-101322-doc1.html",
        category="Procedure",
        note="WIPO Lex English reference text.",
        alt_urls=("https://www.wipo.int/wipolex/edocs/lexdocs/laws/en/vn/vn018en.pdf",),
    ),
    VietnamSource(
        filename="vn_penal_code_2015_amended_2017",
        title="Vietnam Penal/Criminal Code 2015, amended 2017",
        url="https://dazpro.com/law-100-2015-vietnam-on-penal-crime/",
        category="Core codes",
        note="Consolidated English reference text; includes Law 12/2017/QH14 amendments.",
        alt_urls=("https://www.warnathgroup.com/wp-content/uploads/2017/11/Vietnam-Criminal-Code-2015.pdf",),
    ),
    VietnamSource(
        filename="vn_labour_code_2019",
        title="Vietnam Labour Code No. 45/2019/QH14",
        url="https://vietanlaw.com/vietnam-labour-code-2019/",
        category="Labour",
        note="English reference text of the 2019 Labour Code.",
    ),
    VietnamSource(
        filename="vn_enterprise_law_2020",
        title="Vietnam Law on Enterprises No. 59/2020/QH14",
        url="https://english.luatvietnam.vn/law-on-enterprises-no-59-2020-qh14-dated-june-17-2020-of-the-national-assembly-186272-doc1.html",
        category="Business and investment",
        note="English text published by LuatVietnam.",
    ),
    VietnamSource(
        filename="vn_investment_law_2020",
        title="Vietnam Law on Investment No. 61/2020/QH14",
        url="https://english.luatvietnam.vn/law-on-investment-no-61-2020-qh14-dated-june-17-2020-of-the-national-assembly-186270-doc1.html",
        category="Business and investment",
        note="English text published by LuatVietnam.",
        alt_urls=("https://vplsdms.vn/en/law-on-investment-no.-612020qh14-dated-june-17-2020",),
    ),
    VietnamSource(
        filename="vn_tax_administration_law_2019",
        title="Vietnam Law on Tax Administration No. 38/2019/QH14",
        url="https://english.luatvietnam.vn/law-no-38-2019-qh14-dated-june-13-2019-of-the-national-assembly-on-tax-administration-174969-doc1.html",
        category="Tax",
        note="English text published by LuatVietnam.",
    ),
    VietnamSource(
        filename="vn_land_law_2024",
        title="Vietnam Land Law No. 31/2024/QH15",
        url="https://english.luatvietnam.vn/dat-dai/land-law-2024-no-31-2024-qh15-296638-d1.html",
        category="Land and real estate",
        note="New Land Law effective from July 1, 2024; English text published by LuatVietnam.",
    ),
    VietnamSource(
        filename="vn_housing_law_2023",
        title="Vietnam Housing Law No. 27/2023/QH15",
        url="https://english.luatvietnam.vn/dat-dai/housing-law-no-27-2023-qh15-284800-d1.html",
        category="Land and real estate",
        note="Includes foreign-organization and foreign-individual housing ownership provisions.",
    ),
    VietnamSource(
        filename="vn_real_estate_business_law_2023",
        title="Vietnam Law on Real Estate Business No. 29/2023/QH15",
        url="https://english.luatvietnam.vn/dat-dai/law-on-real-estate-business-2023-no-29-2023-qh15-284798-d1.html",
        category="Land and real estate",
        note="Real-estate business and services law effective under the 2023 reform package.",
    ),
    VietnamSource(
        filename="vn_housing_decree_95_2024_foreigners",
        title="Vietnam Decree No. 95/2024/ND-CP detailing the Housing Law",
        url="https://english.luatvietnam.vn/dau-tu/decree-95-2024-nd-cp-detail-housing-law-361551-d1.html",
        category="Land and real estate",
        note="Practical implementation rules for housing, including foreign ownership restrictions.",
    ),
    VietnamSource(
        filename="vn_consumer_protection_law_2023",
        title="Vietnam Law on Protection of Consumers' Rights No. 19/2023/QH15",
        url="https://english.luatvietnam.vn/thuong-mai/law-on-protection-of-consumer-rights-no-19-2023-qh15-259732-d1.html",
        category="Consumer protection",
        note="New consumer law effective from July 1, 2024.",
    ),
    VietnamSource(
        filename="vn_tourism_law_2017",
        title="Vietnam Tourism Law No. 09/2017/QH14",
        url="https://english.luatvietnam.vn/law-no-09-2017-qh14-dated-june-19-2017-of-the-national-assembly-on-tourism-115518-doc1.html",
        category="Tourism and travel complaints",
        note="Rights and obligations of tourists and tourism service providers.",
        alt_urls=("https://www.hpta.vn/en/vb-tourism-law-no-092017qh14.html",),
    ),
    VietnamSource(
        filename="vn_advertising_law_2012",
        title="Vietnam Law on Advertising No. 16/2012/QH13",
        url="https://www.wipo.int/wipolex/edocs/lexdocs/laws/en/vn/vn027en.html",
        category="Consumer protection",
        note="WIPO Lex English text; useful for misleading advertising and service representations.",
    ),
    VietnamSource(
        filename="vn_competition_law_2018",
        title="Vietnam Competition Law No. 23/2018/QH14",
        url="https://english.luatvietnam.vn/law-no-23-2018-qh14-dated-june-12-2018-of-the-national-assembly-on-competition-164727-doc1.html",
        category="Commerce",
        note="Competition and unfair competition reference.",
    ),
    VietnamSource(
        filename="vn_e_transactions_law_2023",
        title="Vietnam Law on E-Transactions No. 20/2023/QH15",
        url="https://english.luatvietnam.vn/thuong-mai/law-on-e-transactions-2023-no-20-2023-qh15-259738-d1.html",
        category="Digital services",
        note="New electronic transactions law effective from July 1, 2024.",
    ),
    VietnamSource(
        filename="vn_cybersecurity_law_2018",
        title="Vietnam Cybersecurity Law No. 24/2018/QH14",
        url="https://lawnet.vn/thong-tin-phap-luat/en/khac/full-text-of-the-cybersecurity-law-2018-in-vietnam-157889.html",
        category="Digital services",
        note="English full-text reference via LawNet.",
        alt_urls=("https://dulieuphapluat.vn/van-ban/cong-nghe-thong-tin-van-ban/law-on-cybersecurity-2018-1013298.html",),
    ),
    VietnamSource(
        filename="vn_personal_data_decree_13_2023",
        title="Vietnam Decree No. 13/2023/ND-CP on Personal Data Protection",
        url="https://www.dataguidance.com/sites/default/files/decree-13-2023-pdpd_en_clean.pdf",
        category="Digital services",
        note="English reference translation of Vietnam's personal data protection decree.",
        alt_urls=("https://apolatlegal.com/laws/decree-no-13-2023-nd-cp-on-personal-data-protection/",),
    ),
    VietnamSource(
        filename="vn_immigration_law_2014",
        title="Vietnam Law on Entry, Exit, Transit and Residence of Foreigners No. 47/2014/QH13",
        url="https://english.luatvietnam.vn/law-no-47-2014-qh13-on-entry-exit-transit-and-residence-of-foreigners-in-vietnam-87925-doc1.html",
        category="Immigration and visas",
        note="Core law for foreigner entry, exit, transit, visas and residence.",
        alt_urls=("https://vanbanphapluat.co/law-no-47-2014-qh13-dated-2014-entry-exit-transit-residence-of-foreigners-in-vietnam",),
    ),
    VietnamSource(
        filename="vn_immigration_law_2019_amendments",
        title="Vietnam Law No. 51/2019/QH14 amending foreigner entry/exit/residence rules",
        url="https://vplsdms.vn/en/advising-on-the-law-on-entry-exit-transit-and-residence-of-foreigners-in-vietnam-no.-472014qh13-dated-june-16-2014",
        category="Immigration and visas",
        note="VPLSDMS page referencing the 2019 amendments and current status.",
    ),
    VietnamSource(
        filename="vn_official_evisa_guide",
        title="Official guide to Vietnam e-Visa application",
        url="https://vietnam.travel/plan-your-trip/official-vietnam-evisa-application",
        category="Immigration and visas",
        note="Vietnam National Authority of Tourism guide pointing travelers to the official e-visa website.",
        alt_urls=("https://evisa.gov.vn/",),
    ),
    VietnamSource(
        filename="vn_visa_information_mofa",
        title="Information on Viet Nam visa and immigration regulations",
        url="https://vietnam.travel/plan-your-trip/official-vietnam-evisa-application",
        category="Immigration and visas",
        note="Official Vietnam Tourism e-visa information; useful for tourist/e-visa questions.",
    ),
    VietnamSource(
        filename="vn_foreign_worker_decree_152_2020",
        title="Vietnam Decree No. 152/2020/ND-CP on foreign workers",
        url="https://english.luatvietnam.vn/decree-no152-2020-nd-cp-dated-december-30-2020-of-the-government-providing-regulations-on-foreign-employees-working-in-vietnam-and-recruitment-mana-196375-doc1.html",
        category="Labour",
        note="Foreign worker and work permit rules.",
        alt_urls=("https://vanbanphapluat.co/decree-152-2020-nd-cp-foreign-workers-working-in-vietnam",),
    ),
)


STATEMENT_TEMPLATE_TEXT = """Vietnam statement and application templates for common bot questions.
These are practical drafting/checklist templates for Russian citizens and other foreigners. They are not official forms unless a competent Vietnamese authority publishes a specific form.

Section 1. Consumer complaint / demand letter against seller or service provider.
Use for defective goods, refund refusal, misleading service, online order, hotel/service issue or warranty dispute.
Source basis: Law on Protection of Consumers' Rights 2023; Civil Code 2015; Advertising Law 2012 where misleading statements matter.
Template fields:
1. Consumer: full name, passport, nationality, address/contact in Vietnam or abroad.
2. Seller/service provider: legal name, address, website/platform, phone/email.
3. Contract/order details: date, price, payment proof, invoice/order number.
4. Problem: defect, non-delivery, misleading information, unsafe service, refusal to refund.
5. Evidence: photos, chat, receipt, advertisement, warranty card, delivery record.
6. Demand: refund, replacement, repair, compensation, written explanation and deadline.
Draft wording:
I request that the seller/service provider resolve the consumer rights issue described above within the stated deadline. If no response is received, I reserve the right to submit a complaint to competent Vietnamese authorities and pursue available civil remedies.

Section 2. Tourism complaint for hotel, tour operator, guide, transport or travel service.
Use for cancelled tours, unsafe service, misrepresentation, overcharge, lost booking, guide misconduct or tourist damage.
Source basis: Tourism Law 2017; Consumer Protection Law 2023; Civil Code 2015.
Template fields:
1. Tourist details: name, passport, nationality, contacts and itinerary dates.
2. Service provider: hotel/tour company/guide/transport provider.
3. Booking details: date, route, voucher, price, payment proof.
4. Incident description and harm.
5. Evidence and witnesses.
6. Requested remedy: refund, replacement service, compensation, written apology, authority review.

Section 3. Police report for theft, fraud, assault, lost passport or property.
Use when a Russian citizen or foreigner needs a written incident report for police, embassy, insurer or immigration.
Source basis: Penal Code 2015 amended 2017; Criminal Procedure Code 2015; immigration law for passport/visa consequences.
Template fields:
1. Applicant: name, passport, nationality, visa/e-visa/residence details, Vietnam address.
2. Incident: date, time, place, suspect if known, property/value, bank/cards/devices affected.
3. Evidence: photos, CCTV location, transaction records, witnesses, chats.
4. Requested action: register report, investigate, issue confirmation/case number/copy for embassy or insurer.
Draft wording:
I request registration of this report and a written confirmation/case reference for use with my embassy, insurer and immigration authorities.

Section 4. E-visa application checklist for a Russian citizen.
Use before filing or correcting a Vietnam e-visa application.
Source basis: official e-visa guide; Law on Entry, Exit, Transit and Residence of Foreigners; MOFA visa information.
Template fields:
1. Passport data: full name, sex, date/place of birth, nationality, passport number, issue/expiry date.
2. Trip data: arrival/departure dates, entry/exit border gates, address in Vietnam, host/hotel.
3. Visa type: single/multiple entry if available, purpose, planned stay.
4. Uploads: passport bio page, portrait photo, payment confirmation.
5. Risk checks: exact spelling, passport validity, selected border gate, duplicated applications, scam/third-party website avoidance.
Russian-specific notes:
Use the official e-visa portal or official guidance pages. Check payment route/card availability and preserve application code, receipt and email from official domain.

Section 5. Visa correction / supplement explanation letter.
Use when e-visa data is wrong, an application is returned for correction, or documents must be supplemented.
Source basis: official e-visa guide and immigration law.
Template fields:
1. Application code and applicant passport details.
2. Incorrect field and corrected value.
3. Reason for correction: typo, photo mismatch, passport renewal, changed itinerary.
4. Attached documents.
Draft wording:
I respectfully request correction or review of my e-visa application using the accurate information and supporting documents listed above.

Section 6. Visa extension / temporary stay issue explanation.
Use for overstay risk, flight cancellation, illness, lost passport, administrative delay or request to regularize stay.
Source basis: immigration law on entry, exit, residence and exit suspension; embassy visa guidance.
Template fields:
1. Applicant identity and current visa/stay permission.
2. Current location and Vietnam contact address.
3. Problem and dates.
4. Evidence: flight cancellation, medical certificate, police report, embassy letter, application receipt.
5. Requested action: guidance, extension/regularization, exit assistance, written confirmation.
Draft wording:
The circumstances were outside my control / arose from the facts described above. I request guidance on the lawful procedure to regularize my stay or exit Vietnam.

Section 7. Temporary residence card / residence status checklist.
Use for employment, family, investment or other longer-stay questions.
Source basis: immigration law and amendments; work permit rules where employment is involved.
Template fields:
1. Applicant passport and current visa.
2. Sponsor: employer, investment company, family member, school or other host.
3. Basis: work permit/work permit exemption, investment registration, family relation, study.
4. Documents: sponsor letter, enterprise documents, work permit, photos, address, prior visa/stay evidence.
5. Questions for review: eligibility, validity period, sponsor responsibility, local submission place.

Section 8. Work permit / foreign worker checklist.
Use for Russian citizens and other foreigners working in Vietnam.
Source basis: Labour Code 2019 and Decree 152/2020/ND-CP on foreign workers.
Template fields:
1. Worker identity, passport, education, professional experience.
2. Employer: legal name, enterprise registration, workplace.
3. Position type and job description.
4. Documents: health certificate, criminal record, degree/experience proof, legalized/translated documents if required.
5. Requested review: whether work permit, exemption or temporary residence card path applies.

Section 9. Foreign residential property purchase due-diligence checklist.
Use before a foreigner or Russian citizen pays deposit for apartment/house in Vietnam.
Source basis: Housing Law 2023; Decree 95/2024/ND-CP; Land Law 2024; Real Estate Business Law 2023; Civil Code 2015.
Template fields:
1. Buyer: passport, nationality, visa/entry status, Vietnam contact.
2. Property: project name, developer/seller, apartment/house number, location, price.
3. Eligibility: project is not in restricted defense/security area; foreign quota available; buyer permitted to enter Vietnam.
4. Title/rights: ownership certificate/pink book status, project permits, mortgage/encumbrance, handover and warranty.
5. Contract terms: deposit, refund, transfer date, fees/taxes, default, foreign ownership term, extension/resale.
6. Russian-specific risk checks: bank transfer route, sanctions/payment delays, currency source evidence, Russian tax/currency advice if needed.
Draft request:
Please review whether this property can lawfully be owned by a foreign individual and identify missing documents before I pay deposit or sign the sale agreement.

Section 10. Lease / long-term rental / serviced apartment checklist.
Use for foreigner rentals, deposit disputes or long-stay housing arrangements.
Source basis: Civil Code 2015; Housing Law 2023; immigration address/residence practice.
Template fields:
1. Tenant and landlord identity.
2. Premises: address, unit, term, rent, deposit, utilities.
3. Documents: landlord title/authority, contract, payment receipts, inventory/photos.
4. Clauses: early termination, deposit return, repairs, sublease, registration/address support.
5. Immigration angle: hotel/landlord address reporting, proof of address for visa/residence needs.

Section 11. Demand letter to developer, seller, agent or landlord.
Use for deposit refusal, misleading foreign-ownership promise, construction defect, delayed transfer, rental deposit dispute or unauthorized fee.
Source basis: Civil Code 2015; Housing Law 2023; Real Estate Business Law 2023; Consumer Protection Law 2023.
Template fields:
1. Claimant and respondent details.
2. Contract/reservation/lease details and amounts paid.
3. Problem and legal/business basis.
4. Evidence: contract, receipts, chats, advertisements, photos, title/project documents.
5. Demand and deadline.
Draft wording:
I request that you resolve the issue described above by the stated deadline. If no satisfactory response is received, I reserve all rights to file complaints and seek legal remedies in Vietnam.

Section 12. Real-estate agent / broker complaint checklist.
Use when broker misrepresented foreign quota, price, fees, title, developer status or refund conditions.
Source basis: Real Estate Business Law 2023; Consumer Protection Law 2023; Advertising Law 2012.
Template fields:
1. Broker identity and license/company details if known.
2. Advertisement or statements relied on.
3. Payment and contract history.
4. Misrepresentation or non-performance.
5. Requested remedy and authority/escalation route.

Section 13. Foreign investor / company setup checklist for property-related or business activity.
Use when a foreigner asks whether to open a company, invest, or structure property/business activity in Vietnam.
Source basis: Law on Enterprises 2020; Law on Investment 2020; Land/Housing/Real Estate Business laws.
Template fields:
1. Investor identity and nationality.
2. Planned activity: trading, services, consulting, real estate, leasing, employment.
3. Ownership/investment capital and partners.
4. Required licenses/conditional business lines.
5. Risk flags: nominee arrangements, using a company only to bypass property restrictions, tax and reporting duties.

Section 14. Personal data / online platform complaint.
Use for misuse of passport/photo/identity data, platform account issue, online service, data transfer, scam website or unauthorized processing.
Source basis: Decree 13/2023/ND-CP on personal data protection; E-Transactions Law 2023; Cybersecurity Law 2018; Consumer Protection Law 2023.
Template fields:
1. Data subject identity and contacts.
2. Controller/processor/platform details.
3. Data involved: passport, phone, address, biometric/photo, payment, account.
4. Harm/risk and requested action: delete, correct, restrict, explain, compensate.
5. Evidence: screenshots, emails, consent forms, privacy notices.

Section 15. Embassy / consular support request for Russian citizen.
Use after lost passport, arrest, serious accident, visa/overstay issue, document legalization or emergency.
Source basis: immigration law, criminal procedure principles and practical consular workflows.
Template fields:
1. Citizen identity and Russian passport/internal passport details if available.
2. Vietnam location and contact.
3. Emergency facts and authority involved.
4. Documents/evidence and people to contact.
5. Requested support: return certificate, police/immigration liaison, document confirmation, lawyer/translator contacts.
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


def fetch_source(source: VietnamSource, timeout: float = 45.0) -> tuple[str, str]:
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
                if len(text) < 500:
                    raise ValueError(f"downloaded text is too short ({len(text)} chars)")
                return text, str(response.url)
            except Exception as exc:  # pragma: no cover - exercised by integration run
                last_error = exc

    raise RuntimeError(f"failed to fetch {source.filename}: {last_error}")


def split_to_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"(?is)(?<![A-Za-z])(?:Section|SECTION|Article|ARTICLE|Điều)\s+"
        r"([0-9]+(?:/[0-9]+)?(?:[a-z])?(?:\s*(?:bis|ter|quarter|quinque|sex|septem|octo|novem))?)"
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


def build_indexable_text(source: VietnamSource, text: str, resolved_url: str) -> str:
    sections = split_to_sections(text)
    blocks = [
        f"Vietnam source: {source.title}",
        f"Category: {source.category}",
        f"Source URL: {resolved_url}",
        f"Note: {source.note or 'English reference text; verify against current Vietnamese official text.'}",
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
    imported: Iterable[tuple[VietnamSource, str, int]],
    failed: Iterable[tuple[VietnamSource, str]],
) -> str:
    imported_list = list(imported)
    failed_list = list(failed)
    lines = [
        f"Vietnam legal sources registry ({date.today().isoformat()})",
        "English translations are reference materials unless the source explicitly says otherwise.",
        "For legal force in Vietnam, verify against the Vietnamese text published by the competent authority.",
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
    (output_dir / "vn_statement_templates.txt").write_text(STATEMENT_TEMPLATE_TEXT, encoding="utf-8")


def import_sources(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    imported: list[tuple[VietnamSource, str, int]] = []
    failed: list[tuple[VietnamSource, str]] = []

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
    (output_dir / "vn_sources_registry_2026.txt").write_text(registry, encoding="utf-8")
    write_statement_templates(output_dir)
    return len(imported), len(failed)


if __name__ == "__main__":
    imported_count, failed_count = import_sources()
    print(f"Done: imported={imported_count}, failed={failed_count}")
