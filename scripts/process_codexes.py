"""Скрипт для обработки и индексации кодексов."""
import asyncio
import json
import math
import re
from pathlib import Path
from typing import List, Dict
from bot.utils.config import settings
from bot.utils.logger import log
from bot.services.embeddings_service import embeddings_service
from bot.services.vector_db import vector_db
from bot.services.legal_scope_service import legal_scope_service


def extract_text_from_odt(file_path: Path) -> str:
    """Извлечение текста из ODT файла."""
    try:
        from odf import text, teletype
        from odf.opendocument import load
        import xml.etree.ElementTree as ET
        
        # Отключаем проверку внешних DTD для безопасности
        parser = ET.XMLParser()
        parser.entity["nbsp"] = " "
        
        # Загружаем документ с отключенной проверкой внешних ссылок
        doc = load(str(file_path), parser=parser)
        paragraphs = doc.getElementsByType(text.P)
        
        content = []
        for para in paragraphs:
            para_text = teletype.extractText(para)
            if para_text.strip():
                content.append(para_text)
        
        return "\n".join(content)
    except ImportError:
        log.error("Библиотека odfpy не установлена. Установите: pip install odfpy")
        raise
    except Exception as e:
        # Попробуем альтернативный метод через zip и XML
        try:
            log.warning(f"Первый метод не сработал, пробуем альтернативный: {e}")
            return extract_text_from_odt_alternative(file_path)
        except Exception as e2:
            log.error(f"Ошибка чтения ODT файла {file_path}: {e2}")
            raise


def extract_text_from_odt_alternative(file_path: Path) -> str:
    """Альтернативный метод извлечения текста из ODT через zip и XML."""
    import zipfile
    import xml.etree.ElementTree as ET
    
    content = []
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        # Читаем content.xml из ODT архива
        if 'content.xml' in zip_ref.namelist():
            xml_content = zip_ref.read('content.xml')
            # Отключаем проверку внешних сущностей
            parser = ET.XMLParser()
            # Добавляем пространство имен OpenDocument
            ET.register_namespace('office', 'urn:oasis:names:tc:opendocument:xmlns:office:1.0')
            ET.register_namespace('text', 'urn:oasis:names:tc:opendocument:xmlns:text:1.0')
            
            root = ET.fromstring(xml_content, parser=parser)
            
            # Находим все текстовые узлы в пространстве имен text
            namespaces = {
                'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
                'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
            }
            
            # Извлекаем текст из всех параграфов
            for para in root.findall('.//text:p', namespaces):
                para_text = ''.join(para.itertext()).strip()
                if para_text:
                    content.append(para_text)
            
            # Если не нашли через пространства имен, пробуем простой метод
            if not content:
                for elem in root.iter():
                    if elem.text:
                        text = elem.text.strip()
                        if text and len(text) > 2:  # Игнорируем очень короткие фрагменты
                            content.append(text)
    
    return "\n".join(content)


def extract_text_from_docx(file_path: Path) -> str:
    """Извлечение текста из DOCX файла."""
    try:
        from docx import Document
        
        doc = Document(str(file_path))
        content = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                content.append(para.text)
        
        return "\n".join(content)
    except ImportError:
        log.error("Библиотека python-docx не установлена. Установите: pip install python-docx")
        raise
    except Exception as e:
        log.error(f"Ошибка чтения DOCX файла {file_path}: {e}")
        raise


def extract_text_from_pdf(file_path: Path) -> str:
    """Извлечение текста из PDF файла."""
    try:
        from pypdf import PdfReader
        
        reader = PdfReader(str(file_path))
        content = []
        
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    content.append(page_text)
            except Exception as e:
                log.warning(f"Ошибка извлечения текста со страницы {page_num} в {file_path}: {e}")
                continue
        
        if not content:
            log.warning(f"Не удалось извлечь текст из PDF {file_path}")
            return ""
        
        return "\n\n".join(content)
    except ImportError:
        log.error("Библиотека pypdf не установлена. Установите: pip install pypdf")
        raise
    except Exception as e:
        log.error(f"Ошибка чтения PDF файла {file_path}: {e}")
        raise


def read_file_content(file_path: Path) -> str:
    """Чтение содержимого файла в зависимости от формата."""
    suffix = file_path.suffix.lower()
    
    if suffix == '.odt':
        return extract_text_from_odt(file_path)
    elif suffix == '.docx':
        return extract_text_from_docx(file_path)
    elif suffix == '.pdf':
        return extract_text_from_pdf(file_path)
    elif suffix in ['.txt', '.md']:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {suffix}")


