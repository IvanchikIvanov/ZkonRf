"""Обработчик голосовых сообщений."""
import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.logger import log, log_user_action, log_missing_topic, log_suspicious_request
from bot.services.stt_service import stt_service
from bot.services.embeddings_service import embeddings_service
from bot.services.vector_db import vector_db
from bot.services.llm_service import llm_service
from bot.services.tts_service import tts_service
from bot.services.cache_service import cache_service
from bot.services.payment_service import payment_service
from bot.services.crypto_service import crypto_service
from bot.services.language_service import language_service
from bot.services.request_validator import validate_question
from bot.services.rate_limiter import rate_limiter
from bot.services.conversation_context import conversation_context


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосового сообщения."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"
        message = update.message
        
        if not message or not message.voice:
            return
        
        log.info(f"Голосовое сообщение от @{username} (ID: {user_id})")
        
        # Проверка подписки и лимитов
        sub_info = await payment_service.check_subscription(user_id)
        
        # Проверяем пополнение кошелька (если есть кошелек)
        if sub_info.get('evm_wallet'):
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
                ) + f"\n/subscribe"
            else:
                # Бесплатный лимит исчерпан
                remaining = sub_info['free_requests_limit'] - sub_info['free_requests_used']
                text = language_service.get_text('limit_exceeded_free', user_language).format(
                    used=sub_info['free_requests_used'],
                    limit=sub_info['free_requests_limit'],
                    remaining=remaining
                ) + f"\n/subscribe"
            await message.reply_text(text)
            return
        
        # Увеличиваем счетчик запросов
        await payment_service.increment_request(user_id)
        
        await message.reply_text("🎤 Обрабатываю голосовое сообщение...")
        
        # Скачивание голосового файла
        voice_file = await context.bot.get_file(message.voice.file_id)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            await voice_file.download_to_drive(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            # STT: преобразование голоса в текст
            log.info(f"STT для @{username} (ID: {user_id})")
            question = await stt_service.transcribe(tmp_path)
            
            if not question:
                await message.reply_text("❌ Не удалось распознать речь. Попробуйте еще раз.")
                log.warning(f"STT не распознал речь для @{username} (ID: {user_id})")
                return
            
            # Логируем распознанный вопрос
            log.info(f"Распознано от @{username} (ID: {user_id}): {question}")
            await message.reply_text(f"📝 Распознано: {question}")
            
            # Валидация запроса
            is_valid, reason = validate_question(question)
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
            
            # Логируем действие пользователя
            log_user_action(user_id, username, "voice_query", f"Вопрос: {question}")
            
            await message.reply_text("🔍 Ищу релевантные статьи...")
            
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
            
            log.info(f"Найдено {len(relevant_articles)} статей до фильтрации (голосовой запрос)")
            
            # Фильтруем результаты по релевантности (distance < 0.85 для лучшего качества)
            if relevant_articles:
                filtered_articles = []
                for article in relevant_articles:
                    distance = article.get('distance', 1.0)
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
            
            await message.reply_text("🤖 Генерирую ответ...")
            
            # Получаем контекст разговора
            conversation_context_text = await conversation_context.format_context_for_prompt(user_id)
            
            # Если нет статей, передаем пустой список - ChatGPT сам скажет что информации нет
            if not relevant_articles:
                log_missing_topic(user_id, username, question, "не найдено релевантных статей в базе (голосовой запрос)")
                # Передаем пустой список статей - ChatGPT сам сформулирует ответ
                relevant_articles = []
            
            # Генерация ответа с помощью ChatGPT с учетом контекста
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
                log_missing_topic(user_id, username, question, "LLM указал на отсутствие информации в ответе (голосовой запрос)")
            
            # Отправка текстового ответа
            await message.reply_text(answer, parse_mode="Markdown")
            
            # Логируем вопрос и ответ в консоль
            question_preview = question[:100] + "..." if len(question) > 100 else question
            answer_preview = answer[:500] + "..." if len(answer) > 500 else answer
            log.info(f"Обработка голосового сообщения завершена для @{username} (ID: {user_id})")
            log.info(f"Вопрос: {question_preview}")
            log.info(f"Ответ ({len(answer)} символов): {answer_preview}")
            
            # Логируем ответ в файл действий пользователя
            answer_preview_file = answer[:200] + "..." if len(answer) > 200 else answer
            log_user_action(user_id, username, "voice_query", f"Ответ: {answer_preview_file}")
            
            # TTS: преобразование ответа в голос
            await message.reply_text("🔊 Создаю голосовое сообщение...")
            
            # Разбивка длинного ответа на части
            text_parts = tts_service.split_text(answer)
            
            for i, part in enumerate(text_parts):
                audio_bytes = await tts_service.synthesize(part)
                
                # Отправка голосового сообщения
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                    tmp_audio.write(audio_bytes)
                    tmp_audio_path = tmp_audio.name
                
                try:
                    with open(tmp_audio_path, "rb") as audio_file:
                        if len(text_parts) > 1:
                            caption = f"Часть {i + 1} из {len(text_parts)}"
                        else:
                            caption = None
                        
                        await message.reply_voice(
                            voice=audio_file,
                            caption=caption,
                            duration=int(len(audio_bytes) / 16000)  # Примерная длительность
                        )
                finally:
                    if os.path.exists(tmp_audio_path):
                        os.unlink(tmp_audio_path)
            
            log.info(f"Обработка голосового сообщения завершена для @{username} (ID: {user_id}). Вопрос: {question[:100]}{'...' if len(question) > 100 else ''}")
            
        finally:
            # Удаление временного файла
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        log.error(f"Ошибка обработки голосового сообщения: {e}")
        await message.reply_text("❌ Произошла ошибка при обработке сообщения. Попробуйте позже.")

