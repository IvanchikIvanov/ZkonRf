"""Импорт источников по ЗПП РФ в формат для индексации."""
import html
import re
from dataclasses import dataclass
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


SOURCES: List[Source] = [
    Source(
        filename="zpp_pravo_gov_portal",
        title="Официальный портал правовой информации",
        url="https://pravo.gov.ru/",
        category="Официальный источник",
    ),
    Source(
        filename="zpp_pravo_gov_codex",
        title="Раздел Кодексы на pravo.gov.ru",
        url="https://pravo.gov.ru/codex/",
        category="Официальный источник",
    ),
    Source(
        filename="zpp_law_2300_consultant",
        title="Закон РФ О защите прав потребителей № 2300-1 (Consultant+)",
        url="https://www.consultant.ru/document/cons_doc_LAW_305/",
        category="Базовый закон ЗоЗПП",
    ),
    Source(
        filename="zpp_law_2300_pravo_gov",
        title="Закон РФ О защите прав потребителей № 2300-1 (pravo.gov.ru)",
        url="https://pravo.gov.ru/proxy/ips/?docbody&nd=102014512",
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
    ),
    Source(
        filename="zpp_gk_rf_full",
        title="Гражданский кодекс РФ (полный)",
        url="https://www.consultant.ru/document/cons_doc_LAW_5142/",
        category="Кодексы РФ",
    ),
    Source(
        filename="zpp_koap_rf",
        title="КоАП РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_34661/",
        category="Кодексы РФ",
    ),
    Source(
        filename="zpp_gpk_rf",
        title="ГПК РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_39570/",
        category="Кодексы РФ",
    ),
    Source(
        filename="zpp_jk_rf",
        title="Жилищный кодекс РФ",
        url="https://www.consultant.ru/document/cons_doc_LAW_51057/",
        category="Кодексы РФ",
    ),
    Source(
        filename="zpp_pp_2463",
        title="Постановление Правительства РФ № 2463",
        url="https://www.consultant.ru/document/cons_doc_LAW_373622/",
        category="Подзаконные акты",
    ),
    Source(
        filename="zpp_184_fz_tech_reg",
        title="ФЗ № 184 О техническом регулировании",
        url="https://www.consultant.ru/document/cons_doc_LAW_34481/",
        category="Смежные законы",
    ),
    Source(
        filename="zpp_38_fz_ads_reference",
        title="Ссылка из списка пользователя: Закон о рекламе",
        url="https://www.consultant.ru/document/cons_doc_LAW_34481/",
        category="Смежные законы",
    ),
    Source(
        filename="zpp_353_fz_credit",
        title="ФЗ № 353 О потребительском кредите (займе)",
        url="https://www.consultant.ru/document/cons_doc_LAW_155986/",
        category="Смежные законы",
    ),
    Source(
        filename="zpp_rospotreb_npa_federal",
        title="Роспотребнадзор: федеральные НПА по ЗПП",
        url="https://zpp.rospotrebnadzor.ru/npa/federal",
        category="Реестры и перечни НПА",
    ),
    Source(
        filename="zpp_vs_plenum_17_2012",
        title="Пленум ВС РФ № 17 от 28.06.2012",
        url="https://www.consultant.ru/document/cons_doc_LAW_131885/",
        category="Судебная практика",
    ),
    Source(
        filename="zpp_gis_zpp_rospotreb",
        title="ГИС ЗПП Роспотребнадзора",
        url="https://zpp.rospotrebnadzor.ru/",
        category="Госресурсы",
    ),
    Source(
        filename="zpp_rospotreb_main",
        title="Официальный сайт Роспотребнадзора",
        url="https://rospotrebnadzor.ru/",
        category="Госресурсы",
    ),
    Source(
        filename="zpp_legalacts",
        title="LegalActs.ru: ЗоЗПП",
        url="https://legalacts.ru/doc/ZZPP/",
        category="Дополнительные ресурсы",
    ),
    Source(
        filename="zpp_cntd",
        title="CNTD: Закон РФ о защите прав потребителей",
        url="https://docs.cntd.ru/document/9005388",
        category="Дополнительные ресурсы",
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


def split_to_articles(text: str, source: Source, max_chars: int = 5500) -> str:
    """Разбивает текст на формат `Статья X.` для текущего парсера."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        normalized = f"Источник {source.title}. Не удалось извлечь текст с {source.url}."
    
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
            f"URL: {source.url}. Текст: {chunk}"
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


def download_text(client: httpx.Client, source: Source) -> str:
    """Скачивает и очищает текст документа."""
    last_error = None
    for attempt in range(1, 3):
        try:
            response = client.get(source.url, follow_redirects=True)
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
            return cleaned
        except Exception as exc:
            last_error = exc
            log.warning(
                f"Не удалось скачать {source.url} (попытка {attempt}/2): {exc}"
            )
    raise RuntimeError(f"Ошибка загрузки {source.url}: {last_error}")


def build_registry_file(codexes_ru_dir: Path, imported: List[Source], failed: List[Source]) -> None:
    """Создает индексный файл со всеми ссылками."""
    lines = []
    idx = 1
    lines.append("Статья 1. Сводный реестр источников по защите прав потребителей РФ на май 2026 года.")
    lines.append("")
    idx += 1
    
    for src in imported:
        lines.append(
            f"Статья {idx}. Загруженный источник. Категория: {src.category}. "
            f"Название: {src.title}. URL: {src.url}."
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
    
    imported: List[Source] = []
    failed: List[Source] = []
    
    timeout = httpx.Timeout(timeout=25.0, connect=10.0)
    with httpx.Client(timeout=timeout, verify=True) as client:
        for source in SOURCES:
            try:
                target_file = codexes_ru_dir / f"{source.filename}.txt"
                if target_file.exists() and target_file.stat().st_size > 2000:
                    imported.append(source)
                    log.info(f"Файл уже существует, пропускаем скачивание: {target_file.name}")
                    continue
                
                log.info(f"Загрузка: {source.title} ({source.url})")
                text = download_text(client, source)
                article_text = split_to_articles(text, source)
                target_file.write_text(article_text, encoding="utf-8")
                imported.append(source)
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
