# План разработки Telegram бота с ИИ для кодексов РФ

## Цель
Telegram бот, который принимает голосовые вопросы о кодексах РФ и отвечает голосовым сообщением со ссылками на статьи.

## Технологический стек

### Основные компоненты:
1. **Telegram Bot API** - python-telegram-bot или aiogram
2. **Speech-to-Text (STT)** - OpenAI Whisper API
3. **Text-to-Speech (TTS)** - OpenAI TTS API
4. **LLM для ответов** - OpenAI ChatGPT (GPT-4/GPT-4o/GPT-3.5-turbo)
5. **Векторная БД** - ChromaDB, Qdrant или FAISS для поиска по кодексам
6. **Embeddings** - OpenAI text-embedding-3-small/3-large
7. **Docker** - контейнеризация для масштабирования
8. **Redis** - кэширование и очереди задач
9. **Docker Compose** - оркестрация сервисов

## Архитектура

### Логическая архитектура
```
┌─────────────┐
│  Telegram   │
│     Bot     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Voice Handler  │ (получение голосового сообщения)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  STT Service    │ (преобразование голоса в текст)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Query Parser   │ (обработка вопроса)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vector Search   │ (поиск релевантных статей)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Service    │ (генерация ответа с ссылками)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TTS Service    │ (преобразование текста в голос)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Response Send  │ (отправка голосового сообщения)
└─────────────────┘
```

### Docker архитектура (масштабируемая)
```
┌─────────────────────────────────────────────────┐
│              Docker Compose                      │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐            │
│  │  Bot Worker  │  │  Bot Worker  │  ... (N)   │
│  │  (Container) │  │  (Container) │            │
│  └──────┬───────┘  └──────┬───────┘            │
│         │                  │                     │
│         └────────┬─────────┘                     │
│                  │                               │
│         ┌────────▼────────┐                     │
│         │   Redis Cache    │                     │
│         │   (Container)    │                     │
│         └────────┬─────────┘                     │
│                  │                               │
│         ┌────────▼────────┐                     │
│         │  Vector DB      │                     │
│         │  (ChromaDB)      │                     │
│         │  (Volume)        │                     │
│         └──────────────────┘                     │
│                                                  │
│  ┌──────────────────────────────────────┐       │
│  │  Shared Volumes:                     │       │
│  │  - data/embeddings (Vector DB)       │       │
│  │  - data/codexes (Исходные файлы)    │       │
│  │  - logs/ (Логи)                      │       │
│  └──────────────────────────────────────┘       │
└─────────────────────────────────────────────────┘
```

## Структура проекта

```
zakonrff/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа бота
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── voice_handler.py # Обработка голосовых сообщений
│   │   └── text_handler.py  # Обработка текстовых сообщений (опционально)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stt_service.py   # Speech-to-Text
│   │   ├── tts_service.py   # Text-to-Speech
│   │   ├── llm_service.py    # LLM для генерации ответов
│   │   ├── vector_db.py     # Работа с векторной БД
│   │   └── cache_service.py # Redis кэширование
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # Конфигурация
│       └── logger.py        # Логирование
├── docker/
│   ├── Dockerfile           # Dockerfile для бота
│   └── docker-compose.yml   # Docker Compose конфигурация
├── data/
│   ├── codexes/             # Исходные файлы кодексов (volume)
│   └── embeddings/          # Векторные представления (volume)
├── logs/                    # Логи (volume)
├── scripts/
│   ├── load_codexes.py      # Скрипт загрузки кодексов
│   └── process_codexes.py   # Скрипт обработки и индексации
├── .dockerignore
├── .env.example
├── requirements.txt
├── config.yaml              # Конфигурационный файл
└── README.md
```

## Этапы разработки

### Этап 1: Базовая инфраструктура
- [ ] Настройка проекта (виртуальное окружение, зависимости)
- [ ] Создание структуры папок
- [ ] Настройка конфигурации (API ключи, токены)
- [ ] Базовый Telegram бот (прием сообщений)

### Этап 1.5: Docker инфраструктура
- [ ] Создание Dockerfile для бота
- [ ] Настройка Docker Compose (бот, Redis)
- [ ] Настройка volumes для данных (embeddings, codexes, logs)
- [ ] Health checks для контейнеров
- [ ] Настройка масштабирования (scale workers)
- [ ] Интеграция Redis для кэширования
- [ ] Окружение для разработки и продакшена

