# Telegram бот для работы с кодексами РФ

Telegram бот с ИИ на базе ChatGPT, который отвечает на вопросы о кодексах РФ голосовыми сообщениями.

## Возможности

- 🎤 Прием голосовых вопросов
- 📝 Прием текстовых вопросов
- 🔍 Поиск релевантных статей в кодексах
- 🤖 Генерация ответов с помощью ChatGPT
- 🔊 Голосовые ответы с помощью OpenAI TTS
- 📚 Ссылки на конкретные статьи кодексов
- 🚀 Масштабируемая архитектура на Docker

## Технологии

- **Telegram Bot API**: python-telegram-bot
- **STT**: OpenAI Whisper API
- **TTS**: OpenAI TTS API
- **LLM**: OpenAI ChatGPT (GPT-4o)
- **Embeddings**: OpenAI text-embedding-3-large
- **Vector DB**: ChromaDB
- **Cache**: Redis
- **Containerization**: Docker + Docker Compose

## Установка

### 1. Клонирование и настройка

```bash
git clone <repository>
cd zakonrff
```

### 2. Настройка переменных окружения

Скопируйте `env.example` в `.env` и заполните:

```bash
cp env.example .env
```

Отредактируйте `.env`:
- `TELEGRAM_BOT_TOKEN` - токен бота от @BotFather
- `OPENAI_API_KEY` - API ключ OpenAI
- `GROK_API_KEY` - API ключ xAI/Grok для генерации ответов

### 2.1 Прод-конфигурация векторной БД (рекомендуется)

Для production рекомендуется использовать `PostgreSQL + pgvector`.

В `.env`:

```bash
VECTOR_BACKEND=pgvector
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
DATABASE_URL=postgresql://user:password@host:5432/dbname  # Railway/managed Postgres, если есть
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=zakonrff
POSTGRES_USER=zakonrff
POSTGRES_PASSWORD=zakonrff
PGVECTOR_TABLE=codex_embeddings
EMBEDDING_DIMENSIONS=3072
```

Запуск инфраструктуры:

```bash
docker-compose -f docker/docker-compose.yml up -d postgres redis
```

### 3. Загрузка кодексов

Поместите файлы кодексов в `data/codexes/`

**Поддерживаемые страны:**
- 🇷🇺 Россия (ru) - по умолчанию
- 🇰🇿 Казахстан (kz)
- 🇦🇲 Армения (am)
- 🇧🇾 Беларусь (by)
- 🇹🇯 Таджикистан (tj)
- 🇺🇿 Узбекистан (uz)
- 🇦🇿 Азербайджан (az)

**Структура папок:**
```
data/codexes/
├── ru/          # Россия
│   ├── koap.txt
│   └── uk.txt
├── kz/          # Казахстан
│   └── ...
└── ...
```

Или используйте префикс в имени файла: `ru_koap.txt`, `kz_koap.txt`

**Поддерживаемые форматы:**
- `.txt` - текстовые файлы
- `.md` - Markdown файлы
- `.odt` - OpenDocument Text (LibreOffice/OpenOffice)
- `.docx` - Microsoft Word документы

**Формат содержимого:**
Каждая статья должна начинаться с "Статья X.":
```
Статья 1. Текст статьи...

Статья 2. Текст статьи...
```

Подробнее см. `COUNTRIES_SETUP.md`

### 4. Индексация кодексов

```bash
# Локально
python -m scripts.process_codexes

# Или в Docker
docker-compose -f docker/docker-compose.yml run --rm bot python -m scripts.process_codexes
```

### 4.1 Миграция существующих embeddings из Chroma в pgvector

Если у вас уже есть данные в Chroma, перенесите их в PostgreSQL:

```bash
python -m scripts.migrate_chroma_to_pgvector
```

## Деплой

### Railway.app (самый простой способ)

📖 **Подробная инструкция:** [`RAILWAY_DEPLOY.md`](RAILWAY_DEPLOY.md)

1. Создайте проект на [railway.app](https://railway.app)
2. Подключите GitHub репозиторий
3. Railway автоматически определит Dockerfile и задеплоит бота
4. Добавьте переменные окружения и Redis сервис

---

## Запуск

### Docker Compose (для локального запуска)

```bash
# Запуск с одним воркером
docker-compose -f docker/docker-compose.yml up -d

# Запуск с несколькими воркерами
docker-compose -f docker/docker-compose.yml up -d --scale bot=3

# Просмотр логов
docker-compose -f docker/docker-compose.yml logs -f bot

# Остановка
docker-compose -f docker/docker-compose.yml down
```

### Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск Redis (если не используется Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Запуск бота
python -m bot.main
```

## Использование

1. Найдите бота в Telegram
2. Отправьте команду `/start`
3. Задайте вопрос текстом или голосовым сообщением
4. Получите ответ со ссылками на статьи

## Команды бота

- `/start` - Начать работу
- `/help` - Справка
- `/stats` - Статистика базы данных
- `/subscribe` - Оформить подписку
- `/countries` - Список доступных стран
- `/country <код>` - Выбрать страну для поиска (например: `/country kz`)

## Структура проекта

```
zakonrff/
├── bot/                    # Код бота
│   ├── handlers/           # Обработчики сообщений
│   ├── services/           # Сервисы (STT, TTS, LLM, etc.)
│   └── utils/              # Утилиты
├── docker/                 # Docker конфигурация
├── data/                   # Данные (volumes)
│   ├── codexes/           # Исходные файлы кодексов
│   └── embeddings/         # Векторная БД
├── scripts/                # Скрипты обработки
└── logs/                   # Логи
```

## Масштабирование

Для увеличения нагрузки запустите несколько воркеров:

```bash
docker-compose -f docker/docker-compose.yml up -d --scale bot=5
```

## Мониторинг

```bash
# Логи
docker-compose -f docker/docker-compose.yml logs -f

# Ресурсы
docker stats

# Статистика Redis
docker exec -it zakonrff-redis redis-cli INFO
```

## Стоимость

Примерная стоимость для 1000 запросов в месяц:
- Whisper (STT): ~$0.60
- ChatGPT: ~$5-15
- TTS: ~$1-3
- Embeddings: ~$0.10 (одноразово)

**Итого: ~$7-19/месяц**

## Лицензия

MIT

