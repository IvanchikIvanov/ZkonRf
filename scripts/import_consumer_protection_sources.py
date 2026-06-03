"""Импорт источников по ЗПП РФ в формат для индексации."""
import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import httpx

from bot.utils.config import settings
from bot.utils.logger import log


@dataclass
class Source:
    filename: str
    title: str
    url: str
    category: str
    alt_urls: tuple[str, ...] = field(default_factory=tuple)


# Отдельного «Налогового процессуального кодекса» в РФ нет: процессуальные нормы в НК РФ (zpp_nk_rf_part1/2).
SOURCES: List[Source] = [
    Source(
        filename="zpp_pravo_gov_portal",
        title="Официальный портал правовой информации (publication.pravo.gov.ru; HTTP — при сбое TLS на HTTPS)",
        url="https://publication.pravo.gov.ru/",
        category="Официальный источник",
        alt_urls=(
            "http://publication.pravo.gov.ru/",
            "https://zpp.rospotrebnadzor.ru/",
        ),
    ),
    Source(
        filename="zpp_pravo_gov_codex",
        title="Раздел кодексов (pravo.gov.ru; HTTP — при сбое TLS на HTTPS)",
        url="http://publication.pravo.gov.ru/search",
        category="Официальный источник",
        alt_urls=("https://www.consultant.ru/law/ref/", "https://sudact.ru/law/koap/"),
    ),
    Source(
        filename="zpp_law_2300_consultant",
        title="Закон РФ О защите прав потребителей № 2300-1 (Consultant+)",
        url="https://www.consultant.ru/document/cons_doc_LAW_305/",
        category="Базовый закон ЗоЗПП",
        alt_urls=("https://sudact.ru/law/zakon-rf-ot-07021992-n-2300-1-o/",),
    ),
    Source(
        filename="zpp_law_2300_pravo_gov",
        title="Закон РФ О защите прав потребителей № 2300-1 (замена: СудАкт; pravo.gov.ru с этой сети недоступен)",
        url="https://sudact.ru/law/zakon-rf-ot-07021992-n-2300-1-o/",
        category="Базовый закон ЗоЗПП",
    ),
    Source(
        filename="zpp_law_2300_garant",
        title="Закон РФ О защите прав потребителей № 2300-1 (Гарант)",
        url="https://base.garant.ru/10106035/",
        category="Базовый закон ЗоЗПП",
    ),
    Source(
        filename="zpp_gk_rf_part2",
        title="Гражданский кодекс РФ (часть 2)",
        url="https://www.consultant.ru/document/cons_doc_LAW_9027/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/gk-rf-chast2/",),
    ),
    Source(
        filename="zpp_gk_rf_full",
        title="Гражданский кодекс РФ (полный)",
        url="https://www.consultant.ru/document/cons_doc_LAW_5142/",
        category="Кодексы РФ",
        alt_urls=(
            "https://sudact.ru/law/gk-rf-chast1/",
            "https://sudact.ru/law/gk-rf-chast2/",
        ),
    ),
    Source(
        filename="zpp_koap_rf",
        title="КоАП РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_34661/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/koap/",),
    ),
    Source(
        filename="zpp_uk_rf",
        title="Уголовный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_10699/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/uk-rf/",),
    ),
    Source(
        filename="zpp_apk_rf",
        title="Арбитражный процессуальный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_37800/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/apk-rf/",),
    ),
    Source(
        filename="zpp_nk_rf_part1",
        title="Налоговый кодекс РФ (часть первая, 146-ФЗ)",
        url="https://www.consultant.ru/document/cons_doc_LAW_19671/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/nk-rf-chast1/",),
    ),
    Source(
        filename="zpp_nk_rf_part2",
        title="Налоговый кодекс РФ (часть вторая, 117-ФЗ)",
        url="https://www.consultant.ru/document/cons_doc_LAW_28165/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/nk-rf-chast2/",),
    ),
    Source(
        filename="zpp_gpk_rf",
        title="ГПК РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_39570/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/gpk-rf/",),
    ),
    Source(
        filename="zpp_jk_rf",
        title="Жилищный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_51057/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/zhk-rf/",),
    ),
    Source(
        filename="zpp_upk_rf",
        title="Уголовно-процессуальный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_34481/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/upk-rf/",),
    ),
    Source(
        filename="zpp_kas_rf",
        title="Кодекс административного судопроизводства РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_176147/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/kas-rf/",),
    ),
    Source(
        filename="zpp_zk_rf",
        title="Земельный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_33773/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/zemelnyi-kodeks/",),
    ),
    Source(
        filename="zpp_tk_rf",
        title="Трудовой кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_34683/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/tk-rf/",),
    ),
    Source(
        filename="zpp_sk_rf",
        title="Семейный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_8982/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/sk-rf/",),
    ),
    Source(
        filename="zpp_bk_rf",
        title="Бюджетный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_19702/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/bk-rf/",),
    ),
    Source(
        filename="zpp_vk_rf",
        title="Водный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_60683/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/vodnyi-kodeks/",),
    ),
    Source(
        filename="zpp_grk_rf",
        title="Градостроительный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_525518/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/gradostroitelnyi-kodeks/",),
    ),
    Source(
        filename="zpp_les_kod_rf",
        title="Лесной кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_64299/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/lesnoi-kodeks-rossiiskoi-federatsii-ot-04122006-n/",),
    ),
    Source(
        filename="zpp_uik_rf",
        title="Уголовно-исполнительный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_12940/",
        category="Кодексы РФ",
        alt_urls=("https://sudact.ru/law/uik-rf/",),
    ),
    Source(
        filename="zpp_konst_rf",
        title="Конституция Российской Федерации",
        url="https://www.consultant.ru/document/cons_doc_LAW_28399/",
        category="Кодексы РФ",
        alt_urls=("https://base.garant.ru/12138275/",),
    ),
    Source(
        filename="zpp_pp_2463",
        title="Постановление Правительства РФ № 2463",
        url="https://www.consultant.ru/document/cons_doc_LAW_373622/",
        category="Подзаконные акты",
        alt_urls=("https://sudact.ru/law/postanovlenie-pravitelstva-rf-ot-31122020-n-2463/postanovlenie/",),
    ),
    Source(
        filename="zpp_184_fz_tech_reg",
        title="ФЗ № 184 О техническом регулировании",
        url="https://www.consultant.ru/document/cons_doc_LAW_512697/",
        category="Смежные законы",
        alt_urls=("https://sudact.ru/law/federalnyi-zakon-ot-27122002-n-184-fz-o/",),
    ),
    Source(
        filename="zpp_38_fz_ads_reference",
        title="Ссылка из списка пользователя: Закон о рекламе",
        url="https://www.consultant.ru/document/cons_doc_LAW_58968/",
        category="Смежные законы",
        alt_urls=("https://sudact.ru/law/federalnyi-zakon-ot-13032006-n-38-fz-o/",),
    ),
    Source(
        filename="zpp_353_fz_credit",
        title="ФЗ № 353 О потребительском кредите (займе)",
        url="https://www.consultant.ru/document/cons_doc_LAW_155986/",
        category="Смежные законы",
        alt_urls=("https://sudact.ru/law/federalnyi-zakon-ot-21122013-n-353-fz-o/",),
    ),
    Source(
        filename="zpp_rospotreb_npa_federal",
        title="Роспотребнадзор: федеральные НПА по ЗПП",
        url="https://zpp.rospotrebnadzor.ru/npa/federal",
        category="Реестры и перечни НПА",
    ),
    Source(
        filename="zpp_152_fz_personal_data",
        title="ФЗ № 152 О персональных данных",
        url="https://www.consultant.ru/document/cons_doc_LAW_61801/",
        category="Смежные законы: цифровые услуги и персональные данные",
    ),
    Source(
        filename="zpp_149_fz_information",
        title="ФЗ № 149 Об информации, информационных технологиях и о защите информации",
        url="https://www.consultant.ru/document/cons_doc_LAW_61798/",
        category="Смежные законы: цифровые услуги и персональные данные",
    ),
    Source(
        filename="zpp_54_fz_cash_registers",
        title="ФЗ № 54 О применении контрольно-кассовой техники",
        url="https://www.consultant.ru/document/cons_doc_LAW_42359/",
        category="Смежные законы: торговля и расчеты",
    ),
    Source(
        filename="zpp_381_fz_trade",
        title="ФЗ № 381 Об основах государственного регулирования торговой деятельности",
        url="https://www.consultant.ru/document/cons_doc_LAW_95629/",
        category="Смежные законы: торговля и розница",
    ),
    Source(
        filename="zpp_395_1_banks",
        title="Закон РФ № 395-1 О банках и банковской деятельности",
        url="https://www.consultant.ru/document/cons_doc_LAW_5842/",
        category="Смежные законы: банки и платежи",
    ),
    Source(
        filename="zpp_161_fz_payment_system",
        title="ФЗ № 161 О национальной платежной системе",
        url="https://www.consultant.ru/document/cons_doc_LAW_115625/",
        category="Смежные законы: банки и платежи",
    ),
    Source(
        filename="zpp_230_fz_debt_collection",
        title="ФЗ № 230 О защите прав физлиц при взыскании просроченной задолженности",
        url="https://www.consultant.ru/document/cons_doc_LAW_200497/",
        category="Смежные законы: кредиты и взыскание",
        alt_urls=("https://legalacts.ru/doc/federalnyi-zakon-ot-03072016-n-230-fz-o/",),
    ),
    Source(
        filename="zpp_151_fz_microfinance",
        title="ФЗ № 151 О микрофинансовой деятельности и микрофинансовых организациях",
        url="https://www.consultant.ru/document/cons_doc_LAW_102112/",
        category="Смежные законы: кредиты и МФО",
    ),
    Source(
        filename="zpp_127_fz_bankruptcy",
        title="ФЗ № 127 О несостоятельности (банкротстве)",
        url="https://www.consultant.ru/document/cons_doc_LAW_39331/",
        category="Смежные законы: долги и банкротство",
    ),
    Source(
        filename="zpp_40_fz_osago",
        title="ФЗ № 40 Об обязательном страховании гражданской ответственности владельцев транспортных средств",
        url="https://www.consultant.ru/document/cons_doc_LAW_36528/",
        category="Смежные законы: страхование",
    ),
    Source(
        filename="zpp_4015_1_insurance",
        title="Закон РФ № 4015-1 Об организации страхового дела в Российской Федерации",
        url="https://www.consultant.ru/document/cons_doc_LAW_1307/",
        category="Смежные законы: страхование",
    ),
    Source(
        filename="zpp_214_fz_shared_construction",
        title="ФЗ № 214 Об участии в долевом строительстве",
        url="https://www.consultant.ru/document/cons_doc_LAW_51038/",
        category="Смежные законы: жилье и строительство",
    ),
    Source(
        filename="zpp_273_fz_education",
        title="ФЗ № 273 Об образовании в Российской Федерации",
        url="https://www.consultant.ru/document/cons_doc_LAW_140174/",
        category="Смежные законы: платные услуги",
    ),
    Source(
        filename="zpp_323_fz_health",
        title="ФЗ № 323 Об основах охраны здоровья граждан в Российской Федерации",
        url="https://www.consultant.ru/document/cons_doc_LAW_121895/",
        category="Смежные законы: платные медицинские услуги",
    ),
    Source(
        filename="zpp_air_code_rf",
        title="Воздушный кодекс Российской Федерации",
        url="https://www.consultant.ru/document/cons_doc_LAW_13744/",
        category="Кодексы РФ: перевозки",
    ),
    Source(
        filename="zpp_18_fz_railway_transport_charter",
        title="ФЗ № 18 Устав железнодорожного транспорта Российской Федерации",
        url="https://www.consultant.ru/document/cons_doc_LAW_40444/",
        category="Смежные законы: перевозки",
    ),
    Source(
        filename="zpp_229_fz_enforcement",
        title="ФЗ № 229 Об исполнительном производстве",
        url="https://www.consultant.ru/document/cons_doc_LAW_71450/",
        category="Смежные законы: исполнение решений и взыскание",
    ),
    Source(
        filename="zpp_rospotreb_npa_regional",
        title="Роспотребнадзор: региональные НПА по ЗПП и иным обязательным требованиям (поддомен ЗПП)",
        url="https://zpp.rospotrebnadzor.ru/npa/regional",
        category="Реестры и перечни НПА",
    ),
    Source(
        filename="zpp_52_fz_sanitary_epidemiological",
        title='Федеральный закон № 52-ФЗ "О санитарно-эпидемиологическом благополучии населения" (Consultant+)',
        url="https://www.consultant.ru/document/cons_doc_LAW_511660/",
        category="Санитарное законодательство и СанПиН",
        alt_urls=("https://base.garant.ru/12125253/",),
    ),
    Source(
        filename="zpp_sp_213678_retail_services",
        title="СП 2.1.3678-20: требования при продаже товаров, работах, услугах (помещения, торговля, быт, гостиницы и др.; СудАкт)",
        url="https://sudact.ru/law/postanovlenie-glavnogo-gosudarstvennogo-sanitarnogo-vracha-rf-ot_1363/",
        category="Санитарное законодательство и СанПиН",
    ),
    Source(
        filename="zpp_sanpin_2343590_public_catering",
        title="СанПиН 2.3/2.4.3590-20: общественное питание, производственный контроль и принципы ХАССП в санитарных нормах (СудАкт)",
        url="https://sudact.ru/law/postanovlenie-glavnogo-gosudarstvennogo-sanitarnogo-vracha-rf-ot_1355/",
        category="Санитарное законодательство и СанПиН",
    ),
    Source(
        filename="zpp_sanpin_21368421_settlements_premises",
        title="СанПиН 2.1.3684-21: территории, вода, воздух, жилые и общественные помещения, мероприятия (СудАкт)",
        url="https://sudact.ru/law/postanovlenie-glavnogo-gosudarstvennogo-sanitarnogo-vracha-rf-ot_1364/",
        category="Санитарное законодательство и СанПиН",
    ),
    Source(
        filename="zpp_gost_r_51705_haccp",
        title="ГОСТ Р 51705.1-2024: системы менеджмента на основе принципов ХАССП для пищевой продукции (Гарант; полный текст может требовать подписки)",
        url="https://base.garant.ru/409077162/",
        category="ХАССП и пищевая безопасность",
    ),
    Source(
        filename="zpp_tr_ts_021_food_safety",
        title="ТР ТС 021/2011 О безопасности пищевой продукции (СудАкт; альтернатива Consultant по расписанию)",
        url="https://sudact.ru/law/reshenie-komissii-tamozhennogo-soiuza-ot-09122011-n_2/tr-ts-0212011/",
        category="ХАССП и пищевая безопасность",
        alt_urls=("https://www.consultant.ru/document/cons_doc_LAW_124768/",),
    ),
    Source(
        filename="zpp_vs_plenum_17_2012",
        title="Пленум ВС РФ № 17 от 28.06.2012",
        url="https://www.consultant.ru/document/cons_doc_LAW_131885/",
        category="Судебная практика",
        alt_urls=("https://sudact.ru/law/postanovlenie-plenuma-verkhovnogo-suda-rf-ot-28062012/",),
    ),
    Source(
        filename="zpp_gis_zpp_rospotreb",
        title="ГИС ЗПП Роспотребнадзора",
        url="https://zpp.rospotrebnadzor.ru/",
        category="Госресурсы",
    ),
    Source(
        filename="zpp_rospotreb_main",
        title="Информация Роспотребнадзора для потребителя (поддомен ЗПП; rospotrebnadzor.ru с этой сети недоступен)",
        url="https://zpp.rospotrebnadzor.ru/npa/global",
        category="Госресурсы",
    ),
    Source(
        filename="zpp_legalacts",
        title="LegalActs.ru: ЗоЗПП",
        url="https://legalacts.ru/doc/ZZPP/",
        category="Дополнительные ресурсы",
        alt_urls=("https://www.consultant.ru/document/cons_doc_LAW_305/",),
    ),
    Source(
        filename="zpp_cntd",
        title="CNTD: Закон РФ о защите прав потребителей (замена: Consultant+; docs.cntd.ru с этой сети недоступен)",
        url="https://www.consultant.ru/document/cons_doc_LAW_305/",
        category="Дополнительные ресурсы",
        alt_urls=("https://sudact.ru/law/zakon-rf-ot-07021992-n-2300-1-o/",),
    ),
    Source(
        filename="zpp_sudact",
        title="СудАкт: Закон РФ о защите прав потребителей",
        url="https://sudact.ru/law/zakon-rf-ot-07021992-n-2300-1-o/",
        category="Дополнительные ресурсы",
    ),
]


