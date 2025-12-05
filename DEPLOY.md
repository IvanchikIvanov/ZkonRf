# Инструкция по развертыванию на VPS

## Шаг 1: Настройка переменных окружения

```bash
# Копирование примера
cp env.example .env

# Редактирование .env
nano .env
```

Заполните обязательные поля:
- `TELEGRAM_BOT_TOKEN` - получите у @BotFather в Telegram
- `OPENAI_API_KEY` - получите на https://platform.openai.com/api-keys

## Шаг 2: Загрузка кодексов

```bash
# Поместите файлы кодексов в папку
# Поддерживаются: .txt, .md, .odt, .docx
mkdir -p data/codexes

# Скопируйте файлы кодексов в data/codexes/
# Например:
# cp /path/to/кодекс.odt data/codexes/
```

## Шаг 3: Индексация кодексов

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Запуск индексации
python -m scripts.process_codexes
```

Это займет время в зависимости от количества статей (генерация embeddings).

## Шаг 4: Запуск Redis (если не используете Docker)

```bash
# Установка Redis
sudo apt install -y redis-server

# Запуск Redis
sudo systemctl start redis
sudo systemctl enable redis

# Проверка
redis-cli ping
# Должен ответить: PONG
```

## Шаг 5: Запуск бота

### Вариант 1: Прямой запуск

```bash
source venv/bin/activate
python -m bot.main
```

### Вариант 2: В фоне с screen

```bash
# Установка screen
sudo apt install -y screen

# Создание сессии
screen -S bot

# Запуск бота
source venv/bin/activate
python -m bot.main

# Отсоединение: Ctrl+A, затем D
# Подключение: screen -r bot
```

### Вариант 3: С systemd (автозапуск)

```bash
# Создание сервиса
sudo nano /etc/systemd/system/zakonrff-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=ZakonRFF Telegram Bot
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/zakonrff
Environment="PATH=/root/zakonrff/venv/bin"
ExecStart=/root/zakonrff/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Запуск сервиса
sudo systemctl start zakonrff-bot

# Автозапуск при загрузке
sudo systemctl enable zakonrff-bot

# Проверка статуса
sudo systemctl status zakonrff-bot

# Просмотр логов
sudo journalctl -u zakonrff-bot -f
```

## Проверка работы

1. Найдите бота в Telegram
2. Отправьте `/start`
3. Отправьте текстовый вопрос или голосовое сообщение
4. Проверьте логи: `tail -f logs/bot.log`

## Полезные команды

```bash
# Просмотр логов
tail -f logs/bot.log

# Проверка статуса Redis
redis-cli ping

# Проверка количества статей в БД
python -c "from bot.services.vector_db import vector_db; vector_db.initialize(); print(f'Статей: {vector_db.get_count()}')"

# Перезапуск бота (если через systemd)
sudo systemctl restart zakonrff-bot
```

