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
    ThailandSource(
        filename="thai_revenue_code_title_1_general",
        title="Revenue Code, Title 1 General provisions",
        url="https://www.rd.go.th/english/37694.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_revenue_code_title_2_general",
        title="Revenue Code, Title 2 Revenue Taxes, Chapter 1 General provisions",
        url="https://www.rd.go.th/english/37698.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_revenue_code_assessment",
        title="Revenue Code, assessment tax procedures",
        url="https://www.rd.go.th/english/37744.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_revenue_code_income_tax",
        title="Revenue Code, income tax",
        url="https://www.rd.go.th/english/37748.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_revenue_code_vat",
        title="Revenue Code, value added tax",
        url="https://www.rd.go.th/english/37718.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_revenue_code_sbt",
        title="Revenue Code, specific business tax",
        url="https://www.rd.go.th/english/37752.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_revenue_code_stamp_duty",
        title="Revenue Code, stamp duty",
        url="https://www.rd.go.th/english/37758.html",
        category="Tax",
        note="Revenue Department English publication; Thai version controls for official use.",
    ),
    ThailandSource(
        filename="thai_land_code",
        title="Act Promulgating the Land Code B.E. 2497 (1954), update 2008",
        url="http://web.krisdika.go.th/data/outsitedata/outsite21/file/Act_Promulgating_the_Land_Code_BE_2497_(1954).pdf",
        category="Land and real estate",
        note="Office of the Council of State/Krisdika English reference translation.",
        alt_urls=("https://www.thailandlawonline.com/thai-real-estate-law/thai-land-law-land-code-act",),
    ),
    ThailandSource(
        filename="thai_condominium_act",
        title="Condominium Act B.E. 2522 (1979), 2008 amendment reference",
        url="https://www.dol.go.th/estate/Pages/act%202008.pdf",
        category="Land and real estate",
        note="Department of Lands-hosted English unofficial translation of the 2008 amendment reference.",
        alt_urls=("https://www.samuiforsale.com/law-texts/new-thailand-condominium-act-2008.html",),
    ),
    ThailandSource(
        filename="thai_labour_protection_act",
        title="Labour Protection Act B.E. 2541 (1998), revised 2019",
        url="https://area5.labour.go.th/attachments/article/192/2562.pdf",
        category="Labour",
        note="Ministry of Labour regional office PDF; English/Thai labour protection text.",
        alt_urls=("https://www.samuiforsale.com/law-texts/labour-protection-act.html",),
    ),
    ThailandSource(
        filename="thai_foreign_workers_emergency_decree",
        title="Royal Ordinance concerning Management of Employment of Foreign Workers B.E. 2560 (2017)",
        url="https://natlex.ilo.org/dyn/natlex2/r/natlex/fe/details?p3_isn=107728",
        category="Labour and immigration",
        note="ILO NATLEX record for foreign-worker management legislation.",
        alt_urls=("https://www.doe.go.th/prd/assets/upload/files/sukhothai_th/928cb9d2c6e07cd3e5812a43993a0fdd.pdf",),
    ),
    ThailandSource(
        filename="thai_immigration_act",
        title="Immigration Act B.E. 2522 (1979)",
        url="https://www.refworld.org/pdfid/46b2f9f42.pdf",
        category="Immigration",
        note="Refworld English translation; comments note later Thai amendments.",
        alt_urls=("https://www.samutprakanimmigration.go.th/downloads/Immigration_Act.pdf",),
    ),
    ThailandSource(
        filename="thai_foreign_business_act",
        title="Foreign Business Act B.E. 2542 (1999)",
        url="https://investmentpolicy.unctad.org/investment-laws/laws/589/print/3",
        category="Business and investment",
        note="UNCTAD Investment Policy Hub English text.",
        alt_urls=("https://www.boi.go.th/upload/Foreign%20Business%20Act_5dd766122ff27.pdf",),
    ),
    ThailandSource(
        filename="thai_tourism_business_and_guide_act",
        title="Tourism Business and Guide Act B.E. 2551 (2008)",
        url="http://web.krisdika.go.th/data/outsitedata/outsite21/file/TOURISM_BUSINESS_AND_GUIDE_ACT_B.E._2551.pdf",
        category="Tourism",
        note="Office of the Council of State/Krisdika English reference translation linked by BOI OSOS.",
        alt_urls=("https://osos.boi.go.th/One-Stop/faq-group/200/Setting-up-Tourism-Business/",),
    ),
    ThailandSource(
        filename="thai_hotel_act",
        title="Hotel Act B.E. 2547 (2004)",
        url="https://www.samuiforsale.com/law-texts/thailand-hotel-act-2004-translation.html",
        category="Tourism and accommodation",
        note="English reference translation; official Thai Royal Gazette text controls.",
    ),
    ThailandSource(
        filename="thai_air_navigation_act",
        title="Air Navigation Act B.E. 2497 (1954), consolidated English translation",
        url="https://www.caat.or.th/wp-content/uploads/2021/03/%E0%B8%84%E0%B8%B3%E0%B9%81%E0%B8%9B%E0%B8%A5%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%A3%E0%B8%B2%E0%B8%8A%E0%B8%9A%E0%B8%B1%E0%B8%8D%E0%B8%8D%E0%B8%B1%E0%B8%95%E0%B8%B4%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B9%80%E0%B8%94%E0%B8%B4%E0%B8%99%E0%B8%AD%E0%B8%B2%E0%B8%81%E0%B8%B2%E0%B8%A8-%E0%B8%9E.%E0%B8%A8.-2497-%E0%B9%81%E0%B8%81%E0%B9%89%E0%B9%84%E0%B8%82%E0%B9%80%E0%B8%9E%E0%B8%B4%E0%B9%88%E0%B8%A1%E0%B9%80%E0%B8%95%E0%B8%B4%E0%B8%A1%E0%B8%96%E0%B8%B6%E0%B8%87%E0%B8%89%E0%B8%9A%E0%B8%B1%E0%B8%9A%E0%B8%97%E0%B8%B5%E0%B9%88-14-%E0%B8%9E.%E0%B8%A8.2562.pdf",
        category="Transport",
        note="Civil Aviation Authority of Thailand consolidated English translation.",
        alt_urls=(
            "https://www.caat.or.th/wp-content/uploads/2021/03/New-English-Translation-Air-NavAct-14th-amended-Consolidated-Text-updated-Jan-2023-n.pdf",
            "https://doa.airports.go.th/th/gov_law/21/478.html",
        ),
    ),
    ThailandSource(
        filename="thai_land_traffic_act",
        title="Land Traffic Act B.E. 2522 (1979)",
        url="https://motogirlthailand.com/wp-content/uploads/2017/03/Thai_Traffic_Laws.pdf",
        category="Transport",
        note="English reference translation of Thai land traffic law.",
        alt_urls=("https://laksong.metro.police.go.th/api-console/public/media/a46c4c2c695fe181be951770868789091.pdf",),
    ),
    ThailandSource(
        filename="thai_visa_general_moscow_russians",
        title="Royal Thai Embassy in Moscow: general visa information",
        url="https://moscow.thaiembassy.org/en/page/84779-general-visa-information?menu=5d843dbc15e39c1abc00588d",
        category="Visa templates and checklists",
        note="Official Moscow embassy visa information, relevant to Russian citizens and residents.",
    ),
    ThailandSource(
        filename="thai_visa_tourist_moscow_russians",
        title="Royal Thai Embassy in Moscow: tourist visa requirements",
        url="https://moscow.thaiembassy.org/en/publicservice/83954-2-tourist-visa?cate=5d843b6a15e39c1abc0051a3",
        category="Visa templates and checklists",
        note="Official Moscow embassy tourist visa requirements and document checklist.",
    ),
    ThailandSource(
        filename="thai_visa_applying_moscow_russians",
        title="Royal Thai Embassy in Moscow: applying for a visa",
        url="https://moscow.thaiembassy.org/en/page/cate-7699-applying-for-a-visa?menu=5d843dba15e39c1abc005796",
        category="Visa templates and checklists",
        note="Official Moscow embassy visa category index for Russian applicants/residents.",
    ),
    ThailandSource(
        filename="thai_immigration_download_forms",
        title="Immigration forms: TM.7, TM.8, TM.30, TM.47 and related forms",
        url="https://www.samutprakanimmigration.go.th/download-forms/",
        category="Visa templates and checklists",
        note="Immigration-office forms page with extension, re-entry, 90-day reporting and residence certificate forms.",
    ),
    ThailandSource(
        filename="thai_foreign_condo_purchase_guide",
        title="Buying a condominium in Thailand as a foreigner",
        url="https://www.thailandlawonline.com/thai-real-estate-law/buying-a-condominium-in-thailand-as-a-foreigner-what-you-need-to-know",
        category="Foreign real estate",
        note="Practical foreign-condominium purchase guide cross-referencing Condominium Act requirements.",
    ),
    ThailandSource(
        filename="thai_condominium_act_foreign_ownership",
        title="Condominium Act foreign ownership rules and 2008 amendment text",
        url="https://www.samuiforsale.com/law-texts/new-thailand-condominium-act-2008.html",
        category="Foreign real estate",
        note="English reference translation of Condominium Act ownership provisions and amendments.",
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

Section 6. Visa application checklist for a Russian citizen applying through the Royal Thai Embassy in Moscow or Thai e-Visa.
Use for tourist visa, long-stay visa, DTV or other visa-route questions where the applicant is a Russian citizen or resident applying from Russia.
Source basis: Royal Thai Embassy in Moscow visa pages and official Thai e-Visa portal.
Template fields:
1. Applicant: full name as in passport, Russian passport number, date of birth, nationality, phone, email, current address.
2. Visa route: visa exemption, tourist visa, non-immigrant visa, Destination Thailand Visa, retirement, education, work, family, or other category.
3. Trip facts: expected entry date, length of stay, city/province in Thailand, accommodation, previous Thai entries and overstays if any.
4. Passport and identity documents: passport validity, passport bio page, photo, prior Thai visas/stamps.
5. Financial/travel evidence: bank statement, ticket/itinerary, hotel booking or invitation, insurance if required for the route, employment/self-employment or sponsor documents if relevant.
6. Russian-specific filing details: whether applying via Royal Thai Embassy in Moscow or Thai e-Visa, whether the applicant is physically in Russia/resident there, whether documents need translation.
7. Questions for embassy/visa support: confirm correct visa category, confirm required documents for Russian citizens, confirm processing time and fee, confirm whether visa exemption is enough for the planned stay.

Draft request:
Please confirm the appropriate Thai visa category for the applicant described above and the current document checklist for a Russian citizen/resident applying from Russia. The applicant requests confirmation before submission because the planned stay and purpose are as described in this statement.

Section 7. Extension of stay in Thailand (TM.7) checklist.
Use when a Russian citizen or other foreigner is already in Thailand and needs to extend permission to stay.
Source basis: Thai Immigration form TM.7 / immigration forms pages.
Template fields:
1. Applicant and passport details.
2. Current entry: date of entry, immigration checkpoint, visa type or visa-exempt entry, permitted-until date, TM.30/address status if available.
3. Requested extension: number of days/months, reason for extension, planned departure or continuing stay plan.
4. Address in Thailand: hotel/condo/house, landlord or manager contact, province immigration office.
5. Supporting documents: passport copies, entry stamp, photo, application form, fee receipt, accommodation evidence, TM.30 receipt if required locally, financial/sponsor/medical/school/work documents if relevant.
6. Risk flags: overstay risk, passport expiring soon, missing TM.30, multiple recent extensions, mismatch between visa purpose and actual activity.

Draft wording:
I request an extension of temporary stay in the Kingdom of Thailand for the reason and period stated above. I confirm that the address and supporting documents are accurate and that I understand the conditions of temporary stay.

Section 8. Re-entry permit (TM.8) checklist.
Use when a foreigner in Thailand has a current extension or permission to stay and needs to leave Thailand without losing that permission.
Source basis: Thai Immigration form TM.8 / immigration forms pages.
Template fields:
1. Applicant and passport details.
2. Current permission to stay: visa/extension type, permitted-until date, issuing immigration office.
3. Travel plan: departure date, return date, destination country, reason for travel.
4. Permit requested: single re-entry or multiple re-entry.
5. Supporting documents: passport, photo, copies of passport bio page, visa/extension stamp, departure card/entry record if applicable, application fee.

Draft wording:
I request a re-entry permit for the travel described above so that my current permission to stay in Thailand remains valid upon return.

Section 9. TM.30 address notification / 90-day report (TM.47) checklist.
Use for questions about address reporting, landlord/hotel reporting, or 90-day notification.
Source basis: Thai Immigration forms TM.30 and TM.47 / immigration forms pages.
Template fields for TM.30:
1. House owner, possessor, hotel manager or landlord details.
2. Foreigner details: name, nationality, passport, arrival date, visa/permission type.
3. Address: house/condo/hotel name, room/unit, district, province.
4. Evidence: passport copy, entry stamp, rental/booking evidence, owner/manager documents if required by local office.
Template fields for TM.47:
1. Foreigner details and passport.
2. Current address in Thailand.
3. Date of last entry and date when 90-day period is reached.
4. Prior 90-day receipt if any.

Section 10. Residence certificate request for visa, driving licence, bank, or property transaction.
Use when a foreigner needs proof of address in Thailand.
Source basis: immigration forms pages and local immigration practice.
Template fields:
1. Applicant identity and passport.
2. Purpose: driving licence, bank account, condominium purchase/transfer, vehicle purchase, school/work, other.
3. Address in Thailand and evidence of residence.
4. Supporting documents: passport copies, photo, TM.30/address evidence, lease or owner letter if available.
Draft wording:
I request a residence certificate confirming my current address in Thailand for the purpose stated above.

Section 11. Foreign condominium purchase due-diligence checklist for a Russian citizen.
Use before paying deposit or signing SPA/reservation for a Thai condominium.
Source basis: Condominium Act, Land Department materials and Thailand.go.th foreign-property guidance.
Template fields:
1. Buyer: Russian citizen passport details, Thai address/contact, source of funds.
2. Unit/project: project name, juristic person, room/unit number, floor, area, title details, seller/developer details.
3. Foreign quota: written confirmation that the unit can be transferred under the foreign ownership quota and that total foreign ownership does not exceed the legal limit.
4. Funds: foreign currency remittance evidence, bank letter/FET or equivalent bank certificate, sender/beneficiary consistency with buyer and purchase price.
5. Title and encumbrances: land office title search, mortgage/lease/servitude/litigation check, developer permits for new projects.
6. Contract review: price, deposit, transfer date, taxes/fees split, default clauses, refund conditions, furniture list, sinking fund/common fee, handover defects.
7. Russian-specific risk checks: payment route from Russian bank or third country, sanctions/bank transfer delays, currency conversion evidence, Russian tax/currency-control advice if needed.
8. Requested action: review documents, confirm foreign freehold eligibility, identify missing documents before deposit/transfer.

Draft request:
Please review the condominium transaction described above before payment or transfer. The key issues are foreign quota eligibility, clean title, lawful foreign-source funds evidence, contract risks, and documents required at the Land Office for registration in the buyer's name.

Section 12. Foreign real-estate lease / villa / house-on-land checklist.
Use when a foreigner, including a Russian citizen, wants to lease land/house/villa or structure a long-term residence without owning land.
Source basis: Land Code, Civil and Commercial Code lease rules, Thailand.go.th foreign land-ownership guidance.
Template fields:
1. Lessee/buyer: passport, nationality, Thai address/contact.
2. Property: land title type, owner, location, buildings, access road, utilities, zoning or hotel/villa-use issues.
3. Legal structure: lease term, renewal promises, usufruct/superficies/servitude if proposed, company/nominee structure warning.
4. Registration: whether lease over three years must be registered at Land Office, taxes/fees, who signs and pays.
5. Due diligence: owner title, mortgages/encumbrances, spouse consent, building permits, access rights, developer/agent authority.
6. Risk flags: nominee Thai company, promise of foreign land ownership, unregistered long lease, unclear renewal, prepaid rent without registration, land title below Chanote/Nor Sor 3 Gor.

Draft request:
Please review the proposed lease/property structure for compliance with Thai restrictions on foreign land ownership and identify documents needed before signing or paying deposit.

Section 13. Complaint or demand letter to real-estate agent, developer, landlord, or seller.
Use for deposit refusal, misleading foreign-quota promise, construction defect, delayed transfer, rental deposit dispute, or failed property service.
Recipient: agent/developer/landlord/seller, with possible escalation to consumer/tourism/land-office/lawyer channels depending on facts.
Template fields:
1. Claimant and respondent details.
2. Contract/reservation/lease details: date, property, unit, amount paid, payment proof.
3. Misconduct/problem: failure to transfer, false foreign-quota statement, defect, delay, refusal to refund deposit, unauthorized fee, missing documents.
4. Evidence: reservation form, SPA/lease, receipts, chats, advertisements, photos, Land Office or juristic person letters.
5. Legal basis to mention: consumer protection/unfair terms, Civil and Commercial Code contract principles, Condominium Act foreign ownership rules where relevant.
6. Demand: refund, document delivery, repair, transfer by date, cancellation, compensation, written explanation.
7. Deadline and escalation: set a reasonable response date and reserve rights to file complaint or seek legal action.

Draft wording:
I request that you resolve the issue described above by the stated deadline. If no satisfactory response is received, I reserve all rights to submit complaints to the competent Thai authorities and to seek legal remedies.
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
