#!/bin/bash
# Скрипт для настройки окружения на VPS

echo "Создание виртуального окружения..."
python3 -m venv venv

echo "Активация виртуального окружения..."
source venv/bin/activate

echo "Обновление pip..."
pip install --upgrade pip

echo "Установка зависимостей..."
pip install -r requirements.txt

echo "Создание директорий..."
mkdir -p data/codexes data/embeddings logs

echo "Настройка завершена!"
echo "Для активации окружения выполните: source venv/bin/activate"