def extract_country_from_path(file_path: Path, codexes_dir: Path) -> str:
    """Извлечение кода страны из пути файла."""
    # Маппинг кодов стран на названия
    country_mapping = {
        "ru": "Россия",
        "kz": "Казахстан",
        "am": "Армения",
        "by": "Беларусь",
        "kg": "Кыргызстан",
        "tj": "Таджикистан",
        "uz": "Узбекистан",
        "az": "Азербайджан",
        "thai": "Таиланд",
        "vn": "Вьетнам"
    }
    
    try:
        # Пытаемся извлечь код страны из структуры папок: codexes/{country}/file.txt
        relative_path = file_path.relative_to(codexes_dir)
        parts = relative_path.parts
        
        if len(parts) > 1:
            # Если файл в подпапке, первая часть - код страны
            country_code = parts[0].lower()
            if country_code in country_mapping:
                return country_code
        
        # Если структура папок не используется, пытаемся извлечь из имени файла
        # Формат: {country}_{codex_name}.txt
        filename = file_path.stem
        if '_' in filename:
            possible_country = filename.split('_')[0].lower()
            if possible_country in country_mapping:
                return possible_country
        
        # По умолчанию - Россия (для обратной совместимости)
        log.warning(f"Не удалось определить страну для {file_path}, используется 'ru' по умолчанию")
        return "ru"
    except Exception as e:
        log.warning(f"Ошибка извлечения страны из пути {file_path}: {e}, используется 'ru'")
        return "ru"


def parse_codex_file(file_path: Path, codexes_dir: Path) -> List[Dict[str, str]]:
    """Парсинг файла кодекса."""
    articles = []
    
    try:
        content = read_file_content(file_path)
        
        # Отладочная информация
        if not content or len(content.strip()) == 0:
            log.error(f"Текст из файла {file_path.name} пустой!")
            return []
        
        log.info(f"Извлечено {len(content)} символов из {file_path.name}")
        
        # Извлекаем страну из пути
        country_code = extract_country_from_path(file_path, codexes_dir)
        log.info(f"Определена страна для {file_path.name}: {country_code}")
        
        # Определяем формат статей в документе
        article_pattern = None
        if "Section" in content or "section" in content:
            # Английский формат: Section X.
            # В английских переводах Adilet могут встречаться русские маркеры
            # "Статья" в метаданных, поэтому Section имеет приоритет.
            article_pattern = r"Section\s+(\d+)[\.\s]+(.*?)(?=Section\s+\d+|$)"
            log.info("Обнаружен формат 'Section X.'")
        elif "Статья" in content or "статья" in content:
            # Русский формат: Статья X.
            article_pattern = r"Статья\s+(\d+)[\.\s]+(.*?)(?=Статья\s+\d+|$)"
            log.info("Обнаружен формат 'Статья X.'")
        else:
            log.warning(f"В тексте файла {file_path.name} не найдено ни 'Статья', ни 'Section'. Возможно, формат другой.")
            # Показываем первые строки для понимания формата
            first_lines = "\n".join(content.split("\n")[:20])
            log.info(f"Первые 20 строк текста из {file_path.name}:\n{first_lines}")
            return []
        
        # Парсинг статей по найденному паттерну
        matches = re.finditer(article_pattern, content, re.DOTALL | re.IGNORECASE)
        
        codex_name = file_path.stem
        # Убираем префикс страны из имени кодекса если он есть
        if codex_name.startswith(f"{country_code}_"):
            codex_name = codex_name[len(f"{country_code}_"):]
        codex_key = legal_scope_service.normalize_codex_key(codex_name)
        source_type = legal_scope_service.infer_source_type(codex_name)
        
        # Словарь для объединения частей одной статьи
        articles_dict = {}
        
        for match in matches:
            article_number = match.group(1)
            article_text = match.group(2).strip()
            
            if article_text:
                # Если статья с таким номером уже встречалась, объединяем текст
                if article_number in articles_dict:
                    # Показываем начало текста для понимания что объединяется
                    text_preview = article_text[:100].replace('\n', ' ') if len(article_text) > 100 else article_text.replace('\n', ' ')
                    existing_preview = articles_dict[article_number]["text"][:100].replace('\n', ' ') if len(articles_dict[article_number]["text"]) > 100 else articles_dict[article_number]["text"].replace('\n', ' ')
                    log.info(f"Объединение статьи {article_number}: существующая часть начинается с '{existing_preview}...', добавляется часть начинающаяся с '{text_preview}...'")
                    articles_dict[article_number]["text"] += "\n\n" + article_text
                else:
                    articles_dict[article_number] = {
                        "codex_name": codex_name,
                        "codex_key": codex_key,
                        "source_type": source_type,
                        "article_number": article_number,
                        "text": article_text,
                        "country": country_code,
                        "topic_tags": legal_scope_service.infer_topic_tags(codex_key, article_text),
                        "link": ""  # Ссылка будет формироваться динамически или оставляется пустой
                    }
        
        # Преобразуем словарь в список
        articles = list(articles_dict.values())
        
        log.info(f"Извлечено {len(articles)} статей из {file_path.name} (страна: {country_code})")
    except Exception as e:
        log.error(f"Ошибка парсинга {file_path}: {e}")
    
    return articles


