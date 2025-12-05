"""Веб-сервер для обработки вебхуков ЮKassa."""
from aiohttp import web
from bot.utils.logger import log
from bot.services.payment_service import payment_service
from bot.utils.config import settings


async def handle_yookassa_webhook(request):
    """Обработка вебхука от ЮKassa."""
    try:
        data = await request.json()
        log.info(f"Получен вебхук от ЮKassa: {data.get('event')}")
        
        # Обработка вебхука
        result = await payment_service.handle_yookassa_webhook(data)
        
        if result:
            return web.json_response({"status": "ok"})
        else:
            return web.json_response({"status": "error"}, status=400)
            
    except Exception as e:
        log.error(f"Ошибка обработки вебхука ЮKassa: {e}")
        return web.json_response({"status": "error"}, status=500)


async def health_check(request):
    """Проверка здоровья сервера."""
    return web.json_response({"status": "ok"})


def create_app():
    """Создание приложения aiohttp."""
    app = web.Application()
    
    # Маршруты
    app.router.add_post("/webhook/yookassa", handle_yookassa_webhook)
    app.router.add_get("/health", health_check)
    
    return app


def run_webhook_server(host="0.0.0.0", port=8080):
    """Запуск веб-сервера для вебхуков."""
    app = create_app()
    log.info(f"Запуск веб-сервера для вебхуков на {host}:{port}")
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    run_webhook_server()

