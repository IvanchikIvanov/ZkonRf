FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libreoffice \
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

