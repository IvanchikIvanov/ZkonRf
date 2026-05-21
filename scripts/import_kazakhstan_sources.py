"""Import Kazakhstan legal sources into bot-indexable text files."""
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


DEFAULT_OUTPUT_DIR = Path("data/codexes/kz")
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*",
}


@dataclass(frozen=True)
class KazakhstanSource:
    filename: str
    title: str
    url: str
    category: str
    note: str = ""
    alt_urls: tuple[str, ...] = field(default_factory=tuple)


SOURCES: tuple[KazakhstanSource, ...] = (
    KazakhstanSource(
        filename="kz_constitution",
        title="Constitution of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K950001000_",
        category="Core constitutional law",
        note="Official English reference text from Adilet legal information system.",
    ),
    KazakhstanSource(
        filename="kz_civil_code_general_part",
        title="Civil Code of the Republic of Kazakhstan, General Part",
        url="https://adilet.zan.kz/eng/docs/K940001000_",
        category="Core codes",
        note="Official English reference text from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_civil_code_special_part",
        title="Civil Code of the Republic of Kazakhstan, Special Part",
        url="https://adilet.zan.kz/eng/docs/K990000409_",
        category="Core codes",
        note="Official English reference text from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_civil_procedure_code",
        title="Civil Procedure Code of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K1500000377",
        category="Procedure",
        note="Official English reference text from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_penal_code",
        title="Penal Code of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K1400000226",
        category="Core codes",
        note="Official English reference text from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_criminal_procedure_code",
        title="Criminal Procedure Code of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K1400000231",
        category="Procedure",
        note="Official English reference text from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_administrative_offences_code",
        title="Code of the Republic of Kazakhstan on Administrative Offences",
        url="https://adilet.zan.kz/eng/docs/K1400000235",
        category="Administrative offences",
        note="Current administrative offences code; Adilet official English reference.",
        alt_urls=("https://www.adilet.zan.kz/eng/docs/K010000155_",),
    ),
    KazakhstanSource(
        filename="kz_labour_code",
        title="Labour Code of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K1500000414",
        category="Labour",
        note="Official English reference text from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_tax_code",
        title="Tax Code of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K2500000214",
        category="Tax",
        note="Current Tax Code of the Republic of Kazakhstan; official English reference from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_entrepreneur_code",
        title="Entrepreneur Code of the Republic of Kazakhstan",
        url="https://adilet.zan.kz/eng/docs/K1500000375",
        category="Business and consumer protection",
        note="Covers entrepreneurship, competition, state control and consumer-rights context.",
    ),
    KazakhstanSource(
        filename="kz_consumer_protection_law",
        title="Law of the Republic of Kazakhstan on Protection of Consumer Rights",
        url="https://www.refworld.org/sites/default/files/2026-01/the_law_of_the_republic_of_kazakhstan_dated_4_may_2010_no._274-iv_on_protection_of_consumer_rights.pdf",
        category="Consumer protection",
        note="Official English reference text from Adilet.",
        alt_urls=("https://adilet.zan.kz/eng/docs/Z100000274_",),
    ),
    KazakhstanSource(
        filename="kz_land_code",
        title="Land Code of the Republic of Kazakhstan",
        url="https://www.adilet.zan.kz/eng/docs/K030000442_",
        category="Land and real estate",
        note="Land ownership and land-use rules; official English reference from Adilet.",
    ),
    KazakhstanSource(
        filename="kz_housing_relations_law",
        title="Law of the Republic of Kazakhstan on Housing Relations",
        url="https://www.adilet.zan.kz/eng/docs/Z970000094_",
        category="Land and real estate",
        note="Housing relations, apartments and housing-stock rules.",
        alt_urls=("https://www.icnl.org/research/library/kazakhstan_housing/",),
    ),
    KazakhstanSource(
        filename="kz_real_estate_registration_law",
        title="Law on State Registration of Rights to Immovable Property",
        url="https://www.adilet.zan.kz/eng/docs/Z070000310_",
        category="Land and real estate",
        note="Real-estate registration rules; useful for apartment/ownership questions.",
    ),
    KazakhstanSource(
        filename="kz_architecture_construction_law",
        title="Law on Architectural, Town-planning and Construction Activity",
        url="https://www.adilet.zan.kz/eng/docs/Z010000242_",
        category="Land and real estate",
        note="Construction and permitting context for new-build or developer disputes.",
    ),
    KazakhstanSource(
        filename="kz_migration_law",
        title="Law of the Republic of Kazakhstan on Population Migration",
        url="https://www.refworld.org/legal/legislation/natlegbod/2011/en/151262",
        category="Immigration and visas",
        note="Migration law governing stay, residence and migration categories.",
        alt_urls=("https://adilet.zan.kz/eng/docs/Z1100000477",),
    ),
    KazakhstanSource(
        filename="kz_foreigners_legal_status_law",
        title="Law of the Republic of Kazakhstan on the Legal Status of Foreigners",
        url="https://adilet.zan.kz/eng/docs/U950002337_",
        category="Immigration and visas",
        note="Rights, duties and legal status of foreigners in Kazakhstan.",
    ),
    KazakhstanSource(
        filename="kz_entry_exit_foreigners_egov",
        title="Rules for entry and exit from Kazakhstan for foreign nationals",
        url="https://egov.kz/cms/en/articles/move_abroad/exit-entry_of_foreign_nationals",
        category="Immigration and visas",
        note="Official eGov practical guidance on entry, stay and receiving-party notification.",
    ),
    KazakhstanSource(
        filename="kz_evisa_official_guide",
        title="How to get an e-visa to Kazakhstan",
        url="https://www.gov.kz/uploads/2020/6/18/6af70adb08dfffdfa70dad92fb26e239_original.102322.pdf",
        category="Immigration and visas",
        note="Official gov.kz guide pointing to the Visa and Migration Portal.",
        alt_urls=("https://www.gov.kz/situations/763/intro?lang=en",),
    ),
    KazakhstanSource(
        filename="kz_visa_obtaining_egov",
        title="Obtaining visa of the Republic of Kazakhstan",
        url="https://egov.kz/cms/en/articles/rk_visa_obtaining",
        category="Immigration and visas",
        note="Official eGov visa guide and service overview.",
    ),
    KazakhstanSource(
        filename="kz_temporary_residence_permit_egov",
        title="Temporary residence permit for foreigners in Kazakhstan",
        url="https://egov.kz/cms/en/services/for_foreigners/00203002_mvd",
        category="Immigration and visas",
        note="Official eGov service page for temporary residence permits.",
    ),
    KazakhstanSource(
        filename="kz_residence_permit_egov",
        title="How to get residence permit in Kazakhstan",
        url="https://egov.kz/cms/en/articles/for_foreigners/vid_na_jitelstvo?mobile=no",
        category="Immigration and visas",
        note="Official eGov practical guidance on residence permit for foreigners.",
    ),
    KazakhstanSource(
        filename="kz_work_permit_egov",
        title="How foreigners can obtain a work permit in Kazakhstan",
        url="https://egov.kz/cms/en/articles/workpermit",
        category="Labour",
        note="Official eGov guide; notes EAEU citizens, including Russian citizens, may work under an employment contract without a permit.",
    ),
    KazakhstanSource(
        filename="kz_foreign_labour_procedure_egov",
        title="Procedure for employment of foreign labour in Kazakhstan",
        url="https://egov.kz/cms/en/articles/job_search/inostrannyi_trud",
        category="Labour",
        note="Official eGov guide on employer permits and foreign labour procedure.",
    ),
)


