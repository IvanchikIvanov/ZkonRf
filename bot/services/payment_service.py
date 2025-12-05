"""Сервис для работы с платежами и подписками."""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from yookassa import Configuration, Payment
from bot.utils.config import settings
from bot.utils.logger import log
from bot.services.cache_service import cache_service
from bot.services.user_service import user_service
from bot.services.crypto_service import crypto_service


class PaymentService:
    """Сервис для работы с платежами."""
    
    def __init__(self):
        """Инициализация сервиса платежей."""
        if settings.yookassa_shop_id and settings.yookassa_secret_key:
            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key
            self.yookassa_enabled = True
        else:
            self.yookassa_enabled = False
            log.warning("ЮKassa не настроена (отсутствуют ключи)")
        
        # Инициализация вайтлиста
        whitelist_str = getattr(settings, 'user_whitelist', '')
        if whitelist_str:
            try:
                self.whitelist = set(int(uid.strip()) for uid in whitelist_str.split(',') if uid.strip())
                log.info(f"Вайтлист загружен: {len(self.whitelist)} пользователей")
            except ValueError:
                log.warning("Ошибка парсинга вайтлиста, используется пустой список")
                self.whitelist = set()
        else:
            self.whitelist = set()
    
    def is_whitelisted(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь в вайтлисте."""
        return user_id in self.whitelist
    
    async def check_subscription(self, user_id: int) -> Dict[str, Any]:
        """
        Проверка подписки пользователя.
        
        Returns:
            dict: {
                'registered': bool,
                'has_subscription': bool,
                'expires_at': datetime или None,
                'free_requests_used': int,
                'free_requests_limit': int,
                'requests_used': int,
                'requests_limit': int,
                'can_make_request': bool,
                'evm_wallet': Optional[str],
                'is_whitelisted': bool
            }
        """
        # Проверяем вайтлист
        is_whitelisted = self.is_whitelisted(user_id)
        
        # Если пользователь в вайтлисте, даем неограниченный доступ
        if is_whitelisted:
            return {
                'registered': True,
                'has_subscription': True,
                'expires_at': None,
                'free_requests_used': 0,
                'free_requests_limit': float('inf'),
                'requests_used': 0,
                'requests_limit': float('inf'),
                'can_make_request': True,
                'evm_wallet': None,
                'is_whitelisted': True
            }
        
        # Проверяем лимиты через user_service
        limits = await user_service.check_user_limits(user_id)
        
        # Если пользователь не зарегистрирован, регистрируем его
        if not limits['registered']:
            await user_service.register_user(user_id)
            limits = await user_service.check_user_limits(user_id)
        
        return {
            'registered': limits['registered'],
            'has_subscription': limits['subscription_active'],
            'expires_at': limits['subscription_expires_at'],
            'free_requests_used': limits['free_requests_used'],
            'free_requests_limit': limits['free_requests_limit'],
            'requests_used': limits['requests_used'],
            'requests_limit': limits['requests_limit'],
            'can_make_request': limits['can_make_request'],
            'evm_wallet': limits['evm_wallet'],
            'is_whitelisted': False
        }
    
    async def _get_requests_count(self, user_id: int, date: str) -> int:
        """Получить количество запросов пользователя за день."""
        requests_key = f"requests:{user_id}:{date}"
        count_data = await cache_service.get(requests_key)
        return count_data if count_data else 0
    
    async def increment_request(self, user_id: int):
        """Увеличить счетчик запросов пользователя."""
        # Если пользователь в вайтлисте, не увеличиваем счетчик
        if self.is_whitelisted(user_id):
            return
        
        # Проверяем лимиты пользователя
        limits = await user_service.check_user_limits(user_id)
        
        if limits['subscription_active']:
            # Увеличиваем счетчик запросов подписки
            await user_service.increment_subscription_request(user_id)
        else:
            # Увеличиваем счетчик бесплатных запросов
            await user_service.increment_free_request(user_id)
    
    async def create_yookassa_payment(
        self,
        user_id: int,
        amount: Optional[int] = None,
        description: str = "Подписка на месяц",
        months: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Создать платеж через ЮKassa."""
        if not self.yookassa_enabled:
            return None
        
        try:
            amount = amount or settings.subscription_price_yookassa
            
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{settings.telegram_bot_token.split(':')[0]}"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "months": str(months)
                }
            }, settings.yookassa_test_mode)
            
            # Сохраняем информацию о платеже
            payment_key = f"payment:{payment.id}"
            await cache_service.set(
                payment_key,
                {
                    "user_id": user_id,
                    "amount": amount,
                    "status": payment.status,
                    "created_at": datetime.now().isoformat()
                },
                ttl=3600  # 1 час
            )
            
            return {
                "id": payment.id,
                "status": payment.status,
                "confirmation_url": payment.confirmation.confirmation_url,
                "amount": amount
            }
        except Exception as e:
            log.error(f"Ошибка создания платежа ЮKassa: {e}")
            return None
    
    async def activate_subscription(self, user_id: int, months: int = 1, requests_limit: int = 500):
        """Активировать подписку пользователя."""
        # Используем user_service для активации подписки
        # Для года используем 365 дней, для остальных - 30 дней на месяц
        if months == 12:
            days = 365
        else:
            days = 30 * months
        
        success = await user_service.activate_subscription(user_id, requests_limit=requests_limit, days=days)
        
        if success:
            log.info(f"Подписка активирована для пользователя {user_id} на {days} дней")
        
        return success
    
    async def handle_yookassa_webhook(self, event_data: Dict[str, Any]) -> bool:
        """Обработка вебхука от ЮKassa."""
        try:
            event_type = event_data.get("event")
            if event_type != "payment.succeeded":
                log.debug(f"Игнорируем событие {event_type}")
                return False
            
            payment_data = event_data.get("object", {})
            payment_id = payment_data.get("id")
            metadata = payment_data.get("metadata", {})
            user_id_str = metadata.get("user_id", "0")
            
            try:
                user_id = int(user_id_str)
            except (ValueError, TypeError):
                log.error(f"Неверный user_id в метаданных платежа {payment_id}: {user_id_str}")
                return False
            
            if not user_id:
                log.error(f"Не найден user_id в метаданных платежа {payment_id}")
                return False
            
            # Проверяем, что платеж еще не обработан
            payment_key = f"payment:{payment_id}"
            existing = await cache_service.get(payment_key)
            
            if existing and existing.get("processed"):
                log.warning(f"Платеж {payment_id} уже обработан")
                return True
            
            # Извлекаем период из метаданных
            months = int(metadata.get("months", "1"))
            
            # Активируем подписку
            await self.activate_subscription(user_id, months=months)
            
            # Помечаем платеж как обработанный
            if existing:
                existing["processed"] = True
                existing["processed_at"] = datetime.now().isoformat()
                await cache_service.set(payment_key, existing, ttl=86400 * 7)
            else:
                # Сохраняем информацию о платеже, если его еще нет
                await cache_service.set(
                    payment_key,
                    {
                        "user_id": user_id,
                        "processed": True,
                        "processed_at": datetime.now().isoformat(),
                        "payment_id": payment_id
                    },
                    ttl=86400 * 7
                )
            
            log.info(f"Подписка активирована через ЮKassa для пользователя {user_id}, платеж {payment_id}")
            return True
            
        except Exception as e:
            log.error(f"Ошибка обработки вебхука ЮKassa: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False


payment_service = PaymentService()

