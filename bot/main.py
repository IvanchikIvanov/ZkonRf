"""Главный файл для запуска бота."""
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters
)
from bot.utils.config import settings
from bot.utils.logger import log
from bot.handlers.voice_handler import handle_voice_message
from bot.handlers.photo_handler import handle_photo_message
from bot.handlers.text_handler import (
    handle_text_message,
    handle_start,
    handle_help,
    handle_stats,
    handle_templates,
    handle_cancel_doc
)
from bot.handlers.payment_handler import (
    handle_subscribe,
    handle_callback_query,
    handle_pre_checkout,
    handle_successful_payment
)
from bot.services.cache_service import cache_service
from bot.services.vector_db import vector_db
from bot.services.payment_service import payment_service

yookassa_poll_task: asyncio.Task | None = None


async def _yookassa_poll_loop():
    """Пока бот запущен — периодически проверяем незавершённые платежи ЮKassa через API."""
    interval = settings.yookassa_poll_interval_seconds
    if interval <= 0:
        return
    interval = max(15, int(interval))
    log.info(f"Опрос ЮKassa: каждые {interval} с (ключи payment:* в Redis → Payment.find_one)")
    while True:
        try:
            await payment_service.poll_pending_yookassa_from_redis()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Ошибка опроса ЮKassa")
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break


async def post_init(app: Application):
    """Инициализация после запуска бота."""
    log.info("Инициализация сервисов...")
    global yookassa_poll_task
    
    # Удаление меню бота
    try:
        from telegram import MenuButtonDefault
        await app.bot.delete_my_commands()
        await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        log.info("Меню бота удалено")
    except Exception as e:
        log.warning(f"Не удалось удалить меню: {e}")
    
    await cache_service.connect()
    vector_db.initialize()
    
    if payment_service.yookassa_enabled:
        log.info("ЮKassa настроена и готова к работе")
        if settings.yookassa_poll_interval_seconds > 0:
            yookassa_poll_task = asyncio.create_task(_yookassa_poll_loop())
        else:
            log.warning(
                "ЮKassa: YOOKASSA_POLL_INTERVAL_SECONDS=0 — оплаты картой не активируют подписку автоматически "
                "(нужен интервал опроса или ручная активация)"
            )
    else:
        log.info("ЮKassa не настроена (работает только Telegram Stars)")
    
    log.info("Все сервисы инициализированы")
    log.info(f"Бот запущен. Статей в базе: {vector_db.get_count()}")


async def post_shutdown(app: Application):
    """Очистка при остановке бота."""
    global yookassa_poll_task
    
    log.info("Остановка сервисов...")
    
    if yookassa_poll_task:
        yookassa_poll_task.cancel()
        try:
            await yookassa_poll_task
        except asyncio.CancelledError:
            pass
        yookassa_poll_task = None
    
    await cache_service.disconnect()
    log.info("Бот остановлен")


def main():
    """Главная функция запуска бота."""
    log.info("Запуск бота...")
    
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("stats", handle_stats))
    application.add_handler(CommandHandler("subscribe", handle_subscribe))
    application.add_handler(CommandHandler("templates", handle_templates))
    application.add_handler(CommandHandler("cancel_doc", handle_cancel_doc))
    
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    application.post_init = post_init
    application.post_shutdown = post_shutdown
    
    log.info("Бот готов к работе")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