STATEMENT_TEMPLATE_TEXT = """Kazakhstan statement and application templates for common bot questions.
These are practical drafting/checklist templates for Russian citizens and other foreigners. They are not official forms unless a competent Kazakhstan authority publishes a specific form.

Section 1. Consumer complaint / demand letter against seller or service provider.
Use for defective goods, refund refusal, misleading service, online order, warranty dispute, delivery problem or paid service failure.
Source basis: Law on Protection of Consumer Rights; Civil Code; Entrepreneur Code.
Template fields:
1. Consumer: full name, passport/IIN if available, nationality, Kazakhstan address/contact.
2. Seller/service provider: legal name, BIN/IIN if known, address, website/platform, phone/email.
3. Contract/order details: date, price, payment proof, invoice/order number.
4. Problem: defect, non-delivery, misleading information, unsafe service, refusal to refund.
5. Evidence: photos, chat, receipt, advertisement, warranty card, delivery record.
6. Demand: refund, replacement, repair, compensation, written explanation and deadline.
Draft wording:
I request that the seller/service provider resolve the consumer rights issue described above within the stated deadline. If no response is received, I reserve the right to submit a complaint to the competent Kazakhstan authority and pursue available civil remedies.

Section 2. Tourism or travel-service complaint.
Use for hotel, tour operator, transport, event, booking, overcharge or unsafe service problems in Kazakhstan.
Source basis: Consumer Protection Law; Civil Code; Entrepreneur Code.
Template fields:
1. Tourist details: name, passport, nationality, contacts and itinerary dates.
2. Service provider: hotel/tour company/transport provider/platform.
3. Booking details: date, route, voucher, price, payment proof.
4. Incident description and harm.
5. Evidence and witnesses.
6. Requested remedy: refund, replacement service, compensation, written explanation.

Section 3. Police report for theft, fraud, assault, lost passport or property.
Use when a Russian citizen or foreigner needs a written incident report for police, embassy, insurer or migration authority.
Source basis: Penal Code; Criminal Procedure Code; Law on the Legal Status of Foreigners.
Template fields:
1. Applicant: name, passport, nationality, visa/TRP/residence details, Kazakhstan address.
2. Incident: date, time, place, suspect if known, property/value, bank/cards/devices affected.
3. Evidence: photos, CCTV location, transaction records, witnesses, chats.
4. Requested action: register report, investigate, issue confirmation/case number/copy for embassy or insurer.
Draft wording:
I request registration of this report and a written confirmation/case reference for use with my embassy, insurer and migration authorities.

Section 4. Visa and migration checklist for a Russian citizen.
Use before entry, visa/e-visa application, extension, notification or stay-planning question.
Source basis: eGov entry/exit rules; gov.kz e-visa guide; Law on Migration; Law on the Legal Status of Foreigners.
Template fields:
1. Passport data: full name, date/place of birth, citizenship, passport number, issue/expiry date.
2. Trip data: arrival/departure dates, address in Kazakhstan, host/receiving party.
3. Purpose: tourism, business, work, study, family, treatment, investment or other.
4. Entry/stay basis: visa-free entry, e-visa, visa, TRP, residence permit.
5. Receiving-party notification: who submits arrival/address notification and by what channel.
Russian-specific notes:
Russian citizens usually rely on visa-free/EAEU rules rather than ordinary e-visa, but must still track permitted stay, address notification and TRP/residence requirements when staying longer or working.

Section 5. E-visa / visa application or correction request.
Use for Kazakhstan e-visa, visa invitation, error correction, missing document or embassy/portal question.
Source basis: official gov.kz e-visa guide; eGov visa guide.
Template fields:
1. Application/invitation number if any.
2. Applicant passport and travel purpose.
3. Incorrect or missing field and corrected value.
4. Sponsor/inviting party details if applicable.
5. Attached documents and payment/portal evidence.
Draft wording:
I respectfully request review or correction of my Kazakhstan visa/e-visa application using the accurate information and documents listed above.

Section 6. Temporary residence permit / stay regularization checklist.
Use for TRP, long stay, address change, receiving party notice, family, study, work or treatment basis.
Source basis: eGov TRP service; Law on Migration; entry/exit rules.
Template fields:
1. Applicant identity and current stay basis.
2. Receiving party: employer, landlord, family member, school, clinic or company.
3. Purpose and expected term.
4. Documents: passport, address, contract/invitation, employment or study/treatment/family basis.
5. Problem: expired stay, address change, missing notification, document correction.
Draft wording:
I request guidance and acceptance of documents for lawful temporary residence / regularization of my stay based on the facts and evidence described above.

Section 7. Residence permit checklist.
Use for permanent residence, solvency documents, housing confirmation, no-objection/departure documents or renewal.
Source basis: eGov residence permit guide; Law on Migration; Law on Legal Status of Foreigners.
Template fields:
1. Applicant passport, nationality, current legal stay.
2. Basis for residence and family/employment/business ties.
3. Solvency confirmation and housing arrangement.
4. Police clearance / departure or no-objection document if required by applicable procedure.
5. Requested review: eligibility, missing documents, timing and territorial migration body.

Section 8. Work permit / employment checklist.
Use for foreign employment, employer permit, EAEU/Russian citizen employment, labour contract or TRP for work.
Source basis: Labour Code; eGov work permit and foreign labour procedure; Law on Migration.
Template fields:
1. Worker identity, citizenship, passport and qualifications.
2. Employer: legal name, BIN, workplace, position.
3. Employment basis: EAEU employment contract, employer permit, intra-corporate transfer or other.
4. Documents: employment contract, ESUTD registration if applicable, permits, address, TRP documents.
5. Questions for review: whether a permit is needed, who applies, timing, renewal and tax/social obligations.

Section 9. Foreign real-estate purchase due-diligence checklist.
Use before a Russian citizen or other foreigner pays deposit or signs for apartment, house, land, commercial premises or new-build property.
Source basis: Civil Code; Land Code; Housing Relations Law; State Registration of Rights to Immovable Property Law; construction law.
Template fields:
1. Buyer: passport, nationality, Kazakhstan stay/residence status, IIN if available.
2. Property: address, cadastral number, apartment/house/land/commercial status, seller/developer.
3. Eligibility: whether foreigner can own the asset type; land restrictions; apartment versus land plot distinction; residence-status implications.
4. Title and encumbrances: state registration, owner authority, mortgage/arrest/claims, cadastral passport.
5. Contract terms: deposit, price, currency, deadline, taxes/fees, default, handover, defects.
6. Russian-specific risk checks: cross-border bank transfer route, sanctions/payment delays, currency controls, Russian tax reporting advice if needed.
Draft request:
Please review whether this property can lawfully be acquired by a foreign individual and identify missing documents before I pay deposit or sign the sale agreement.

Section 10. Lease / long-term rental / address registration checklist.
Use for apartment rent, landlord deposit dispute, temporary address, receiving-party notification or proof of housing for TRP/residence.
Source basis: Civil Code; Housing Relations Law; migration/entry rules.
Template fields:
1. Tenant and landlord identity.
2. Premises: address, term, rent, deposit, utilities, inventory/photos.
3. Landlord authority and ownership/registration documents.
4. Migration angle: receiving-party notification, address confirmation, lease term for TRP/residence.
5. Dispute remedy: deposit return, repairs, early termination, written explanation.

Section 11. Demand letter to developer, seller, real-estate agent or landlord.
Use for deposit refusal, misleading ownership promise, construction defect, delayed transfer, rental deposit dispute or unauthorized fee.
Source basis: Civil Code; Consumer Protection Law; Housing Relations Law; Real Estate Registration Law; construction law.
Template fields:
1. Claimant and respondent details.
2. Contract/reservation/lease details and amounts paid.
3. Problem and legal/business basis.
4. Evidence: contract, receipts, chats, advertisements, photos, registry/cadastral documents.
5. Demand and deadline.
Draft wording:
I request that you resolve the issue described above by the stated deadline. If no satisfactory response is received, I reserve all rights to file complaints and seek legal remedies in Kazakhstan.

Section 12. Real-estate registration / cadastral correction request.
Use when ownership registration, encumbrance removal, cadastral passport, address mismatch or registry extract is needed.
Source basis: Law on State Registration of Rights to Immovable Property; Civil Code; Land Code.
Template fields:
1. Applicant and property details.
2. Right or transaction to register/correct.
3. Current registry issue and requested correction.
4. Attached documents: contract, ID/passport, cadastral documents, payment proof, power of attorney.
5. Requested result: registration, extract, correction, refusal explanation.

Section 13. Foreign investor / company setup checklist.
Use for business, individual entrepreneur/company, property-related business, employment of foreigners or tax questions.
Source basis: Entrepreneur Code; Civil Code; Tax Code; Labour Code; Migration Law.
Template fields:
1. Investor identity and nationality.
2. Planned activity, location, partners and capital.
3. Legal form: individual entrepreneur, LLP/company, branch, representative office or other.
4. Licenses/permits/tax registration and employer obligations.
5. Risk flags: nominee arrangements, property restrictions, foreign labour permits, tax residency.

Section 14. Administrative fine / protocol response template.
Use for migration fine, traffic/consumer/business fine, protocol disagreement or need to appeal administrative action.
Source basis: Code on Administrative Offences; Civil Procedure/administrative court context where applicable.
Template fields:
1. Person/entity fined and protocol details.
2. Authority, date, article cited, amount, deadline.
3. Facts disputed or mitigating circumstances.
4. Evidence and witnesses.
5. Requested action: terminate, reduce, correct, provide copy, restore appeal term.
Draft wording:
I do not agree with the protocol/decision for the reasons stated above and request review of the evidence, correction of errors and a reasoned written decision.

Section 15. Consular support request for Russian citizen.
Use after lost passport, arrest, accident, illness, visa/stay issue, property dispute or document legalization.
Source basis: legal status of foreigners, migration rules, criminal procedure principles and practical consular workflows.
Template fields:
1. Citizen identity and Russian passport/internal passport details if available.
2. Kazakhstan location and contact.
3. Emergency facts and authority involved.
4. Documents/evidence and people to contact.
5. Requested support: return certificate, police/migration liaison, document confirmation, lawyer/translator contacts.
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


def fetch_source(source: KazakhstanSource, timeout: float = 45.0) -> tuple[str, str]:
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
        r"(?is)(?<![A-Za-z])(?:Section|SECTION|Article|ARTICLE)\s+"
        r"([0-9]+(?:[-/][0-9]+)?(?:[a-z])?(?:\s*(?:bis|ter|quarter|quinque|sex|septem|octo|novem))?)"
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


def build_indexable_text(source: KazakhstanSource, text: str, resolved_url: str) -> str:
    sections = split_to_sections(text)
    blocks = [
        f"Kazakhstan source: {source.title}",
        f"Category: {source.category}",
        f"Source URL: {resolved_url}",
        f"Note: {source.note or 'English reference text; verify against current Kazakhstan official text.'}",
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
    imported: Iterable[tuple[KazakhstanSource, str, int]],
    failed: Iterable[tuple[KazakhstanSource, str]],
) -> str:
    imported_list = list(imported)
    failed_list = list(failed)
    lines = [
        f"Kazakhstan legal sources registry ({date.today().isoformat()})",
        "English translations are reference materials unless the source explicitly says otherwise.",
        "For legal force in Kazakhstan, verify against the Kazakh/Russian text published by the competent authority.",
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
    (output_dir / "kz_statement_templates.txt").write_text(STATEMENT_TEMPLATE_TEXT, encoding="utf-8")


def import_sources(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    imported: list[tuple[KazakhstanSource, str, int]] = []
    failed: list[tuple[KazakhstanSource, str]] = []

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
    (output_dir / "kz_sources_registry_2026.txt").write_text(registry, encoding="utf-8")
    write_statement_templates(output_dir)
    return len(imported), len(failed)


if __name__ == "__main__":
    imported_count, failed_count = import_sources()
    print(f"Done: imported={imported_count}, failed={failed_count}")
