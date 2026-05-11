"""Обработчик текстовых сообщений."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils.logger import log, log_user_action, log_missing_topic, log_suspicious_request
from bot.services.embeddings_service import embeddings_service
from bot.services.vector_db import vector_db
from bot.services.llm_service import llm_service
from bot.services.payment_service import payment_service
from bot.services.language_service import language_service
from bot.services.request_validator import validate_question
from bot.services.rate_limiter import rate_limiter
from bot.services.conversation_context import conversation_context


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового сообщения."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"
        message = update.message
        
        if not message or not message.text:
            return
        
        question = message.text.strip()
        
        if not question:
            return
        
        # Проверяем контекст разговора перед валидацией
        # Если есть контекст, короткие ответы могут быть уточнениями
        conversation_context_text = await conversation_context.format_context_for_prompt(user_id)
        has_context = bool(conversation_context_text)
        
        # Валидация запроса (для коротких ответов с контекстом - более мягкая проверка)
        is_valid, reason = validate_question(question, allow_short_with_context=has_context)
        
        # Сохраняем контекст для использования ниже
        _conversation_context_cache = conversation_context_text
        if not is_valid:
            log_suspicious_request(user_id, username, question, reason)
            log.warning(f"Заблокирован подозрительный запрос от @{username} (ID: {user_id}): {reason}")
            await message.reply_text("❌ Ваш запрос не может быть обработан. Пожалуйста, задайте юридический вопрос.")
            return
        
        # Rate limiting
        rate_ok, rate_message = rate_limiter.check_rate_limit(user_id)
        if not rate_ok:
            log.warning(f"Превышен rate limit для @{username} (ID: {user_id})")
            await message.reply_text(rate_message)
            return
        
        # Логируем запрос пользователя
        log.info(f"Текстовый запрос от @{username} (ID: {user_id}): {question}")
        
        # Логируем действие пользователя
        log_user_action(user_id, username, "text_query", f"Вопрос: {question}")
        
        # Проверка подписки и лимитов
        sub_info = await payment_service.check_subscription(user_id)
        
        # Проверяем пополнение кошелька (если есть кошелек)
        if sub_info.get('evm_wallet'):
            from bot.services.crypto_service import crypto_service
            await crypto_service.check_payment_received(user_id)
            # Обновляем информацию о подписке после проверки
            sub_info = await payment_service.check_subscription(user_id)
        
        # Получаем язык пользователя
        user_language = await language_service.get_user_language(user_id)
        
        if not sub_info['can_make_request']:
            if sub_info['has_subscription']:
                # Лимит подписки исчерпан
                remaining = sub_info['requests_limit'] - sub_info['requests_used']
                text = language_service.get_text('limit_exceeded_subscription', user_language).format(
                    used=sub_info['requests_used'],
                    limit=sub_info['requests_limit'],
                    remaining=remaining
                )
            else:
                # Бесплатный лимит исчерпан
                remaining = sub_info['free_requests_limit'] - sub_info['free_requests_used']
                text = language_service.get_text('limit_exceeded_free', user_language).format(
                    used=sub_info['free_requests_used'],
                    limit=sub_info['free_requests_limit'],
                    remaining=remaining
                )
            # Добавляем инлайн-кнопку для подписки
            subscribe_text = language_service.get_text('subscribe_button', user_language)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(subscribe_text, callback_data="subscribe_menu")
            ]])
            await message.reply_text(text, reply_markup=keyboard)
            return
        
        searching_text = language_service.get_text('searching', user_language)
        await message.reply_text(searching_text)
        
        # Извлекаем информацию из контекста для улучшения поиска
        context_info = await conversation_context.extract_context_info(user_id)
        extracted_country = context_info.get("country")
        extracted_codex = context_info.get("codex")
        enhanced_country_name = context_info.get("enhanced_question")
        
        # Расширяем вопрос информацией из контекста
        enhanced_question = question
        if enhanced_country_name:
            enhanced_question = f"{question} {enhanced_country_name}"
            log.info(f"Вопрос расширен контекстом для @{username} (ID: {user_id}): '{enhanced_question}' (страна из контекста: {enhanced_country_name})")
            
            # Если страна Таиланд (или другая с англ. кодексом), переводим запрос на английский
            # Это улучшит поиск по английскому тексту кодекса
            if extracted_country == 'thai':
                translated_query = await llm_service.translate_query(question, target_language="en")
                enhanced_question = f"{translated_query} {enhanced_country_name}"
                log.info(f"Запрос переведен для поиска (Thai): '{question}' -> '{enhanced_question}'")
        
        # Генерация embedding для расширенного вопроса
        question_embedding = await embeddings_service.generate_embedding(enhanced_question)
        
        # Поиск релевантных статей с фильтром по стране из контекста
        # Увеличено количество результатов для лучшего мультиязычного поиска
        relevant_articles = vector_db.search(
            question_embedding, 
            n_results=15,  # Увеличено с 5 до 15 для мультиязычного поиска
            country_filter=extracted_country  # Используем страну из контекста для фильтрации
        )
        
        if extracted_country:
            log.info(f"Поиск выполнен с фильтром по стране из контекста: {extracted_country} для @{username} (ID: {user_id})")
        
        log.info(f"Найдено {len(relevant_articles)} статей до фильтрации")
        
        # Фильтруем результаты по релевантности (distance < 0.85 для лучшего качества)
        # ChromaDB использует косинусное расстояние: чем меньше, тем релевантнее
        if relevant_articles:
            filtered_articles = []
            for article in relevant_articles:
                distance = article.get('distance', 1.0)
                # Оставляем только достаточно релевантные результаты
                if distance < 0.85:
                    filtered_articles.append(article)
            
            log.info(f"После фильтрации (distance < 0.85): {len(filtered_articles)} статей")
            
            # Если после фильтрации осталось меньше 3 статей, берем топ-5 по расстоянию
            if len(filtered_articles) < 3:
                relevant_articles = sorted(relevant_articles, key=lambda x: x.get('distance', 1.0))[:5]
                log.info(f"Используем топ-5 по расстоянию (фильтрация слишком строгая)")
            else:
                relevant_articles = filtered_articles[:10]  # Берем топ-10 релевантных
            
            log.info(f"Итоговое количество статей для ответа: {len(relevant_articles)}")
            
            # Ограничиваем количество статей для безопасности (максимум 5)
            MAX_ARTICLES_IN_RESPONSE = 5
            relevant_articles = relevant_articles[:MAX_ARTICLES_IN_RESPONSE]
        
        generating_text = language_service.get_text('generating', user_language)
        await message.reply_text(generating_text)
        
        # Используем контекст разговора (уже получили выше для валидации)
        conversation_context_text = _conversation_context_cache
        
        # Логируем контекст для отладки
        if conversation_context_text:
            log.info(f"Контекст разговора для @{username} (ID: {user_id}):\n{conversation_context_text[:500]}{'...' if len(conversation_context_text) > 500 else ''}")
        
        # Если нет статей, передаем пустой список - Grok сам скажет что информации нет
        if not relevant_articles:
            log_missing_topic(user_id, username, question, "не найдено релевантных статей в базе")
            # Передаем пустой список статей - Grok сам сформулирует ответ
            relevant_articles = []
        
        # Генерация ответа с помощью Grok с учетом контекста
        answer = await llm_service.generate_answer(question, relevant_articles, conversation_context=conversation_context_text)
        
        # Сохраняем сообщения в контекст
        await conversation_context.add_message(user_id, "user", question)
        await conversation_context.add_message(user_id, "assistant", answer)
        
        # Проверяем, упоминает ли ответ об отсутствии информации
        missing_phrases = [
            "не содержит", "не найдено", "недостаточно информации", 
            "нет информации", "отсутствует информация", "не содержит конкретных",
            "does not contain", "not found", "insufficient information",
            "no information", "missing information"
        ]
        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in missing_phrases):
            log_missing_topic(user_id, username, question, "LLM указал на отсутствие информации в ответе")
        
        # Отправка ответа (с fallback без Markdown, если модель вернула невалидную разметку)
        try:
            await message.reply_text(answer, parse_mode="Markdown")
        except Exception as send_error:
            log.warning(f"Не удалось отправить Markdown-ответ, отправляем plain text: {send_error}")
            await message.reply_text(answer)
        
        # Учитываем запрос только после успешной отправки ответа
        await payment_service.increment_request(user_id)
        
        # Логируем вопрос и ответ в консоль
        question_preview = question[:100] + "..." if len(question) > 100 else question
        answer_preview = answer[:500] + "..." if len(answer) > 500 else answer
        log.info(f"Обработка текстового сообщения завершена для @{username} (ID: {user_id})")
        log.info(f"Вопрос: {question_preview}")
        log.info(f"Ответ ({len(answer)} символов): {answer_preview}")
        
        # Логируем ответ в файл действий пользователя
        answer_preview_file = answer[:200] + "..." if len(answer) > 200 else answer
        log_user_action(user_id, username, "text_query", f"Ответ: {answer_preview_file}")
    
    except Exception as e:
        import traceback
        log.error(f"Ошибка обработки текстового сообщения: {e}")
        log.error(f"Traceback: {traceback.format_exc()}")
        
        # Безопасная отправка сообщения об ошибке
        try:
            if update.message:
                user_language = await language_service.get_user_language(user_id)
                error_text = language_service.get_text('error', user_language)
                await update.message.reply_text(error_text)
        except Exception as send_error:
            log.error(f"Не удалось отправить сообщение об ошибке: {send_error}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    user_id = update.effective_user.id
    
    # Очищаем контекст разговора при старте
    await conversation_context.clear_context(user_id)
    
    # Получаем язык пользователя
    user_language = await language_service.get_user_language(user_id)
    
    # Проверяем подписку для показа кнопки
    sub_info = await payment_service.check_subscription(user_id)
    
    # Получаем приветственный текст на нужном языке
    welcome_text = language_service.get_text('welcome', user_language)
    
    # Добавляем инлайн-кнопки
    keyboard_buttons = []
    
    # Кнопка оплаты всегда видна
    subscribe_text = language_service.get_text('subscribe_button', user_language)
    keyboard_buttons.append([
        InlineKeyboardButton(subscribe_text, callback_data="subscribe_menu")
    ])
    
    language_text = language_service.get_text('language_button', user_language)
    keyboard_buttons.append([
        InlineKeyboardButton(language_text, callback_data="toggle_language")
    ])
    
    # Кнопка сброса контекста
    clear_context_text = language_service.get_text('clear_context_button', user_language)
    keyboard_buttons.append([
        InlineKeyboardButton(clear_context_text, callback_data="clear_context")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help."""
    help_text = """
📚 Помощь по использованию бота:

1. Задайте вопрос текстом или голосовым сообщением
2. Бот найдет релевантные статьи в кодексах РФ
3. Получите развернутый ответ со ссылками на статьи
4. Для голосовых сообщений ответ также будет голосовым

Команды:
/start - Начать работу с ботом
/help - Показать эту справку
/stats - Статистика по базе данных
/subscribe - Оформить подписку
/country - Выбрать страну для поиска
/countries - Список доступных стран
"""
    await update.message.reply_text(help_text)


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /stats."""
    from bot.services.vector_db import vector_db
    
    try:
        count = vector_db.get_count()
        stats_text = f"""
📊 Статистика базы данных:

Статей в базе: {count}

База данных содержит индексированные статьи из кодексов РФ.
"""
        await update.message.reply_text(stats_text)
    except Exception as e:
        log.error(f"Ошибка получения статистики: {e}")
        await update.message.reply_text("❌ Ошибка получения статистики.")


