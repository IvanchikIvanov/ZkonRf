"""Сервис для работы с языками интерфейса."""
from typing import Dict, Optional
from bot.services.user_service import user_service
from bot.utils.logger import log


# Тексты интерфейса на разных языках
TEXTS: Dict[str, Dict[str, str]] = {
    'ru': {
        'welcome': """Надоело искать свою статью в кодексах вчитываться в место где находится самая суть?

Просто задай свой вопрос как есть в бота через голосове сообщение или текстом и получи ответ за секунду!

Теперь не нужны юристы! Вся юридическая помощь здесь!

📚 Доступные кодексы:
• Гражданский кодекс РФ
• Трудовой кодекс РФ
• Налоговый кодекс РФ
• Кодекс об административных правонарушениях (КоАП РФ)
• Уголовный кодекс РФ
• И кодексы других стран (Казахстан, Армения, Беларусь, Таджикистан, Узбекистан, Азербайджан)

💡 Как пользоваться:
💬 Напишите вопрос текстом - задайте любой юридический вопрос простым языком
🎙️ Отправьте голосовое сообщение - бот распознает речь и ответит голосом
📷 Отправьте фото - проанализирую скриншоты законов, кодексов или документов

✨ Что вы получите:
✅ Развернутый ответ на ваш вопрос
✅ Ссылки на конкретные статьи кодексов
✅ Объяснение юридических терминов простым языком
✅ Информацию о стране и полном названии кодекса
✅ Голосовой ответ (при запросе голосом)

🚀 Начните прямо сейчас - просто задайте вопрос!""",
        'searching': '🔍 Ищу релевантные статьи...',
        'generating': '🤖 Генерирую ответ...',
        'not_found': '❌ Не найдено релевантных статей в кодексах.',
        'error': '❌ Произошла ошибка при обработке сообщения. Попробуйте позже.',
        'subscribe_button': '💎 Оформить подписку',
        'language_button': 'RU/EN',
        'language_switched': '✅ Язык изменен на: {language}',
        'clear_context_button': '🔄 Сбросить контекст',
        'context_cleared': '✅ Контекст разговора сброшен',
        'subscription_active': '✅ У вас уже есть активная подписка!\nДействует до: {expires}\n\nВы можете задавать вопросы без лимита по подписке.',
        'choose_period': '💎 Выберите период подписки\n\n🎯 Что дает подписка:\n• Неограниченное количество запросов\n• Приоритетная обработка\n• Доступ ко всем кодексам\n\nВыберите период:',
        'period_1month': '1 месяц',
        'period_3months': '3 месяца',
        'period_1year': '1 год',
        'choose_payment': '💎 Подписка на {period}\n\n💰 Выберите способ оплаты:',
        'pay_stars': '⭐ Telegram Stars ({price} ⭐)',
        'pay_card': '💳 Банковская карта ({price} ₽)',
        'pay_crypto': '₿ Криптовалюта (EVM)',
        'crypto_payment': '₿ Оплата криптовалютой (USDT)\n\n📝 Ваш адрес кошелька для пополнения:\n`{address}`\n\n⚠️ ВАЖНО:\n• Отправьте USDT на указанный адрес только в сети BSC или Ethereum\n• После пополнения подписка активируется автоматически\n• Проверка баланса происходит при каждом запросе\n\nПосле пополнения просто отправьте любое сообщение боту для активации подписки.',
        'limit_exceeded_subscription': '❌ Лимит запросов по подписке исчерпан.\n\nИспользовано: {used}/{limit}\nОсталось: {remaining}\n\n💎 Оформите новую подписку для продолжения работы!',
        'limit_exceeded_free': '❌ Лимит бесплатных запросов исчерпан.\n\nИспользовано: {used}/{limit}\nОсталось: {remaining}\n\n💎 Оформите подписку для продолжения работы!',
        'error_payment': '❌ Ошибка создания платежа. Попробуйте позже.',
        'error_wallet': '❌ Ошибка создания кошелька. Попробуйте позже.',
        'error_language': '❌ Ошибка изменения языка.',
        'invalid_period': '❌ Неверный период подписки.',
        'analyzing_image': '📷 Анализирую изображение...',
        'general_answer': 'Спасибо за ваш вопрос! Я обработал ваш запрос и подготовил ответ на основе доступной информации в кодексах.'
    },
    'en': {
        'welcome': """Tired of searching for your article in codes, reading into where the essence is?

Just ask your question as is to the bot via voice message or text and get an answer in a second!

Now lawyers are not needed! All legal help is here!

📚 Available codes:
• Civil Code of the Russian Federation
• Labor Code of the Russian Federation
• Tax Code of the Russian Federation
• Administrative Offenses Code (KoAP RF)
• Criminal Code of the Russian Federation
• And codes from other countries (Kazakhstan, Armenia, Belarus, Tajikistan, Uzbekistan, Azerbaijan)

💡 How to use:
💬 Write your question as text - ask any legal question in plain language
🎙️ Send a voice message - the bot will recognize speech and respond with voice
📷 Send a photo - I'll analyze screenshots of laws, codes, or documents

✨ What you'll get:
✅ Detailed answer to your question
✅ Links to specific code articles
✅ Explanation of legal terms in simple language
✅ Information about the country and full code name
✅ Voice response (when requested by voice)

🚀 Start right now - just ask your question!""",
        'searching': '🔍 Searching for relevant articles...',
        'generating': '🤖 Generating answer...',
        'not_found': '❌ No relevant articles found in the codes.',
        'error': '❌ An error occurred while processing the message. Please try again later.',
        'subscribe_button': '💎 Subscribe',
        'language_button': 'RU/EN',
        'language_switched': '✅ Language changed to: {language}',
        'clear_context_button': '🔄 Clear context',
        'context_cleared': '✅ Conversation context cleared',
        'subscription_active': '✅ You already have an active subscription!\nValid until: {expires}\n\nYou can ask questions without a subscription limit.',
        'choose_period': '💎 Choose subscription period\n\n🎯 What the subscription gives:\n• Unlimited number of requests\n• Priority processing\n• Access to all codes\n\nChoose period:',
        'period_1month': '1 month',
        'period_3months': '3 months',
        'period_1year': '1 year',
        'choose_payment': '💎 Subscription for {period}\n\n💰 Choose payment method:',
        'pay_stars': '⭐ Telegram Stars ({price} ⭐)',
        'pay_card': '💳 Bank card ({price} ₽)',
        'pay_crypto': '₿ Cryptocurrency (EVM)',
        'crypto_payment': '₿ Cryptocurrency payment (USDT)\n\n📝 Your wallet address for top-up:\n`{address}`\n\n⚠️ IMPORTANT:\n• Send USDT to the specified address only on BSC or Ethereum network\n• After top-up, the subscription activates automatically\n• Balance check occurs with each request\n\nAfter top-up, just send any message to the bot to activate the subscription.',
        'limit_exceeded_subscription': '❌ Subscription request limit exceeded.\n\nUsed: {used}/{limit}\nRemaining: {remaining}\n\n💎 Subscribe again to continue!',
        'limit_exceeded_free': '❌ Free request limit exceeded.\n\nUsed: {used}/{limit}\nRemaining: {remaining}\n\n💎 Subscribe to continue!',
        'error_payment': '❌ Error creating payment. Please try again later.',
        'error_wallet': '❌ Error creating wallet. Please try again later.',
        'error_language': '❌ Error changing language.',
        'invalid_period': '❌ Invalid subscription period.',
        'analyzing_image': '📷 Analyzing image...',
        'general_answer': 'Thank you for your question! I have processed your request and prepared an answer based on the available information in the codes.'
    }
}


