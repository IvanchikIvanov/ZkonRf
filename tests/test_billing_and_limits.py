import asyncio
from types import SimpleNamespace

from bot.services.payment_service import PaymentService
from bot.services.user_service import UserService


def test_yookassa_payment_uses_unique_idempotency_key(monkeypatch):
    service = PaymentService.__new__(PaymentService)
    service.yookassa_enabled = True

    seen_keys = []

    def fake_create(params, idempotency_key=None):
        seen_keys.append(idempotency_key)
        return SimpleNamespace(
            id="pay_123",
            status="pending",
            confirmation=SimpleNamespace(confirmation_url="https://pay.example/123"),
        )

    async def fake_cache_set(key, value, ttl=None):
        return True

    monkeypatch.setattr("bot.services.payment_service.Payment.create", fake_create)
    monkeypatch.setattr("bot.services.payment_service.cache_service.set", fake_cache_set)

    payment = asyncio.run(service.create_yookassa_payment(user_id=42, amount=100, months=1))

    assert payment["id"] == "pay_123"
    assert isinstance(seen_keys[0], str)
    assert seen_keys[0]
    assert seen_keys[0] not in {"True", "False"}


def test_subscription_default_is_unlimited(monkeypatch):
    service = PaymentService.__new__(PaymentService)
    captured = {}

    async def fake_activate_subscription(user_id, requests_limit, days):
        captured.update(user_id=user_id, requests_limit=requests_limit, days=days)
        return True

    monkeypatch.setattr("bot.services.payment_service.user_service.activate_subscription", fake_activate_subscription)

    assert asyncio.run(service.activate_subscription(42, months=1)) is True
    assert captured == {"user_id": 42, "requests_limit": 0, "days": 30}


def test_user_service_treats_zero_subscription_limit_as_unlimited(tmp_path):
    service = UserService()
    service.db_path = tmp_path / "users.db"

    async def scenario():
        await service.register_user(42, "tester")
        await service.activate_subscription(42, requests_limit=0, days=30)
        for _ in range(600):
            await service.increment_subscription_request(42)
        return await service.check_user_limits(42)

    limits = asyncio.run(scenario())

    assert limits["subscription_active"] is True
    assert limits["can_make_request"] is True
    assert limits["requests_limit"] == 0


def test_free_request_limit_uses_settings(monkeypatch, tmp_path):
    monkeypatch.setattr("bot.services.user_service.settings.free_requests_per_day", 3)
    service = UserService()
    service.db_path = tmp_path / "users.db"

    async def scenario():
        await service.register_user(42, "tester")
        for _ in range(3):
            await service.increment_free_request(42)
        return await service.check_user_limits(42)

    limits = asyncio.run(scenario())

    assert limits["can_make_request"] is False
    assert limits["free_requests_limit"] == 3