### Этап 2: Обработка голосовых сообщений
- [ ] Интеграция OpenAI Whisper API (STT)
- [ ] Обработка голосовых файлов из Telegram
- [ ] Конвертация форматов (OGG -> MP3/WAV для Whisper)
- [ ] Обработка ошибок STT

### Этап 3: Загрузка и индексация кодексов
- [ ] Парсинг кодексов (PDF/TXT/HTML)
- [ ] Разбивка на чанки (статьи)
- [ ] Генерация embeddings для статей
- [ ] Сохранение в векторную БД
- [ ] Метаданные (название кодекса, номер статьи, ссылка)

### Этап 4: Поиск и генерация ответов
- [ ] Векторный поиск релевантных статей
- [ ] Интеграция OpenAI ChatGPT API (GPT-4/GPT-3.5-turbo)
- [ ] Промпт-инжиниринг для генерации ответов
- [ ] Форматирование ответа со ссылками на статьи
- [ ] Обработка контекста (несколько релевантных статей)
- [ ] Использование OpenAI embeddings для векторного поиска

### Этап 5: Генерация голосовых ответов
- [ ] Интеграция OpenAI TTS API (tts-1 или tts-1-hd)
- [ ] Конвертация текста в голос (MP3)
- [ ] Отправка голосового сообщения в Telegram
- [ ] Обработка длинных ответов (разбивка на части, лимит 4096 символов для TTS)

### Этап 6: Оптимизация и улучшения
- [ ] Кэширование частых запросов (Redis)
- [ ] Обработка ошибок и edge cases
- [ ] Логирование и мониторинг
- [ ] Оптимизация промптов
- [ ] Тестирование на реальных вопросах
- [ ] Нагрузочное тестирование (scaling)
- [ ] Мониторинг ресурсов контейнеров

## Детали реализации

### Формат данных кодексов
```python
{
    "codex_name": "Гражданский кодекс РФ",
    "article_number": "123",
    "article_text": "Полный текст статьи...",
    "link": "https://www.consultant.ru/document/cons_doc_LAW_5142/...",
    "embedding": [0.1, 0.2, ...]
}
```

### Промпт для ChatGPT
```
Ты - профессиональный юридический ассистент, специализирующийся на кодексах Российской Федерации.

Пользователь задал вопрос: "{question}"

Ниже представлены релевантные статьи из кодексов РФ:

{relevant_articles}

Твоя задача:
1. Дать прямой и точный ответ на вопрос пользователя
2. Обязательно указать ссылки на конкретные статьи в формате: [Название кодекса, статья X](ссылка)
3. Если вопрос требует разъяснения, дай краткое и понятное объяснение
4. Если информации недостаточно, честно об этом скажи

Требования к ответу:
- Ответ должен быть на русском языке
- Используй естественную, понятную речь
- Избегай сложных юридических терминов без объяснений
- Структурируй ответ для лучшей читаемости
- Всегда указывай источники (ссылки на статьи)

Формат ссылок: [Гражданский кодекс РФ, статья 123](https://...)
```

### Обработка голосовых сообщений
1. Получение файла из Telegram
2. Скачивание файла (обычно OGG)
3. Конвертация в формат для STT (если нужно)
4. Отправка в STT API
5. Получение текста

### Обработка длинных ответов
- Если ответ > 4096 символов или > 60 секунд аудио:
  - Разбить на части
  - Отправить несколько голосовых сообщений
  - Или отправить текст + голосовое резюме

## API и сервисы (OpenAI)

### STT: OpenAI Whisper API
- **Модель**: `whisper-1`
- **Форматы**: MP3, MP4, MPEG, MPGA, M4A, WAV, WEBM
- **Лимиты**: 25 MB на файл
- **Стоимость**: $0.006 за минуту
- **Качество**: Отличное для русского языка

### TTS: OpenAI TTS API
- **Модели**: 
  - `tts-1` - быстрая, $15/1M символов
  - `tts-1-hd` - высокое качество, $30/1M символов
- **Голоса**: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
- **Форматы**: MP3, Opus, AAC, FLAC
- **Лимит**: 4096 символов на запрос