class LanguageService:
    """Сервис для работы с языками."""
    
    @staticmethod
    async def get_user_language(user_id: int) -> str:
        """Получить язык пользователя (по умолчанию 'ru')."""
        user = await user_service.get_user(user_id)
        if user and user.get('language'):
            return user['language']
        return 'ru'
    
    @staticmethod
    async def set_user_language(user_id: int, language: str) -> bool:
        """Установить язык пользователя."""
        if language not in ['ru', 'en']:
            return False
        
        await user_service.ensure_db_initialized()
        
        try:
            import aiosqlite
            from datetime import datetime
            from bot.utils.config import settings
            from pathlib import Path
            
            db_dir = Path(settings.database_path_resolved).parent
            db_path = db_dir / "users.db"
            
            async with aiosqlite.connect(db_path) as db:
                # Проверяем, существует ли пользователь
                cursor = await db.execute(
                    "SELECT user_id FROM users WHERE user_id = ?",
                    (user_id,)
                )
                existing = await cursor.fetchone()
                
                if existing:
                    # Обновляем язык
                    await db.execute(
                        "UPDATE users SET language = ?, updated_at = ? WHERE user_id = ?",
                        (language, datetime.now().isoformat(), user_id)
                    )
                else:
                    # Создаем пользователя с языком
                    await db.execute(
                        "INSERT INTO users (user_id, language, created_at, updated_at) VALUES (?, ?, ?, ?)",
                        (user_id, language, datetime.now().isoformat(), datetime.now().isoformat())
                    )
                
                await db.commit()
                log.info(f"Язык установлен для пользователя {user_id}: {language}")
                return True
        except Exception as e:
            log.error(f"Ошибка установки языка для пользователя {user_id}: {e}")
            return False
    
    @staticmethod
    def get_text(key: str, language: str = 'ru') -> str:
        """Получить текст по ключу на указанном языке."""
        return TEXTS.get(language, TEXTS['ru']).get(key, key)
    
    @staticmethod
    async def get_text_for_user(key: str, user_id: int) -> str:
        """Получить текст по ключу для пользователя."""
        language = await LanguageService.get_user_language(user_id)
        return LanguageService.get_text(key, language)


language_service = LanguageService()

