"""Полные тексты НПА с ГИС ЗПП (zpp.rospotrebnadzor.ru) через API сетки и файлы/страницы.

Федеральные (ModuleId=13): строка грида -> GET /npa/federal/{id} -> 302 на /Show/File/{fid} -> doc/docx/pdf.
Региональные (ModuleId=27): строка грида -> GET /npa/regional/{id} -> HTML с блоками .content-intro и .content-full.

Опционально: официальные PDF с publication.pravo.gov.ru (HTTP обходит часть TLS-проблем в контейнерах).

Запуск из корня репозитория:
  python -m scripts.fetch_zpp_npa_fulltext
  ZPP_REGIONAL_MAX=150 python -m scripts.fetch_zpp_npa_fulltext
"""
from __future__ import annotations

import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import logging

import httpx

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from scripts.import_consumer_protection_sources import (
    Source,
    split_to_articles,
    strip_html,
)

ZPP_BASE = "https://zpp.rospotrebnadzor.ru"
PRAVO_PUB_HTTP = "http://publication.pravo.gov.ru"

# (filename_suffix, eo_number, human_title)
PRAVO_OFFICIAL_PDFS: List[Tuple[str, str, str]] = [
    (
        "zpp_pravo_official_pdf_pp_ggsv_20260212",
        "0001202602270023",
        "Официальное опубликование (PDF): ПП ГГСВ РФ от 12.02.2026 № 2 (изм. СанПиН 2.1.3684-21 и СП 2.2.3670-20)",
    ),
]