def strip_html(raw_html: str) -> str:
    """Преобразует HTML в плоский читаемый текст."""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw_html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|h5|h6|br|tr|td|th)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_relevant_text(text: str) -> str:
    """Берет наиболее полезную часть текста для индексации."""
    markers = [
        "Статья 1",
        "Глава 1",
        "РАЗДЕЛ I",
        "Раздел I",
        "Федеральный закон",
        "ЗАКОН",
    ]
    starts = [text.find(marker) for marker in markers if marker in text]
    if starts:
        start = min(idx for idx in starts if idx >= 0)
        return text[start:]
    return text


def split_to_articles(text: str, source: Source, fetched_url: str, max_chars: int = 5500) -> str:
    """Разбивает текст на формат `Статья X.` для текущего парсера."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        normalized = f"Источник {source.title}. Не удалось извлечь текст с {fetched_url}."
    
    chunks = []
    cursor = 0
    length = len(normalized)
    while cursor < length:
        end = min(cursor + max_chars, length)
        if end < length:
            boundary = normalized.rfind(". ", cursor, end)
            if boundary > cursor + 500:
                end = boundary + 1
        chunk = normalized[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        cursor = end
    
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"Статья {idx}. Источник: {source.title}. Категория: {source.category}. "
            f"URL: {fetched_url}. Текст: {chunk}"
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def detect_encoding(response: httpx.Response) -> str:
    """Определяет кодировку ответа по content-type или meta."""
    content_type = response.headers.get("content-type", "").lower()
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip()
        if charset:
            return charset
    return "utf-8"


def _pravo_http_fallback(url: str) -> str | None:
    """Для publication.pravo.gov.ru / pravo.gov.ru: зеркало на http (TLS в части окружений падает)."""
    if url.startswith("https://publication.pravo.gov.ru"):
        return "http://publication.pravo.gov.ru" + url[len("https://publication.pravo.gov.ru") :]
    if url.startswith("https://www.pravo.gov.ru"):
        return "http://www.pravo.gov.ru" + url[len("https://www.pravo.gov.ru") :]
    if url.startswith("https://pravo.gov.ru"):
        return "http://pravo.gov.ru" + url[len("https://pravo.gov.ru") :]
    return None


def download_text(client: httpx.Client, source: Source) -> tuple[str, str]:
    """Скачивает и очищает текст документа. Перебирает url и alt_urls."""
    urls = (source.url,) + source.alt_urls
    last_error = None
    for fetch_url in urls:
        for attempt in range(1, 4):
            try:
                response = client.get(fetch_url, follow_redirects=True)
                response.raise_for_status()
                encoding = detect_encoding(response)
                try:
                    raw_html = response.content.decode(encoding, errors="replace")
                except Exception:
                    raw_html = response.text
                cleaned = strip_html(raw_html)
                cleaned = extract_relevant_text(cleaned)
                if len(cleaned) < 200:
                    raise ValueError("Слишком мало текста после очистки")
                bad_page_markers = (
                    "Федеральный закон \"О полиции\" N 3-ФЗ",
                    "Контактная информация 117292",
                    "Сайт использует файлы cookies",
                )
                if any(marker in cleaned for marker in bad_page_markers):
                    raise ValueError("Получена служебная страница вместо текста документа")
                if fetch_url != source.url:
                    log.info(f"Использован альтернативный URL для {source.filename}: {fetch_url}")
                return cleaned, fetch_url
            except Exception as exc:
                last_error = exc
                log.warning(
                    f"Не удалось скачать {fetch_url} (попытка {attempt}/3, источник {source.filename}): {exc}"
                )
                alt_http = _pravo_http_fallback(fetch_url)
                if alt_http and alt_http != fetch_url:
                    try:
                        response = client.get(alt_http, follow_redirects=True)
                        response.raise_for_status()
                        encoding = detect_encoding(response)
                        try:
                            raw_html = response.content.decode(encoding, errors="replace")
                        except Exception:
                            raw_html = response.text
                        cleaned = strip_html(raw_html)
                        cleaned = extract_relevant_text(cleaned)
                        if len(cleaned) < 200:
                            raise ValueError("Слишком мало текста после очистки")
                        log.info(f"Использован HTTP-fallback pravo.gov для {source.filename}: {alt_http}")
                        return cleaned, alt_http
                    except Exception as exc2:
                        last_error = exc2
                        log.warning(f"HTTP-fallback pravo также не удался: {exc2}")
    raise RuntimeError(f"Ошибка загрузки {source.filename} (все URL исчерпаны): {last_error}")


def build_registry_file(
    codexes_ru_dir: Path,
    imported: List[tuple[Source, str]],
    failed: List[Source],
) -> None:
    """Создает индексный файл со всеми ссылками (URL — фактически загруженный, если отличался)."""
    lines = []
    idx = 1
    lines.append("Статья 1. Сводный реестр источников по защите прав потребителей РФ на май 2026 года.")
    lines.append("")
    idx += 1
    
    for src, reg_url in imported:
        detail = ""
        if reg_url != src.url:
            detail = f" Первичный URL: {src.url}."
        lines.append(
            f"Статья {idx}. Загруженный источник. Категория: {src.category}. "
            f"Название: {src.title}. URL: {reg_url}.{detail}"
        )
        lines.append("")
        idx += 1
    
    for src in failed:
        lines.append(
            f"Статья {idx}. Источник добавлен в реестр, но автоматическое скачивание не удалось. "
            f"Категория: {src.category}. Название: {src.title}. URL: {src.url}."
        )
        lines.append("")
        idx += 1
    
    registry_path = codexes_ru_dir / "ru_zpp_sources_registry_2026.txt"
    registry_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    log.info(f"Создан индексный файл: {registry_path}")


def import_sources() -> None:
    """Скачивает источники и сохраняет в `data/codexes/ru`."""
    codexes_dir = Path(settings.database_path_resolved.parent / "codexes")
    codexes_ru_dir = codexes_dir / "ru"
    codexes_ru_dir.mkdir(parents=True, exist_ok=True)
    
    imported: List[tuple[Source, str]] = []
    failed: List[Source] = []
    
    timeout = httpx.Timeout(timeout=60.0, connect=30.0)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:128.0) Gecko/20100101 Firefox/128.0"
    }
    with httpx.Client(timeout=timeout, verify=True, headers=headers) as client:
        for source in SOURCES:
            try:
                target_file = codexes_ru_dir / f"{source.filename}.txt"
                if target_file.exists() and target_file.stat().st_size > 2000:
                    imported.append((source, source.url))
                    log.info(f"Файл уже существует, пропускаем скачивание: {target_file.name}")
                    continue
                
                log.info(f"Загрузка: {source.title} ({source.url})")
                text, fetched_url = download_text(client, source)
                article_text = split_to_articles(text, source, fetched_url)
                target_file.write_text(article_text, encoding="utf-8")
                imported.append((source, fetched_url))
                log.info(
                    f"Сохранен файл {target_file.name}: {len(article_text)} символов"
                )
            except Exception as exc:
                failed.append(source)
                log.error(f"Пропуск источника {source.title}: {exc}")
    
    build_registry_file(codexes_ru_dir, imported, failed)
    log.info(
        f"Импорт завершен. Успешно: {len(imported)}, с ошибкой: {len(failed)}"
    )


if __name__ == "__main__":
    import_sources()
