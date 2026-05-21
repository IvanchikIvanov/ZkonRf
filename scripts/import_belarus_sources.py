"""Import Belarus legal sources into bot-indexable text files."""
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


DEFAULT_OUTPUT_DIR = Path("data/codexes/by")
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/pdf,application/xhtml+xml,*/*",
}


@dataclass(frozen=True)
class BelarusSource:
    filename: str
    title: str
    url: str
    category: str
    note: str = ""
    alt_urls: tuple[str, ...] = field(default_factory=tuple)


def pravo_url(regnum: str) -> str:
    return f"https://pravo.by/document/?guid=3871&p0={regnum}"


SOURCES: tuple[BelarusSource, ...] = (
    BelarusSource(
        filename="by_constitution",
        title="Constitution of the Republic of Belarus",
        url=pravo_url("V19402875"),
        category="Core constitutional law",
        note="Official text from the National Legal Internet Portal of Belarus.",
    ),
    BelarusSource(
        filename="by_civil_code",
        title="Civil Code of the Republic of Belarus",
        url=pravo_url("hk9800218"),
        category="Core codes",
        note="Civil-law basis for contracts, obligations, property and damages.",
    ),
    BelarusSource(
        filename="by_civil_procedure_code",
        title="Civil Procedure Code of the Republic of Belarus",
        url=pravo_url("hk9900238"),
        category="Procedure",
        note="Civil court procedure and procedural remedies.",
    ),
    BelarusSource(
        filename="by_criminal_code",
        title="Criminal Code of the Republic of Belarus",
        url=pravo_url("hk9900275"),
        category="Core codes",
        note="Criminal liability and offences.",
    ),
    BelarusSource(
        filename="by_criminal_procedure_code",
        title="Criminal Procedure Code of the Republic of Belarus",
        url=pravo_url("hk9900295"),
        category="Procedure",
        note="Criminal complaints, reports and investigation procedure.",
    ),
    BelarusSource(
        filename="by_labour_code",
        title="Labour Code of the Republic of Belarus",
        url=pravo_url("hk9900296"),
        category="Labour",
        note="Employment contracts, workers' rights and labour disputes.",
    ),
    BelarusSource(
        filename="by_family_code",
        title="Code of the Republic of Belarus on Marriage and Family",
        url=pravo_url("hk9900278"),
        category="Family",
        note="Marriage, divorce, family status, children and civil-status context.",
    ),
    BelarusSource(
        filename="by_land_code",
        title="Land Code of the Republic of Belarus",
        url=pravo_url("hk0800425"),
        category="Land and real estate",
        note="Land rights and land-use rules.",
    ),
    BelarusSource(
        filename="by_housing_code",
        title="Housing Code of the Republic of Belarus",
        url=pravo_url("hk1200428"),
        category="Land and real estate",
        note="Housing rights, residential premises and housing-use rules.",
    ),
    BelarusSource(
        filename="by_administrative_offences_code",
        title="Code of the Republic of Belarus on Administrative Offences",
        url=pravo_url("hk2100091"),
        category="Administrative offences",
        note="Administrative liability, including migration and consumer-related penalties.",
    ),
    BelarusSource(
        filename="by_administrative_procedure_execution_code",
        title="Procedural-Executive Code of Administrative Offences of Belarus",
        url=pravo_url("hk2100092"),
        category="Administrative procedure",
        note="Administrative-offence proceedings and execution procedure.",
    ),
    BelarusSource(
        filename="by_tax_code_general_part",
        title="Tax Code of the Republic of Belarus, General Part",
        url=pravo_url("hk0200166"),
        category="Tax",
        note="General tax rules and tax obligations.",
    ),
    BelarusSource(
        filename="by_tax_code_special_part",
        title="Tax Code of the Republic of Belarus, Special Part",
        url=pravo_url("hk0900071"),
        category="Tax",
        note="Specific taxes, duties and special tax regimes.",
    ),
    BelarusSource(
        filename="by_citizenship_law",
        title="Law on Citizenship of the Republic of Belarus",
        url=pravo_url("H10200136"),
        category="Immigration and citizenship",
        note="Citizenship acquisition, termination, passports and citizenship status.",
    ),
    BelarusSource(
        filename="by_foreigners_legal_status_law",
        title="Law on the Legal Status of Foreign Citizens and Stateless Persons",
        url=pravo_url("H11000105"),
        category="Immigration and visas",
        note="Entry, stay, residence, registration and rights of foreigners.",
    ),
    BelarusSource(
        filename="by_external_labour_migration_law",
        title="Law on External Labour Migration",
        url="https://etalonline.by/document/?regnum=H11000225",
        category="Labour",
        note="Foreign labour migration and employment-related migration rules.",
        alt_urls=(pravo_url("H11000225"),),
    ),
    BelarusSource(
        filename="by_consumer_protection_law",
        title="Law on Protection of Consumer Rights",
        url=pravo_url("H10200090"),
        category="Consumer protection",
        note="Consumer complaints, refunds, defects, services and seller duties.",
    ),
    BelarusSource(
        filename="by_real_estate_registration_law",
        title="Law on State Registration of Immovable Property, Rights and Transactions",
        url=pravo_url("H10200133"),
        category="Land and real estate",
        note="Registration of immovable property, rights, encumbrances and transactions.",
    ),
    BelarusSource(
        filename="by_personal_data_law",
        title="Law on Personal Data Protection",
        url=pravo_url("H12100099"),
        category="Digital services",
        note="Personal data processing, consent, subject rights and complaints.",
    ),
    BelarusSource(
        filename="by_tourism_law",
        title="Law on Tourism",
        url=pravo_url("H12100129"),
        category="Tourism and travel complaints",
        note="Tourism services, tour operators, guides and tourist rights context.",
    ),
    BelarusSource(
        filename="by_investments_law",
        title="Law on Investments",
        url=pravo_url("H11300053"),
        category="Business and investment",
        note="Investor rights, investment guarantees and investment activity context.",
    ),
    BelarusSource(
        filename="by_trade_food_service_law",
        title="Law on State Regulation of Trade and Public Catering",
        url=pravo_url("H11400128"),
        category="Business and consumer protection",
        note="Retail, catering, trade and practical consumer-commerce context.",
    ),
    BelarusSource(
        filename="by_information_protection_law",
        title="Law on Information, Informatization and Information Protection",
        url=pravo_url("H10800455"),
        category="Digital services",
        note="Information systems, access to information and information protection.",
    ),
    BelarusSource(
        filename="by_electronic_document_signature_law",
        title="Law on Electronic Document and Electronic Digital Signature",
        url=pravo_url("H10900113"),
        category="Digital services",
        note="Electronic documents, digital signatures and online transactions.",
    ),
    BelarusSource(
        filename="by_appeals_law",
        title="Law on Appeals of Citizens and Legal Entities",
        url=pravo_url("H11100300"),
        category="Administrative complaints",
        note="Administrative complaint/request format, deadlines and competent bodies.",
    ),
    BelarusSource(
        filename="by_documentation_population_decree",
        title="Decree on Documentation of the Population of Belarus",
        url=pravo_url("P30800294"),
        category="Immigration and citizenship",
        note="Passports and identity documents, useful for citizenship/passport questions.",
    ),
)


STATEMENT_TEMPLATE_TEXT = """Belarus statement and application templates for common bot questions.
These are practical drafting/checklist templates for Russian citizens and other foreigners. They are not official forms unless a competent Belarus authority publishes a specific form.

Section 1. Consumer complaint / demand letter against seller or service provider.
Use for defective goods, refund refusal, misleading service, online order, warranty dispute, delivery problem or paid service failure.
Source basis: Law on Protection of Consumer Rights; Civil Code; Law on State Regulation of Trade and Public Catering.
Template fields:
1. Consumer: full name, passport/ID if available, nationality, Belarus address/contact.
2. Seller/service provider: legal name, registration data if known, address, website/platform, phone/email.
3. Contract/order details: date, price, payment proof, invoice/order number.
4. Problem: defect, non-delivery, misleading information, unsafe service, refusal to refund.
5. Evidence: photos, chat, receipt, advertisement, warranty card, delivery record.
6. Demand: refund, replacement, repair, compensation, written explanation and deadline.
Draft wording:
I request that the seller/service provider resolve the consumer rights issue described above within the stated deadline. If no response is received, I reserve the right to submit a complaint to the competent Belarus authority and pursue available civil remedies.

Section 2. Tourism service complaint.
Use for hotel, tour operator, guide, transport, booking, overcharge or unsafe service problems in Belarus.
Source basis: Law on Tourism; Consumer Protection Law; Civil Code.
Template fields:
1. Tourist details: name, passport, nationality, contacts and itinerary dates.
2. Service provider: hotel/tour company/transport provider/platform.
3. Booking details: date, route, voucher, price, payment proof.
4. Incident description and harm.
5. Evidence and witnesses.
6. Requested remedy: refund, replacement service, compensation, written explanation.

Section 3. Police report for theft, fraud, assault, lost passport or property.
Use when a Russian citizen or foreigner needs a written incident report for police, embassy, insurer or migration authority.
Source basis: Criminal Code; Criminal Procedure Code; Law on the Legal Status of Foreigners.
Template fields:
1. Applicant: name, passport, nationality, visa/stay/residence details, Belarus address.
2. Incident: date, time, place, suspect if known, property/value, bank/cards/devices affected.
3. Evidence: photos, CCTV location, transaction records, witnesses, chats.
4. Requested action: register report, investigate, issue confirmation/case number/copy for embassy or insurer.
Draft wording:
I request registration of this report and a written confirmation/case reference for use with my embassy, insurer and migration authorities.

Section 4. Visa and migration checklist for a Russian citizen.
Use before entry, visa application, extension, registration, temporary stay or residence-planning question.
Source basis: Law on the Legal Status of Foreigners; citizenship/passport documentation rules; official Belarus migration practice.
Template fields:
1. Passport data: full name, date/place of birth, citizenship, passport number, issue/expiry date.
2. Trip data: arrival/departure dates, Belarus address, host/receiving party.
3. Purpose: tourism, business, work, study, family, treatment, investment or other.
4. Entry/stay basis: visa-free/EAEU travel, visa, temporary stay, temporary residence, permanent residence.
5. Registration/address duty: where the foreigner will live and who submits notification/registration.
Russian-specific notes:
Russian citizens often rely on Union State/EAEU rules rather than ordinary visa procedure, but must still track registration, permitted stay, residence and work rules when staying longer or changing purpose.

Section 5. Visa / stay application or correction request.
Use for visa, invitation, migration-registration error, missing document or authority/portal question.
Source basis: Law on the Legal Status of Foreigners; appeals law; administrative-offence procedure.
Template fields:
1. Application/invitation/registration number if any.
2. Applicant passport and travel purpose.
3. Incorrect or missing field and corrected value.
4. Host/inviting party details if applicable.
5. Attached documents and payment/portal evidence.
Draft wording:
I respectfully request review or correction of my Belarus visa/stay/registration matter using the accurate information and documents listed above.

Section 6. Temporary or permanent residence checklist.
Use for longer stay, family reunification, study, work, investment or residence status questions.
Source basis: Law on the Legal Status of Foreigners; Law on Citizenship; Decree on Documentation of the Population.
Template fields:
1. Current status and permitted stay deadline.
2. Residence ground: family, work, study, investment/business, humanitarian or other.
3. Address and housing proof.
4. Income/work/study documents.
5. Criminal-record/medical/insurance documents if required by authority.
6. Prior entries, registrations and administrative offences.

Section 7. Work / employment checklist for foreigner or Russian citizen.
Use for employment contract, work authorization, EAEU/Russian citizen question, employer documents or labour dispute.
Source basis: Labour Code; Law on External Labour Migration; Law on the Legal Status of Foreigners.
Template fields:
1. Worker data: citizenship, passport, residence/stay status, profession.
2. Employer data: legal name, address, contact, contract terms.
3. Work basis: EAEU/Russian citizen employment, permit requirement if any, contract, posting or service agreement.
4. Labour issue: unpaid wages, dismissal, unsafe work, contract mismatch, migration risk.
5. Evidence: contract, payslips, chats, timesheets, permit/registration documents.

Section 8. Administrative offence / fine response.
Use for migration, traffic, consumer, public-order or other administrative offence notices.
Source basis: Code on Administrative Offences; Procedural-Executive Code of Administrative Offences.
Template fields:
1. Person: name, passport, address, contact.
2. Notice/protocol details: authority, date, article, deadline.
3. Facts and objections.
4. Mitigating circumstances and evidence.
5. Requested action: terminate, reclassify, reduce fine, restore deadline, provide copies.

Section 9. Foreign real-estate purchase due-diligence checklist.
Use for apartment, house, land, lease, new-build, registration or seller/developer due diligence.
Source basis: Civil Code; Land Code; Housing Code; Law on State Registration of Immovable Property, Rights and Transactions.
Template fields:
1. Buyer: citizenship, passport, marital status, Belarus address/contact.
2. Property: address, cadastral/registration number, type, land plot if relevant.
3. Seller/developer: title documents, authority to sell, encumbrances, spouse consent/entity authority.
4. Contract: price, currency/payment route, handover, defects, penalties, registration duty.
5. Registry checks: ownership, restrictions, arrest, mortgage, lease, easements, utility debts.
Russian-specific risk checks:
Confirm whether the object includes land rights, whether foreign ownership restrictions apply, how payments can be made from Russia, whether notarization/registration is required, and whether tax/residency consequences arise.

Section 10. Real-estate registration / correction request.
Use for registration of ownership, correction of registry error, encumbrance removal or transaction registration.
Source basis: Law on State Registration of Immovable Property, Rights and Transactions; Civil Code; Land Code.
Template fields:
1. Applicant and representative data.
2. Property and registry identifier.
3. Requested registration/correction/removal.
4. Basis document: sale contract, inheritance, court act, mortgage discharge, power of attorney.
5. Attachments and payment proof.

Section 11. Civil claim / pre-trial demand.
Use for contract debt, damage, service failure, unjust enrichment, property dispute or compensation.
Source basis: Civil Code; Civil Procedure Code.
Template fields:
1. Claimant and respondent.
2. Contract/legal basis and timeline.
3. Amount claimed and calculation.
4. Evidence list.
5. Demand and deadline.
Draft wording:
I request voluntary settlement of the claim described above. If the demand is not satisfied, I reserve the right to file a claim with the competent court and seek costs and other remedies.

Section 12. Tax / payment-residency checklist.
Use for tax registration, income, rental income, business income, VAT, customs/payment questions.
Source basis: Tax Code, General and Special Parts; Civil Code.
Template fields:
1. Person/entity and residency facts.
2. Income or transaction type.
3. Dates, amounts, currency and payer/payee.
4. Belarus-source income indicators.
5. Documents: contracts, invoices, bank statements, tax notices.

Section 13. Digital service / e-commerce / information complaint.
Use for online store, platform, electronic document, signature, blocked access or information protection issue.
Source basis: Law on Information, Informatization and Information Protection; Law on Electronic Document and Digital Signature; Consumer Protection Law; Trade Law.
Template fields:
1. Platform/service and account/order details.
2. Issue: refusal, misleading info, invalid e-signature, inaccessible data, account block.
3. Evidence: screenshots, logs, emails, payment proof.
4. Requested action: restore access, correct data, confirm transaction, refund, preserve records.

Section 14. Appeal to Belarus state body.
Use for administrative request, complaint against official action/inaction, request for information or deadline issue.
Source basis: Law on Appeals of Citizens and Legal Entities.
Template fields:
1. Applicant identity and contact details.
2. Authority/addressee.
3. Facts and previous applications.
4. Legal interest and requested action.
5. Attachments and preferred response channel.

Section 15. Consular support request for Russian citizen.
Use for lost passport, detention, accident, death, emergency travel document, migration problem or document legalization.
Source basis: Law on the Legal Status of Foreigners; Criminal Procedure Code; Decree on Documentation of the Population.
Template fields:
1. Russian citizen identity and passport details.
2. Location and emergency facts.
3. Belarus authority involved, if any.
4. Needed support: confirmation, emergency travel document, contact with relatives/lawyer, copy of report.
5. Attachments and contact person.

Section 16. Marriage / family-status checklist.
Use for marriage registration, divorce, child issues, alimony, civil-status certificates or spouse consent.
Source basis: Code on Marriage and Family; Civil Code; Law on Appeals.
Template fields:
1. Parties: names, citizenship, passports, addresses, marital status.
2. Event: marriage, divorce, birth, child residence, alimony, certificate/correction.
3. Foreign documents: apostille/legalization, translation, validity period.
4. Belarus authority and requested action.
5. Russian-specific documents: internal/foreign passport, certificate of marital status if required, notarized translations.

Section 17. Citizenship / passport / statelessness checklist.
Use for Belarus citizenship, loss/termination, dual-citizenship risk, passport/documentation question, statelessness or child citizenship.
Source basis: Law on Citizenship; Decree on Documentation of the Population; Constitution.
Template fields:
1. Applicant and family citizenship history.
2. Birthplace, parents, marriage, residence and prior passports.
3. Existing foreign citizenship/residence permits.
4. Requested result: confirmation, acquisition, termination, passport/document action.
5. Evidence and risk flags: military duty, criminal/administrative cases, foreign residence notification.

Section 18. Personal data complaint.
Use for unlawful data collection, publication, refusal to correct/delete data, biometric/special data or platform leak.
Source basis: Law on Personal Data Protection; Law on Information; Criminal/Administrative liability context.
Template fields:
1. Data subject and controller/operator.
2. Data categories and processing purpose.
3. Violation: no consent, excessive data, refusal of access/correction/deletion, leak, unlawful disclosure.
4. Evidence: screenshots, notices, messages, URLs, account IDs.
5. Demand: access, correction, deletion, restriction, explanation, complaint to competent authority.

Section 19. Tourism service complaint / insurance checklist.
Use for package tour, hotel, guide, health resort, transport, accident, denied service or tourist insurance issue.
Source basis: Law on Tourism; Consumer Protection Law; Civil Code.
Template fields:
1. Tourist and booking data.
2. Service provider and route/service description.
3. Breach, loss, health/safety incident or cancellation.
4. Evidence and medical/insurance documents.
5. Remedy: refund, compensation, replacement service, written explanation, authority complaint.

Section 20. Investment / trade / e-commerce checklist.
Use for foreign investment, business participation, securities, online trade, catering/retail compliance or commercial dispute.
Source basis: Law on Investments; Civil Code; Law on State Regulation of Trade and Public Catering; Securities Market Law; Tax Code.
Template fields:
1. Investor/business participant and citizenship/residence.
2. Transaction: shares, company, real estate, services, online trade, securities, investment project.
3. Licensing/registration/notification checks.
4. Tax, currency/payment, sanctions/banking and beneficial-owner risk checks.
5. Documents: charter, registry extract, contract, payment proof, permits, correspondence.
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


def fetch_source(source: BelarusSource, timeout: float = 45.0) -> tuple[str, str]:
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
                if "404 Not Found" in text[:1000]:
                    raise ValueError("official page returned 404")
                if len(text) < 500:
                    raise ValueError(f"downloaded text is too short ({len(text)} chars)")
                return text, str(response.url)
            except Exception as exc:  # pragma: no cover - exercised by integration run
                last_error = exc

    raise RuntimeError(f"failed to fetch {source.filename}: {last_error}")


def split_to_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"(?is)(?<![A-Za-zА-Яа-я])(?:Статья|СТАТЬЯ|Section|SECTION|Article|ARTICLE)\s+"
        r"([0-9]+(?:[-/][0-9]+)?(?:[a-zа-я])?)"
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


def build_indexable_text(source: BelarusSource, text: str, resolved_url: str) -> str:
    sections = split_to_sections(text)
    blocks = [
        f"Belarus source: {source.title}",
        f"Category: {source.category}",
        f"Source URL: {resolved_url}",
        f"Note: {source.note or 'Reference text; verify against current official Belarus text.'}",
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
    imported: Iterable[tuple[BelarusSource, str, int]],
    failed: Iterable[tuple[BelarusSource, str]],
) -> str:
    imported_list = list(imported)
    failed_list = list(failed)
    lines = [
        f"Belarus legal sources registry ({date.today().isoformat()})",
        "Primary source is the National Legal Internet Portal of Belarus / NCLI services.",
        "Verify current legal force against official Belarus text before filing or court use.",
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
    (output_dir / "by_statement_templates.txt").write_text(STATEMENT_TEMPLATE_TEXT, encoding="utf-8")


def import_sources(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    imported: list[tuple[BelarusSource, str, int]] = []
    failed: list[tuple[BelarusSource, str]] = []

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
    (output_dir / "by_sources_registry_2026.txt").write_text(registry, encoding="utf-8")
    write_statement_templates(output_dir)
    return len(imported), len(failed)


if __name__ == "__main__":
    imported_count, failed_count = import_sources()
    print(f"Done: imported={imported_count}, failed={failed_count}")