async def process_codexes():
    """Обработка всех кодексов и индексация."""
    log.info("Начало обработки кодексов...")
    
    # Инициализация векторной БД
    vector_db.initialize()
    
    # Получаем список уже обработанных ID из БД
    existing_ids = vector_db.get_existing_ids()
    log.info(f"Найдено {len(existing_ids)} уже обработанных статей в БД")
    
    codexes_dir = Path(settings.database_path_resolved.parent / "codexes")
    codexes_dir.mkdir(parents=True, exist_ok=True)
    
    # Поддерживаемые коды стран
    supported_countries = ["ru", "kz", "am", "by", "kg", "tj", "uz", "az", "thai", "vn"]
    
    # Поиск всех файлов кодексов
    # Поддерживаем структуру: codexes/{country}/*.txt или codexes/*.txt
    codex_files = []
    
    # Сначала ищем файлы в подпапках стран
    for country_code in supported_countries:
        country_dir = codexes_dir / country_code
        if country_dir.exists():
            codex_files.extend(
                list(country_dir.glob("*.txt")) + 
                list(country_dir.glob("*.md")) + 
                list(country_dir.glob("*.odt")) + 
                list(country_dir.glob("*.docx")) +
                list(country_dir.glob("*.pdf"))
            )
    
    # Также ищем файлы в корневой папке (для обратной совместимости)
    codex_files.extend(
        list(codexes_dir.glob("*.txt")) + 
        list(codexes_dir.glob("*.md")) + 
        list(codexes_dir.glob("*.odt")) + 
        list(codexes_dir.glob("*.docx")) +
        list(codexes_dir.glob("*.pdf"))
    )
    
    if not codex_files:
        log.warning(f"Не найдено файлов кодексов в {codexes_dir}")
        return
    
    all_articles = []
    
    # Парсинг всех файлов
    for codex_file in codex_files:
        articles = parse_codex_file(codex_file, codexes_dir)
        all_articles.extend(articles)
    
    if not all_articles:
        log.warning("Не найдено статей для индексации")
        return
    
    log.info(f"Всего статей для обработки: {len(all_articles)}")
    
    # Генерация embeddings с разбивкой длинных статей на чанки
    max_tokens_per_chunk = 6000  # Запас от лимита 8192 токенов (уменьшено для безопасности)
    chars_per_token = 1.5  # Для русского текста примерно 1.5 символа = 1 токен (более точная оценка)
    max_chars_per_chunk = int(max_tokens_per_chunk * chars_per_token)  # ~9000 символов на чанк
    articles_with_embeddings = []
    skipped_count = 0
    
    for article in all_articles:
        # Формируем базовый ID статьи с учетом страны (без чанков)
        country_code = article.get('country', 'ru')
        base_id = f"{country_code}_{article['codex_name']}_article_{article['article_number']}"
        
        text = article["text"]
        text_length = len(text)
        
        # Подсчет примерного количества токенов (более точная оценка для русского текста)
        estimated_tokens = text_length / chars_per_token
        
        # Проверка, нужно ли разбивать статью на чанки
        if estimated_tokens > max_tokens_per_chunk:
            # Статья длинная - разбиваем на чанки
            num_chunks = math.ceil(estimated_tokens / max_tokens_per_chunk)
            log.info(f"Статья {article['article_number']}: {text_length} символов (~{int(estimated_tokens)} токенов) → разбиваем на {num_chunks} чанков")
            
            # Разбивка по предложениям для сохранения целостности
            sentences = text.split('. ')
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_with_dot = sentence if sentence.endswith('.') else sentence + '.'
                
                # Если предложение само по себе превышает лимит, режем его на равные части
                while len(sentence_with_dot) > max_chars_per_chunk:
                    part = sentence_with_dot[:max_chars_per_chunk]
                    sentence_with_dot = sentence_with_dot[max_chars_per_chunk:]
                    
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                    chunks.append(part.strip())
                
                # Проверяем, поместится ли предложение в текущий чанк
                if len(current_chunk) + len(sentence_with_dot) + 1 <= max_chars_per_chunk:
                    current_chunk += sentence_with_dot + " "
                else:
                    # Сохраняем текущий чанк и начинаем новый
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence_with_dot + " "
            
            # Добавляем последний чанк
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            log.info(f"Статья {article['article_number']} разбита на {len(chunks)} чанков")
            
            # Генерируем embeddings для каждого чанка и сохраняем как отдельные записи
            for chunk_num, chunk_text in enumerate(chunks):
                chunk_id = f"{country_code}_{article['codex_name']}_article_{article['article_number']}_chunk_{chunk_num + 1}"
                
                # Проверяем, не обработан ли уже этот чанк
                if chunk_id in existing_ids:
                    skipped_count += 1
                    log.debug(f"Чанк {chunk_num + 1}/{len(chunks)} статьи {article['article_number']} уже обработан, пропускаем")
                    continue
                
                # Дополнительная проверка размера чанка перед отправкой
                chunk_length = len(chunk_text)
                estimated_chunk_tokens = chunk_length / chars_per_token
                
                if estimated_chunk_tokens > max_tokens_per_chunk:
                    # Если чанк все еще слишком большой, обрезаем его
                    max_safe_length = int(max_tokens_per_chunk * chars_per_token * 0.9)  # 90% от лимита для безопасности
                    chunk_text = chunk_text[:max_safe_length]
                    log.warning(f"Чанк {chunk_num + 1} статьи {article['article_number']} обрезан до {max_safe_length} символов (было {chunk_length}, ~{int(estimated_chunk_tokens)} токенов)")
                
                log.info(f"Обработка чанка {chunk_num + 1}/{len(chunks)} статьи {article['article_number']} ({len(chunk_text)} символов, ~{int(len(chunk_text) / chars_per_token)} токенов)...")
                
                embeddings = await embeddings_service.generate_embeddings([chunk_text])
                
                # Сохраняем каждый чанк как отдельную запись с метаданными
                chunk_article = {
                    "id": chunk_id,
                    "codex_name": article["codex_name"],
                    "codex_key": article.get("codex_key", "unknown"),
                    "source_type": article.get("source_type", "code"),
                    "article_number": article["article_number"],
                    "country": country_code,
                    "text": chunk_text,
                    "embedding": embeddings[0],
                    "link": article.get("link", ""),
                    "topic_tags": article.get("topic_tags", ""),
                    "chunk_number": chunk_num + 1,
                    "total_chunks": len(chunks)
                }
                articles_with_embeddings.append(chunk_article)
                
        else:
            # Статья нормальной длины - обрабатываем целиком
            # Проверяем, не обработана ли уже эта статья
            if base_id in existing_ids:
                skipped_count += 1
                log.debug(f"Статья {article['article_number']} уже обработана, пропускаем")
                continue
            
            log.info(f"Статья {article['article_number']}: {text_length} символов (~{int(estimated_tokens)} токенов) → обрабатываем целиком")
            
            embeddings = await embeddings_service.generate_embeddings([text])
            
            article["embedding"] = embeddings[0]
            article["id"] = base_id
            articles_with_embeddings.append(article)
    
    if skipped_count > 0:
        log.info(f"Пропущено {skipped_count} уже обработанных статей/чанков")
    
    # Проверка на дубликаты ID перед добавлением
    seen_ids = set()
    unique_articles = []
    duplicates_count = 0
    
    for article in articles_with_embeddings:
        article_id = article["id"]
        if article_id in seen_ids:
            duplicates_count += 1
            log.warning(f"Пропущен дубликат ID: {article_id}")
        else:
            seen_ids.add(article_id)
            unique_articles.append(article)
    
    if duplicates_count > 0:
        log.warning(f"Найдено {duplicates_count} дубликатов, они будут пропущены")
    
    if not unique_articles:
        log.info("Нет новых статей для добавления. Все статьи уже обработаны.")
        return
    
    # Добавление в векторную БД
    log.info(f"Добавление {len(unique_articles)} уникальных статей в векторную БД...")
    vector_db.add_articles(unique_articles)
    
    log.info(f"Обработка завершена. Добавлено {len(unique_articles)} статей")


if __name__ == "__main__":
    asyncio.run(process_codexes())

