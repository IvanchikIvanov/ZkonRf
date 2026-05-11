"""Обработчики платежей."""
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters
from bot.utils.logger import log, log_user_action
from bot.services.payment_service import payment_service
from bot.services.crypto_service import crypto_service
from bot.services.language_service import language_service
from bot.services.conversation_context import conversation_context
from bot.utils.config import settings


def _expected_stars_for_months(months: int) -> int | None:
    if months == 1:
        return settings.subscription_price_stars_1month
    if months == 3:
        return settings.subscription_price_stars_3months
    if months == 12:
        return settings.subscription_price_stars_1year
    return None


async def handle_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /subscribe - выбор периода подписки."""
    user_id = update.effective_user.id
    user_language = await language_service.get_user_language(user_id)
    
    # Проверяем текущую подписку
    sub_info = await payment_service.check_subscription(user_id)
    
    if sub_info['has_subscription']:
        expires_at = sub_info.get('expires_at')
        if expires_at:
            expires_str = expires_at.strftime("%d.%m.%Y %H:%M")
        else:
            expires_str = "не указано"
        text = language_service.get_text('subscription_active', user_language).format(expires=expires_str)
        await update.message.reply_text(text)
        return
    
    # Показываем меню выбора периода подписки
    period_1month_text = language_service.get_text('period_1month', user_language)
    period_3months_text = language_service.get_text('period_3months', user_language)
    period_1year_text = language_service.get_text('period_1year', user_language)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{period_1month_text} - {settings.subscription_price_yookassa_1month} ₽",
                callback_data="period_1month"
            )
        ],
        [
            InlineKeyboardButton(
                f"{period_3months_text} - {settings.subscription_price_yookassa_3months} ₽",
                callback_data="period_3months"
            )
        ],
        [
            InlineKeyboardButton(
                f"{period_1year_text} - {settings.subscription_price_yookassa_1year} ₽",
                callback_data="period_1year"
            )
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = language_service.get_text('choose_period', user_language)
    
    await update.message.reply_text(text, reply_markup=reply_markup)


async def handle_pay_stars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str = "1month"):
    """Обработка оплаты через Telegram Stars."""
    query = update.callback_query
    # query.answer() вызывается в handle_callback_query
    
    user_id = update.effective_user.id
    user_language = await language_service.get_user_language(user_id)
    
    # Определяем период и цены
    period_info = {
        "1month": (language_service.get_text('period_1month', user_language), 1, settings.subscription_price_stars_1month, 30),
        "3months": (language_service.get_text('period_3months', user_language), 3, settings.subscription_price_stars_3months, 90),
        "1year": (language_service.get_text('period_1year', user_language), 12, settings.subscription_price_stars_1year, 365)
    }
    
    if period not in period_info:
        text = language_service.get_text('invalid_period', user_language)
        await query.message.reply_text(text)
        return
    
    period_name, months, stars_price, days = period_info[period]
    
    try:
        # Создаем инвойс для Telegram Stars
        # Для Telegram Stars цена указывается напрямую (1 звезда = 1 единица)
        title = language_service.get_text('choose_payment', user_language).format(period=period_name).split('\n')[0]
        prices = [LabeledPrice(title, stars_price)]
        
        description = f"Unlimited access for {days} days" if user_language == 'en' else f"Неограниченный доступ на {days} дней"
        
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=f"subscription_{user_id}_{months}",
            provider_token="",  # Для Stars не нужен
            currency="XTR",  # Telegram Stars
            prices=prices,
            start_parameter=f"subscription-{user_id}-{period}",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
    except Exception as e:
        log.error(f"Ошибка создания инвойса Stars: {e}")
        text = language_service.get_text('error_payment', user_language)
        await query.message.reply_text(text)


async def handle_pay_yookassa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str = "1month"):
    """Обработка оплаты через ЮKassa."""
    query = update.callback_query
    # query.answer() вызывается в handle_callback_query
    
    user_id = update.effective_user.id
    user_language = await language_service.get_user_language(user_id)
    
    # Определяем период и цены
    period_info = {
        "1month": (language_service.get_text('period_1month', user_language), 1, settings.subscription_price_yookassa_1month),
        "3months": (language_service.get_text('period_3months', user_language), 3, settings.subscription_price_yookassa_3months),
        "1year": (language_service.get_text('period_1year', user_language), 12, settings.subscription_price_yookassa_1year)
    }
    
    if period not in period_info:
        text = language_service.get_text('invalid_period', user_language)
        await query.message.reply_text(text)
        return
    
    period_name, months, yookassa_price = period_info[period]
    
    try:
        # Проверяем, настроена ли ЮKassa
        if not payment_service.yookassa_enabled:
            text = "❌ Bank card payment is temporarily unavailable.\n\nPlease use Telegram Stars to pay for subscription." if user_language == 'en' else "❌ Оплата банковской картой временно недоступна.\n\nПожалуйста, используйте Telegram Stars для оплаты подписки."
            await query.message.reply_text(text)
            return
        
        payment = await payment_service.create_yookassa_payment(
            user_id=user_id,
            amount=yookassa_price,
            description=f"Subscription for {period_name} - Legal codes bot" if user_language == 'en' else f"Подписка на {period_name} - Бот для работы с кодексами",
            months=months
        )
        
        if not payment:
            text = language_service.get_text('error_payment', user_language)
            await query.message.reply_text(text)
            return
        
        pay_button_text = "💳 Pay" if user_language == 'en' else "💳 Оплатить"
        payment_text = f"💳 Payment via ЮKassa\n\nPeriod: {period_name}\nAmount: {payment['amount']} ₽\n\nClick the button below to pay:" if user_language == 'en' else f"💳 Оплата через ЮKassa\n\nПериод: {period_name}\nСумма: {payment['amount']} ₽\n\nНажмите кнопку ниже для оплаты:"
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(pay_button_text, url=payment["confirmation_url"])
        ]])
        
        await query.message.reply_text(payment_text, reply_markup=keyboard)
    except Exception as e:
        log.error(f"Ошибка создания платежа ЮKassa: {e}")
        text = language_service.get_text('error_payment', user_language)
        await query.message.reply_text(text)


async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка предварительной проверки платежа (Telegram Stars)."""
    query = update.pre_checkout_query
    
    try:
        payer = query.from_user
        if not payer:
            await query.answer(ok=False, error_message="Ошибка обработки платежа")
            return
        
        # Проверяем payload
        payload = query.invoice_payload
        if not payload.startswith("subscription_"):
            await query.answer(ok=False, error_message="Неверный платеж")
            return
        
        # Формат: subscription_{user_id}_{months}
        parts = payload.split("_")
        if len(parts) < 3:
            await query.answer(ok=False, error_message="Неверный формат платежа")
            return
        
        user_id = int(parts[1])
        months = int(parts[2])
        
        if user_id != payer.id:
            log.warning(
                f"PreCheckout: user_id в payload ({user_id}) != payer.id ({payer.id})"
            )
            await query.answer(ok=False, error_message="Неверный платеж")
            return
        
        if (query.currency or "").upper() != "XTR":
            await query.answer(ok=False, error_message="Неверная валюта")
            return
        
        expected_stars = _expected_stars_for_months(months)
        if expected_stars is None or query.total_amount != expected_stars:
            log.warning(
                f"PreCheckout: сумма {query.total_amount} не совпадает с тарифом за {months} мес."
            )
            await query.answer(ok=False, error_message="Неверная сумма платежа")
            return
        
        # Подтверждаем платеж
        await query.answer(ok=True)
        
        log.info(
            f"Предварительная проверка платежа Stars для пользователя {user_id}, период: {months} месяцев"
        )
    except Exception as e:
        log.error(f"Ошибка предварительной проверки платежа: {e}")
        await query.answer(ok=False, error_message="Ошибка обработки платежа")


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешного платежа (Telegram Stars)."""
    payment = update.message.successful_payment
    payer = update.effective_user
    if not payer:
        log.error("successful_payment без effective_user")
        return
    
    try:
        payload = payment.invoice_payload
        # Формат: subscription_{user_id}_{months}
        parts = payload.split("_")
        if len(parts) < 3:
            raise ValueError("Неверный формат payload")
        
        payload_user_id = int(parts[1])
        months = int(parts[2])
        
        if payload_user_id != payer.id:
            log.error(
                f"successful_payment: payload user {payload_user_id} != payer {payer.id}"
            )
            await update.message.reply_text(
                "❌ Ошибка проверки платежа. Обратитесь в поддержку."
            )
            return
        
        if (payment.currency or "").upper() != "XTR":
            raise ValueError("Неверная валюта")
        expected_stars = _expected_stars_for_months(months)
        if expected_stars is None or payment.total_amount != expected_stars:
            raise ValueError("Неверная сумма или период")
        
        user_id = payer.id
        
        # Активируем подписку
        await payment_service.activate_subscription(user_id, months=months)
        
        # Правильный расчет дней
        days = 365 if months == 12 else months * 30
        period_names = {1: "1 месяц", 3: "3 месяца", 12: "1 год"}
        period_name = period_names.get(months, f"{months} месяцев")
        
        await update.message.reply_text(
            f"✅ Платеж успешно обработан!\n\n"
            f"🎉 Ваша подписка активирована на {period_name} ({days} дней).\n"
            f"Теперь вы можете задавать неограниченное количество вопросов!"
        )
        
        log.info(f"Подписка активирована через Stars для пользователя {user_id}, период: {months} месяцев")
        
        # Логируем действие пользователя
        username = payer.username or "без username"
        log_user_action(user_id, username, "subscription", f"Подписка активирована на {months} месяцев через Telegram Stars")
    except Exception as e:
        log.error(f"Ошибка обработки успешного платежа: {e}")
        await update.message.reply_text(
            "❌ Ошибка активации подписки. Обратитесь в поддержку."
        )


async def handle_pay_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
    """Обработка выбора оплаты криптовалютой."""
    user_id = update.effective_user.id
    query = update.callback_query
    
    user_language = await language_service.get_user_language(user_id)
    
    # Получаем информацию о пользователе
    sub_info = await payment_service.check_subscription(user_id)
    
    # Если у пользователя еще нет кошелька, создаем его
    if not sub_info.get('evm_wallet'):
        wallet_address = await crypto_service.create_user_wallet(user_id)
        if not wallet_address:
            text = language_service.get_text('error_wallet', user_language)
            await query.message.reply_text(text)
            return
    else:
        wallet_address = sub_info['evm_wallet']
    
    text = language_service.get_text('crypto_payment', user_language).format(address=wallet_address)
    
    await query.message.reply_text(text, parse_mode="Markdown")


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback запросов."""
    query = update.callback_query
    
    if query.data.startswith("pay_stars_"):
        await query.answer()
        period = query.data.replace("pay_stars_", "")
        await handle_pay_stars_callback(update, context, period)
    elif query.data.startswith("pay_yookassa_"):
        await query.answer()
        period = query.data.replace("pay_yookassa_", "")
        await handle_pay_yookassa_callback(update, context, period)
    elif query.data.startswith("pay_crypto_"):
        await query.answer()
        period = query.data.replace("pay_crypto_", "")
        await handle_pay_crypto_callback(update, context, period)
    elif query.data == "subscribe_menu":
        await query.answer()
        # Показываем меню выбора периода подписки
        user_id = update.effective_user.id
        user_language = await language_service.get_user_language(user_id)
        
        # Проверяем текущую подписку
        sub_info = await payment_service.check_subscription(user_id)
        
        if sub_info['has_subscription']:
            expires_at = sub_info.get('expires_at')
            if expires_at:
                expires_str = expires_at.strftime("%d.%m.%Y %H:%M")
            else:
                expires_str = "не указано"
            text = language_service.get_text('subscription_active', user_language).format(expires=expires_str)
            await query.message.reply_text(text)
            return
        
        # Показываем меню выбора периода подписки
        period_1month_text = language_service.get_text('period_1month', user_language)
        period_3months_text = language_service.get_text('period_3months', user_language)
        period_1year_text = language_service.get_text('period_1year', user_language)
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{period_1month_text} - {settings.subscription_price_yookassa_1month} ₽",
                    callback_data="period_1month"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{period_3months_text} - {settings.subscription_price_yookassa_3months} ₽",
                    callback_data="period_3months"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{period_1year_text} - {settings.subscription_price_yookassa_1year} ₽",
                    callback_data="period_1year"
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = language_service.get_text('choose_period', user_language)
        
        await query.message.reply_text(text, reply_markup=reply_markup)
    elif query.data.startswith("period_"):
        await query.answer()
        # Показываем меню выбора способа оплаты для выбранного периода
        period = query.data.replace("period_", "")
        user_id = update.effective_user.id
        user_language = await language_service.get_user_language(user_id)
        
        # Определяем период и цены
        period_names = {
            "1month": (language_service.get_text('period_1month', user_language), 1, settings.subscription_price_stars_1month, settings.subscription_price_yookassa_1month),
            "3months": (language_service.get_text('period_3months', user_language), 3, settings.subscription_price_stars_3months, settings.subscription_price_yookassa_3months),
            "1year": (language_service.get_text('period_1year', user_language), 12, settings.subscription_price_stars_1year, settings.subscription_price_yookassa_1year)
        }
        
        if period not in period_names:
            text = language_service.get_text('invalid_period', user_language)
            await query.message.reply_text(text)
            return
        
        period_name, months, stars_price, yookassa_price = period_names[period]
        
        keyboard = []
        
        # Telegram Stars - всегда показываем
        pay_stars_text = language_service.get_text('pay_stars', user_language).format(price=stars_price)
        keyboard.append([
            InlineKeyboardButton(
                pay_stars_text,
                callback_data=f"pay_stars_{period}"
            )
        ])
        
        # Банковская карта - всегда показываем
        pay_card_text = language_service.get_text('pay_card', user_language).format(price=yookassa_price)
        keyboard.append([
            InlineKeyboardButton(
                pay_card_text,
                callback_data=f"pay_yookassa_{period}"
            )
        ])
        
        # Криптовалюта (EVM)
        pay_crypto_text = language_service.get_text('pay_crypto', user_language)
        keyboard.append([
            InlineKeyboardButton(
                pay_crypto_text,
                callback_data=f"pay_crypto_{period}"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = language_service.get_text('choose_payment', user_language).format(period=period_name)
        
        await query.message.reply_text(text, reply_markup=reply_markup)
    elif query.data == "toggle_language":
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"
        
        # Получаем текущий язык
        current_language = await language_service.get_user_language(user_id)
        
        # Переключаем язык
        new_language = 'en' if current_language == 'ru' else 'ru'
        success = await language_service.set_user_language(user_id, new_language)
        
        if success:
            # Получаем текст на новом языке
            language_name = 'Русский' if new_language == 'ru' else 'English'
            switched_text = language_service.get_text('language_switched', new_language).format(language=language_name)
            welcome_text = language_service.get_text('welcome', new_language)
            
            # Обновляем сообщение с новым языком
            keyboard_buttons = []
            
            # Кнопка оплаты всегда видна
            subscribe_text = language_service.get_text('subscribe_button', new_language)
            keyboard_buttons.append([
                InlineKeyboardButton(subscribe_text, callback_data="subscribe_menu")
            ])
            
            language_text = language_service.get_text('language_button', new_language)
            keyboard_buttons.append([
                InlineKeyboardButton(language_text, callback_data="toggle_language")
            ])
            
            # Кнопка сброса контекста
            clear_context_text = language_service.get_text('clear_context_button', new_language)
            keyboard_buttons.append([
                InlineKeyboardButton(clear_context_text, callback_data="clear_context")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
            
            # Пытаемся отредактировать сообщение, игнорируем ошибку если содержимое не изменилось
            try:
                await query.message.edit_text(welcome_text, reply_markup=reply_markup)
            except Exception as e:
                # Если сообщение не изменилось, просто отвечаем
                log.debug(f"Сообщение не изменилось при переключении языка: {e}")
            
            await query.answer(switched_text, show_alert=False)
            
            # Логируем смену языка
            log_user_action(user_id, username, "language_change", f"Язык изменен на: {language_name} ({new_language})")
        else:
            await query.answer("❌ Ошибка изменения языка.", show_alert=True)
    elif query.data == "clear_context":
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"
        user_language = await language_service.get_user_language(user_id)
        
        # Очищаем контекст разговора
        await conversation_context.clear_context(user_id)
        
        # Получаем текст подтверждения
        cleared_text = language_service.get_text('context_cleared', user_language)
        await query.answer(cleared_text, show_alert=False)
        
        # Логируем сброс контекста
        log_user_action(user_id, username, "context_cleared", "Контекст разговора сброшен")
        log.info(f"Контекст разговора сброшен для пользователя @{username} (ID: {user_id})")

