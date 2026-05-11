# Деплой на Railway.app

Railway - это простая платформа для деплоя приложений с автоматическим деплоем из GitHub.

## Вариант 1: Автоматический деплой через Railway UI (рекомендуется)

Это самый простой способ - Railway сам подключится к GitHub и будет автоматически деплоить при каждом push.

### Шаг 1: Создание проекта в Railway

1. Перейдите на [railway.app](https://railway.app)
2. Войдите через GitHub
3. Нажмите **"New Project"**
4. Выберите **"Deploy from GitHub repo"**
5. Выберите репозиторий `IvanchikIvanov/ZkonRf`

### Шаг 2: Настройка сервисов

Railway автоматически определит Dockerfile. Нужно настроить:

#### 2.1. Основной сервис (Bot)

1. Railway автоматически создаст сервис из Dockerfile
2. Перейдите в настройки сервиса → **Variables**
3. Добавьте все переменные из `env.example`:

**Обязательные:**
```
TELEGRAM_BOT_TOKEN=ваш_токен_бота
OPENAI_API_KEY=ваш_openai_ключ
GROK_API_KEY=ваш_grok_ключ
```

**Остальные переменные (скопируйте из env.example):**
```
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy
GROK_MODEL=grok-beta
MAX_TOKENS=2000
TEMPERATURE=0.7
FREE_REQUESTS_PER_DAY=3
DATABASE_PATH=/app/data/embeddings
REDIS_URL=${{Redis.REDIS_URL}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_PORT=6379
REDIS_DB=0
REDIS_CACHE_TTL=3600
LOG_LEVEL=INFO
LOG_PATH=/app/logs
WORKER_COUNT=2
```

**Важно:** для Railway проще использовать `REDIS_URL` и `DATABASE_URL`.

#### 2.2. Создание Redis сервиса

1. В проекте Railway нажмите **"+ New"** → **"Database"** → **"Add Redis"**
2. Railway автоматически создаст Redis
3. После создания Redis подключите переменную `REDIS_URL` к Bot сервису
4. Вернитесь в настройки Bot сервиса → **Variables**
5. Убедитесь, что `REDIS_URL` доступна Bot сервису

Код также поддерживает ручные `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, если вы не используете `REDIS_URL`.

#### 2.3. Создание PostgreSQL сервиса

1. В проекте Railway нажмите **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Для pgvector нужен образ/расширение с поддержкой `CREATE EXTENSION vector`
3. Подключите `DATABASE_URL` к Bot сервису
4. Установите:
```bash
VECTOR_BACKEND=pgvector
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=3072
```

#### 2.4. Настройка Volumes (для данных)

1. В настройках Bot сервиса → **Volumes**
2. Добавьте volume для всех runtime-данных:
   - **Mount Path:** `/app/data`
   - **Name:** `app-data`

3. Добавьте volume для логов:
   - **Mount Path:** `/app/logs`
   - **Name:** `logs-data`

### Шаг 3: Первоначальная индексация кодексов

После первого деплоя нужно проиндексировать кодексы:

1. Перейдите в Bot сервис → **Deployments** → откройте последний деплой
2. Нажмите **"View Logs"**
3. Откройте **"Shell"** (терминал)
4. Выполните:
```bash
python -m scripts.process_codexes
```

**Или через Railway CLI:**
```bash
railway run python -m scripts.process_codexes
```

### Шаг 4: Загрузка кодексов

1. Через Railway CLI:
```bash
railway login
railway link
railway run bash
# В терминале:
mkdir -p data/codexes
# Загрузите файлы кодексов через Railway UI → Volumes или через CLI
```

2. Или через Railway UI:
   - Перейдите в Bot сервис → **Volumes** → **codexes-data**
   - Загрузите файлы кодексов

### Шаг 5: Проверка работы

1. Railway автоматически создаст домен для вашего бота
2. Проверьте логи: Bot сервис → **Deployments** → **View Logs**
3. Найдите бота в Telegram и отправьте `/start`

---

## Вариант 2: Деплой через GitHub Actions

Если хотите использовать GitHub Actions для автоматического деплоя:

### Шаг 1: Получение Railway Token

1. Перейдите на [railway.app/account/tokens](https://railway.app/account/tokens)
2. Нажмите **"New Token"**
3. Скопируйте токен

### Шаг 2: Получение Service ID

1. В Railway проекте откройте Bot сервис
2. Перейдите в **Settings**
3. Скопируйте **Service ID** (внизу страницы)

### Шаг 3: Настройка GitHub Secrets

1. Перейдите в GitHub репозиторий → **Settings** → **Secrets and variables** → **Actions**
2. Добавьте секреты:
   - `RAILWAY_TOKEN` - токен из шага 1
   - `RAILWAY_SERVICE_ID` - Service ID из шага 2

### Шаг 4: Активация workflow

1. Переименуйте `.github/workflows/deploy-railway.yml` в `deploy.yml`
2. Или удалите другие workflow файлы
3. Сделайте commit и push в `main`
4. Workflow запустится автоматически

---

## Настройка переменных окружения

### Обязательные переменные:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
OPENAI_API_KEY=ваш_openai_ключ
GROK_API_KEY=ваш_grok_ключ
```

### Redis настройки:

После создания Redis сервиса в Railway подключите переменную:

```bash
REDIS_URL=${{Redis.REDIS_URL}}
```

Код также поддерживает ручные `REDIS_HOST` и `REDIS_PORT`, но для Railway предпочтителен `REDIS_URL`.

### Опциональные переменные:

Скопируйте остальные из `env.example` и настройте по необходимости.

---

## Структура проекта на Railway

```
Railway Project
├── Bot Service (Docker)
│   ├── Dockerfile: docker/Dockerfile
│   ├── Variables: все из env.example
│   └── Volumes:
│       ├── /app/data
│       └── /app/logs
├── Redis Service
│   └── REDIS_URL подключен к Bot Service
└── PostgreSQL Service
    └── DATABASE_URL подключен к Bot Service
```

---

## Полезные команды Railway CLI

```bash
# Установка CLI
curl -fsSL https://railway.app/install.sh | sh

# Вход
railway login

# Подключение к проекту
railway link

# Просмотр логов
railway logs

# Выполнение команды в контейнере
railway run python -m scripts.process_codexes

# Открытие shell
railway shell

# Просмотр переменных
railway variables
```

---

## Мониторинг и логи

- **Логи:** Railway UI → Bot сервис → **Deployments** → **View Logs**
- **Метрики:** Railway UI → Bot сервис → **Metrics**
- **Переменные:** Railway UI → Bot сервис → **Variables**

---

## Устранение проблем

### Бот не запускается

1. Проверьте логи: Railway UI → **Deployments** → **View Logs**
2. Убедитесь, что все переменные окружения установлены
3. Проверьте, что Redis сервис запущен и доступен

### Ошибка подключения к Redis

1. Убедитесь, что Redis сервис создан в том же проекте
2. Проверьте `REDIS_URL` или ручные `REDIS_HOST`/`REDIS_PORT`
3. Проверьте, что Redis сервис запущен

### Ошибка "No codexes found"

1. Убедитесь, что файлы кодексов загружены в volume `/app/data/codexes`
2. Выполните индексацию: `railway run python -m scripts.process_codexes`

### Ошибка "Database not found"

1. Убедитесь, что volume для embeddings создан
2. Выполните индексацию кодексов

---

## Стоимость

Railway предлагает:
- **Бесплатный тариф:** $5 кредитов в месяц
- **Pro план:** $20/месяц

Для бота обычно достаточно бесплатного тарифа, если трафик не очень большой.

---

## Автоматический деплой

После настройки через Railway UI, каждый push в `main` автоматически запустит новый деплой.

Проверьте настройки: Railway UI → Bot сервис → **Settings** → **Deploy** → должен быть включен **"Auto Deploy"**.




