"""Веб-сервер для обработки вебхуков ЮKassa."""
import base64
import binascii
import ipaddress
import secrets
from aiohttp import web
from bot.utils.logger import log
from bot.services.payment_service import payment_service
from bot.services.cache_service import cache_service
from bot.utils.config import settings


def _webhook_client_ip(request: web.Request) -> str:
    if settings.yookassa_webhook_trust_x_forwarded_for:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
    if request.remote:
        return request.remote
    return ""


def _parse_allowed_networks() -> list:
    raw = (settings.yookassa_webhook_allowed_ips or "").strip()
    if not raw:
        return []
    nets = []
    for part in raw.split(","):
        p = part.strip()
        if not p:
            continue
        try:
            if "/" in p:
                nets.append(ipaddress.ip_network(p, strict=False))
            else:
                nets.append(ipaddress.ip_network(f"{p}/32", strict=False))
        except ValueError:
            log.warning(f"Некорректная запись в YOOKASSA_WEBHOOK_ALLOWED_IPS: {p}")
    return nets


def _ip_allowed(client_ip: str, networks: list) -> bool:
    if not networks:
        return True
    try:
        ip = ipaddress.ip_address(client_ip.split("%")[0])
    except ValueError:
        return False
    return any(ip in net for net in networks)


def _check_basic_auth(request: web.Request) -> bool:
    user = (settings.yookassa_webhook_basic_user or "").strip()
    if not user:
        return True
    password = settings.yookassa_webhook_basic_password or ""
    hdr = request.headers.get("Authorization", "")
    if not hdr.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(hdr[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    u, _, p = decoded.partition(":")
    return secrets.compare_digest(u, user) and secrets.compare_digest(p, password)


async def handle_yookassa_webhook(request: web.Request):
    """Обработка вебхука от ЮKassa."""
    try:
        if payment_service.yookassa_enabled:
            if not cache_service.is_available:
                log.error("Вебхук ЮKassa: Redis недоступен")
                return web.json_response({"status": "service_unavailable"}, status=503)
            
            if not _check_basic_auth(request):
                log.warning("Вебхук ЮKassa: неверная Basic Auth")
                return web.json_response({"status": "unauthorized"}, status=401)
            
            nets = _parse_allowed_networks()
            cip = _webhook_client_ip(request)
            if nets and not _ip_allowed(cip, nets):
                log.warning(f"Вебхук ЮKassa: IP не в allowlist: {cip!r}")
                return web.json_response({"status": "forbidden"}, status=403)
        
        data = await request.json()
        log.info(f"Получен вебхук от ЮKassa: {data.get('event')}")
        
        result = await payment_service.handle_yookassa_webhook(data)
        
        if result:
            return web.json_response({"status": "ok"})
        return web.json_response({"status": "error"}, status=400)
            
    except Exception as e:
        log.error(f"Ошибка обработки вебхука ЮKassa: {e}")
        return web.json_response({"status": "error"}, status=500)


async def health_check(request: web.Request):
    """Проверка здоровья сервера."""
    return web.json_response({"status": "ok"})


def create_app():
    """Создание приложения aiohttp."""
    app = web.Application()
    
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