def _extract_docx_plain(data: bytes) -> str:
    """Текст из docx без python-docx (достаточно для НПА)."""
    buf: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        if "word/document.xml" not in zf.namelist():
            return ""
        root = ET.fromstring(zf.read("word/document.xml"))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        for node in root.iter(f"{ns}t"):
            if node.text:
                buf.append(node.text)
            if node.tail:
                buf.append(node.tail)
    text = "".join(buf)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_pdf_plain(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: List[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t.strip())
    return "\n\n".join(parts).strip()


def extract_attachment_text(data: bytes, content_type: str) -> str:
    ct = (content_type or "").lower()
    if data[:4] == b"%PDF" or "pdf" in ct:
        t = _extract_pdf_plain(data)
        if len(t.strip()) < 20 and len(data) > 500:
            return (
                "[PDF: текстовый слой не извлечён (вероятно скан); файл доступен по ссылке в метаданных источника.] "
                f"Размер файла: {len(data)} байт."
            )
        return t
    if data.startswith(b"{\x5crtf"):
        return data.decode("cp1251", errors="replace")
    if data[:2] == b"PK" and b"word/" in data[:2000]:
        return _extract_docx_plain(data)
    # Старый .doc бинарный — как текст не трогаем
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def fetch_grid_page(
    client: httpx.Client, module_id: int, page_index: int, page_size: int = 80
) -> Dict[str, Any]:
    r = client.get(
        f"{ZPP_BASE}/Core/Content/GetGridData",
        params={
            "ModuleId": module_id,
            "pageIndex": page_index,
            "pageSize": page_size,
        },
    )
    r.raise_for_status()
    return r.json()


def resolve_federal_file_id(client: httpx.Client, row_id: str) -> Optional[int]:
    r = client.get(
        f"{ZPP_BASE}/npa/federal/{row_id}",
        follow_redirects=False,
    )
    if r.status_code in (301, 302):
        loc = r.headers.get("location") or ""
        m = re.search(r"/Show/File/(\d+)", loc, re.I)
        if m:
            return int(m.group(1))
    if r.status_code == 200:
        m = re.search(r'href="(/Show/File/\d+)', r.text, re.I)
        if m:
            m2 = re.search(r"/Show/File/(\d+)", m.group(1), re.I)
            if m2:
                return int(m2.group(1))
    return None


def extract_regional_act_text(client: httpx.Client, row_id: str) -> Tuple[str, str]:
    """Текст регионального НПА: HTML-карточка или файл по редиректу."""
    r = client.get(
        f"{ZPP_BASE}/npa/regional/{row_id}",
        follow_redirects=False,
    )
    if r.status_code in (301, 302):
        loc = (r.headers.get("location") or "").strip()
        if "FileNotFound" in loc or loc.endswith("/Error/FileNotFound"):
            raise RuntimeError("файл не найден на портале")
        if not loc.startswith("http"):
            loc = f"{ZPP_BASE}{loc}" if loc.startswith("/") else f"{ZPP_BASE}/{loc}"
        m = re.search(r"/Show/File/(\d+)", loc, re.I)
        if m:
            fid = int(m.group(1))
            raw, ctype = download_show_file(client, fid)
            body = extract_attachment_text(raw, ctype)
            return body, f"{ZPP_BASE}/Show/File/{fid}"
        raise RuntimeError(f"неподдерживаемый редирект: {loc}")
    r.raise_for_status()
    html = r.text
    m = re.search(
        r'(<div class="content-full"[\s\S]*?</div>)',
        html,
        re.I,
    )
    chunk = m.group(1) if m else html
    return strip_html(chunk), f"{ZPP_BASE}/npa/regional/{row_id}"


def download_show_file(client: httpx.Client, file_id: int) -> Tuple[bytes, str]:
    r = client.get(f"{ZPP_BASE}/Show/File/{file_id}", follow_redirects=True)
    r.raise_for_status()
    return r.content, r.headers.get("content-type", "")


def fetch_pravo_pdf_text(client: httpx.Client, eo_number: str) -> str:
    url = f"{PRAVO_PUB_HTTP}/file/pdf?eoNumber={eo_number}"
    r = client.get(url, follow_redirects=True)
    r.raise_for_status()
    return _extract_pdf_plain(r.content)


def run_federal(client: httpx.Client, out_dir: Path) -> Path:
    """Скачивает все федеральные НПА из грида ModuleId=13, пишет объединённый .txt."""
    page_size = 80
    first = fetch_grid_page(client, 13, 1, page_size)
    total = int(first.get("itemsCount") or 0)
    rows: List[dict] = list(first.get("data") or [])
    pages = max(1, (total + page_size - 1) // page_size)
    for p in range(2, pages + 1):
        chunk = fetch_grid_page(client, 13, p, page_size)
        rows.extend(chunk.get("data") or [])

    blocks: List[str] = []
    ok = 0
    for row in rows:
        rid = str(row.get("ID") or "").strip()
        title = (row.get("Title") or "").strip() or f"НПА id={rid}"
        if not rid:
            continue
        try:
            fid = resolve_federal_file_id(client, rid)
            if fid is None:
                raise RuntimeError("нет редиректа на /Show/File/")
            raw, ctype = download_show_file(client, fid)
            body = extract_attachment_text(raw, ctype)
            if len(body) < 80:
                raise RuntimeError("слишком мало текста после извлечения")
            src = Source(
                filename=f"zpp_npa_fed_{rid}",
                title=f"{title} (ГИС ЗПП, файл {fid})",
                url=f"{ZPP_BASE}/npa/federal/{rid}",
                category="Реестры и перечни НПА (полные тексты)",
            )
            blocks.append(split_to_articles(body, src, f"{ZPP_BASE}/Show/File/{fid}"))
            ok += 1
        except Exception as exc:
            logger.warning("Федеральный НПА id=%s пропущен: %s", rid, exc)

    merged = (
        f"Статья 0. Сводный пакет федеральных НПА ГИС ЗПП (полные тексты файлов). "
        f"Всего в гриде: {total}, извлечено: {ok}.\n\n"
        + "\n\n".join(blocks)
    )
    out_path = out_dir / "zpp_npa_federal_fulltext_bundle.txt"
    out_path.write_text(merged.strip() + "\n", encoding="utf-8")
    logger.info("Записан %s (%s символов, актов: %s)", out_path, len(merged), ok)
    return out_path


def run_regional(
    client: httpx.Client, out_dir: Path, regional_max: int
) -> Optional[Path]:
    if regional_max <= 0:
        logger.info("Региональные НПА пропущены (ZPP_REGIONAL_MAX<=0).")
        return None
    page_size = min(50, regional_max)
    rows: List[dict] = []
    p = 1
    while len(rows) < regional_max:
        chunk = fetch_grid_page(client, 27, p, page_size)
        part = chunk.get("data") or []
        if not part:
            break
        rows.extend(part)
        if len(part) < page_size:
            break
        p += 1
    rows = rows[:regional_max]

    blocks: List[str] = []
    ok = 0
    for row in rows:
        rid = str(row.get("ID") or "").strip()
        title = (row.get("Title") or "").strip() or f"НПА id={rid}"
        if not rid:
            continue
        try:
            body, src_url = extract_regional_act_text(client, rid)
            min_len = 25 if "/Show/File/" in src_url else 120
            if len(body) < min_len:
                raise RuntimeError("мало текста после извлечения")
            src = Source(
                filename=f"zpp_npa_reg_{rid}",
                title=f"{title} (ГИС ЗПП, региональная карточка)",
                url=f"{ZPP_BASE}/npa/regional/{rid}",
                category="Реестры и перечни НПА (полные тексты, регион)",
            )
            blocks.append(split_to_articles(body, src, src_url))
            ok += 1
        except Exception as exc:
            logger.warning("Региональный НПА id=%s пропущен: %s", rid, exc)

    merged = (
        f"Статья 0. Выборка региональных НПА ГИС ЗПП (HTML-карточки, max={regional_max}). "
        f"Извлечено: {ok}.\n\n" + "\n\n".join(blocks)
    )
    out_path = out_dir / "zpp_npa_regional_fulltext_sample.txt"
    out_path.write_text(merged.strip() + "\n", encoding="utf-8")
    logger.info("Записан %s (%s символов, актов: %s)", out_path, len(merged), ok)
    return out_path


def fetch_pravo_document_html(client: httpx.Client, eo_number: str) -> str:
    r = client.get(f"{PRAVO_PUB_HTTP}/document/{eo_number}", follow_redirects=True)
    r.raise_for_status()
    return strip_html(r.text)


def run_pravo_pdfs(client: httpx.Client, out_dir: Path) -> None:
    for suffix, eo, title in PRAVO_OFFICIAL_PDFS:
        path = out_dir / f"{suffix}.txt"
        try:
            text = fetch_pravo_pdf_text(client, eo)
            if len(text) < 80:
                text = fetch_pravo_document_html(client, eo)
            if len(text) < 80:
                raise ValueError("короткий текст из PDF и HTML")
            src = Source(
                filename=suffix,
                title=title,
                url=f"{PRAVO_PUB_HTTP}/document/{eo}",
                category="Официальное опубликование (pravo.gov.ru, PDF)",
            )
            path.write_text(
                split_to_articles(text, src, f"{PRAVO_PUB_HTTP}/file/pdf?eoNumber={eo}"),
                encoding="utf-8",
            )
            logger.info("Официальный PDF -> %s", path.name)
        except Exception as exc:
            logger.error("Не удалось загрузить pravo PDF %s: %s", eo, exc)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    codexes_ru_dir = repo_root / "data" / "codexes" / "ru"
    codexes_ru_dir.mkdir(parents=True, exist_ok=True)
    regional_max = int(os.environ.get("ZPP_REGIONAL_MAX", "0"))
    skip_federal = os.environ.get("ZPP_SKIP_FEDERAL", "").lower() in ("1", "true", "yes")

    timeout = httpx.Timeout(timeout=120.0, connect=40.0)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ZPPFulltextFetcher/1.0; +legal-bot)",
        "Accept": "*/*",
    }
    with httpx.Client(timeout=timeout, verify=True, headers=headers) as client:
        if not skip_federal:
            run_federal(client, codexes_ru_dir)
        else:
            logger.info("Пропуск федерального пакета (ZPP_SKIP_FEDERAL).")
        run_regional(client, codexes_ru_dir, regional_max=regional_max)
        run_pravo_pdfs(client, codexes_ru_dir)


if __name__ == "__main__":
    main()
