import asyncio

from bot.handlers.payment_handler import handle_pay_crypto_callback
from bot.services.crypto_service import CryptoService


def test_crypto_wallet_creation_is_disabled_without_master_wallet(monkeypatch):
    service = CryptoService.__new__(CryptoService)
    service.master_wallet = ""

    def unexpected_wallet_creation():
        raise AssertionError("must not create an unrecoverable private wallet")

    async def unexpected_save(user_id, address):
        raise AssertionError("must not save a generated crypto address")

    monkeypatch.setattr(service, "create_wallet", unexpected_wallet_creation)
    monkeypatch.setattr("bot.services.crypto_service.user_service.set_evm_wallet", unexpected_save)

    assert asyncio.run(service.create_user_wallet(42)) is None


def test_crypto_master_wallet_balance_does_not_auto_activate(monkeypatch):
    service = CryptoService.__new__(CryptoService)
    service.master_wallet = "0x0000000000000000000000000000000000000001"
    service.token_checkers = {
        "bsc": type(
            "Checker",
            (),
            {
                "network_config": type("Network", (), {"name": "BSC"})(),
                "check_payment_received": lambda self, address: True,
                "check_usdt_balance": lambda self, address: 1_000_000_000_000_000_000,
                "format_balance": lambda self, balance: 1.0,
            },
        )()
    }

    async def fake_get_user(user_id):
        return {
            "evm_wallet": service.master_wallet,
            "subscription_active": False,
        }

    activated = {"called": False}

    async def fake_activation(*args, **kwargs):
        activated["called"] = True
        return True

    monkeypatch.setattr("bot.services.crypto_service.user_service.get_user", fake_get_user)
    monkeypatch.setattr("bot.services.crypto_service.user_service.activate_subscription", fake_activation)

    assert asyncio.run(service.check_payment_received(42)) is False
    assert activated["called"] is False


class FakeUser:
    id = 42


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeCallbackQuery:
    def __init__(self):
        self.message = FakeMessage()


class FakeUpdate:
    def __init__(self):
        self.effective_user = FakeUser()
        self.callback_query = FakeCallbackQuery()


def test_crypto_callback_is_unavailable(monkeypatch):
    async def fake_language(user_id):
        return "ru"

    monkeypatch.setattr("bot.handlers.payment_handler.language_service.get_user_language", fake_language)
    update = FakeUpdate()

    asyncio.run(handle_pay_crypto_callback(update, object(), "1month"))

    assert update.callback_query.message.replies == ["❌ Оплата криптовалютой временно недоступна."]