### LLM: OpenAI ChatGPT
- **Модели**:
  - `gpt-4o` - лучшая, быстрая, $2.50/$10 за 1M токенов
  - `gpt-4-turbo` - мощная, $10/$30 за 1M токенов
  - `gpt-3.5-turbo` - быстрая и дешевая, $0.50/$1.50 за 1M токенов
- **Рекомендация**: `gpt-4o` для баланса качества/цены

### Embeddings: OpenAI Embeddings
- **Модели**:
  - `text-embedding-3-small` - $0.02/1M токенов, 1536 размерность
  - `text-embedding-3-large` - $0.13/1M токенов, 3072 размерность
- **Рекомендация**: `text-embedding-3-small` для кодексов

## Конфигурация

### Переменные окружения (.env):
```
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy
MAX_TOKENS=2000
TEMPERATURE=0.7

# Database
DATABASE_PATH=/app/data/embeddings
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_CACHE_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_PATH=/app/logs

# Docker
WORKER_COUNT=2
```

## Приоритеты разработки

1. **MVP (Минимальный рабочий продукт)**:
   - Базовый Telegram бот
   - OpenAI Whisper API (STT: голос -> текст)
   - Загрузка и индексация кодексов с OpenAI embeddings
   - Векторный поиск релевантных статей
   - OpenAI ChatGPT (генерация ответов со ссылками)
   - OpenAI TTS (текст -> голос)
   - Отправка голосового ответа

2. **Улучшения**:
   - Кэширование частых запросов
   - Оптимизация промптов
   - Обработка длинных ответов (chunking)
   - Логирование и мониторинг
   - Обработка edge cases

## Оценка сложности

- Базовая инфраструктура: 2-3 часа
- OpenAI Whisper API интеграция: 1-2 часа
- Загрузка и индексация кодексов: 2-4 часа
- OpenAI Embeddings + векторный поиск: 2-3 часа
- OpenAI ChatGPT интеграция: 2-3 часа
- OpenAI TTS интеграция: 1-2 часа
- Тестирование и отладка: 3-5 часов

**Итого: ~15-20 часов разработки**

### Docker инфраструктура:
- Dockerfile и docker-compose: 1-2 часа
- Настройка volumes и networking: 1 час
- Redis интеграция: 1-2 часа
- Тестирование масштабирования: 1-2 часа

**Итого с Docker: ~19-26 часов разработки**

## Стоимость использования (примерная)

### Для 1000 запросов в месяц:
- Whisper (STT): ~$0.60 (100 минут аудио)
- ChatGPT (ответы): ~$5-15 (зависит от модели и длины ответов)
- Embeddings (индексация): ~$0.10 (одноразово при загрузке)
- TTS (голосовые ответы): ~$1-3 (зависит от длины ответов)

**Итого: ~$7-19 в месяц** (без учета первоначальной индексации кодексов)

## Docker конфигурация

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY bot/ ./bot/
COPY scripts/ ./scripts/

# Создание директорий для данных
RUN mkdir -p /app/data/embeddings /app/data/codexes /app/logs

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-m", "bot.main"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: zakonrff-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: zakonrff-bot
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./data/embeddings:/app/data/embeddings
      - ./data/codexes:/app/data/codexes
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
```

### Масштабирование
```bash
# Запуск с несколькими воркерами
docker-compose up --scale bot=3

# Или в docker-compose.yml:
deploy:
  replicas: 3
  resources:
    limits:
      cpus: '1'
      memory: 2G
```

### Redis для кэширования
- **Кэш запросов**: кэширование результатов поиска и ответов ChatGPT
- **Очереди задач**: для асинхронной обработки длинных запросов
- **Rate limiting**: ограничение запросов от одного пользователя
- **TTL**: автоматическое истечение кэша (1 час по умолчанию)

### Volumes для данных
- `data/embeddings` - векторная БД (ChromaDB/Qdrant)
- `data/codexes` - исходные файлы кодексов
- `logs/` - логи приложения
- `redis_data` - данные Redis (persistent)

### Мониторинг и логи
- Логи контейнеров: `docker-compose logs -f bot`
- Мониторинг ресурсов: `docker stats`
- Health checks для автоматического перезапуска
- Централизованное логирование в `/app/logs`


