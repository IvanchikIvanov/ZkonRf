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
from bot.services.legal_scope_service import legal_scope_service
from bot.services.legal_ranking_service import legal_ranking_service


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
            
            # Для коротких уточнений ("да", "РФ", "про неё") учитываем наличие контекста.
            conversation_context_text = await conversation_context.format_context_for_prompt(user_id)
            has_context = bool(conversation_context_text)
            
            # Валидация запроса
            is_valid, reason = validate_question(question, allow_short_with_context=has_context)
            if not is_valid:
                log_suspicious_request(user_id, username, question, reason)
                log.warning(f"Заблокирован подозрительный запрос от @{username} (ID: {user_id}): {reason}")
                await message.reply_text("❌ Ваш запрос не может быть обработан. Пожалуйста, задайте юридический вопрос.")
                return
            
            # Rate limiting
            rate_ok, rate_message = await rate_limiter.check_rate_limit_async(user_id)
            if not rate_ok:
                log.warning(f"Превышен rate limit для @{username} (ID: {user_id})")
                await message.reply_text(rate_message)
                return
            
            # Логируем действие пользователя
            log_user_action(user_id, username, "voice_query", f"Вопрос: {question}")
            
            # Определяем intent/scope до поиска, чтобы не гонять RAG для обычного общения.
            context_info = await conversation_context.extract_context_info(user_id)
            last_scope = await conversation_context.get_last_legal_scope(user_id)
            scope = legal_scope_service.detect_scope(
                question,
                conversation_context=conversation_context_text,
                context_info=context_info,
                last_scope=last_scope,
            )
            log.info(f"Legal scope для voice @{username} (ID: {user_id}): {scope}")
            
            if scope.get("intent") == "unsafe_or_meta":
                answer = "Я не раскрываю внутренние инструкции или базу целиком. Задайте конкретный юридический вопрос — разберу по нормам и шагам."
                await conversation_context.add_message(user_id, "user", question)
                await conversation_context.add_message(user_id, "assistant", answer)
                await conversation_context.save_legal_scope(user_id, scope)
                await message.reply_text(answer)
                return
            
            if scope.get("intent") == "casual_chat":
                answer = legal_scope_service.build_casual_response(question)
                await conversation_context.add_message(user_id, "user", question)
                await conversation_context.add_message(user_id, "assistant", answer)
                await conversation_context.save_legal_scope(user_id, scope)
                await message.reply_text(answer)
                await payment_service.increment_request(user_id)
                return
            
            await message.reply_text("🔍 Ищу релевантные статьи...")
            
            # Расширяем вопрос информацией из контекста
            enhanced_question = legal_scope_service.build_enhanced_question(question, scope)
            if scope.get("country") == 'thai':
                translated_query = await llm_service.translate_query(question, target_language="en")
                enhanced_question = legal_scope_service.build_enhanced_question(translated_query, scope)
                log.info(f"Запрос переведен для поиска (Thai voice): '{question}' -> '{enhanced_question}'")
            
            # Генерация embedding для расширенного вопроса
            question_embedding = await embeddings_service.generate_embedding(enhanced_question)
            
            codex_filter = (
                scope.get("codex")
                if scope.get("codex_confidence") == "explicit"
                else None
            )
            
            # Поиск релевантных статей. Кодекс фильтруем жестко только при явном указании.
            relevant_articles = vector_db.search(
                question_embedding, 
                n_results=20,
                country_filter=scope.get("country"),
                codex_filter=codex_filter,
            )
            
            if codex_filter and not relevant_articles:
                log.warning(
                    f"Поиск по codex_key={codex_filter} ничего не дал, retry без codex_filter "
                    f"для voice @{username} (ID: {user_id})"
                )
                relevant_articles = vector_db.search(
                    question_embedding,
                    n_results=20,
                    country_filter=scope.get("country"),
                )
            
            if scope.get("country"):
                log.info(f"Поиск выполнен с фильтром по стране: {scope.get('country')} для voice @{username} (ID: {user_id})")
            
            log.info(f"Найдено {len(relevant_articles)} статей до фильтрации (голосовой запрос)")
            
            ranking_result = legal_ranking_service.rank(question, relevant_articles, scope)
            relevant_articles = ranking_result["articles"]
            log.info(f"Итоговое количество статей после reranking (voice): {len(relevant_articles)}")
            
            if ranking_result["needs_clarification"]:
                answer = ranking_result["clarification"]
                await conversation_context.add_message(user_id, "user", question)
                await conversation_context.add_message(user_id, "assistant", answer)
                await conversation_context.save_legal_scope(user_id, scope)
                await message.reply_text(answer)
                await payment_service.increment_request(user_id)
                return
            
            await message.reply_text("🤖 Генерирую ответ...")
            
            # Контекст уже вычислен выше до валидации
            
            # Если нет статей, передаем пустой список - Grok сам скажет что информации нет
            if not relevant_articles:
                log_missing_topic(user_id, username, question, "не найдено релевантных статей в базе (голосовой запрос)")
                # Передаем пустой список статей - Grok сам сформулирует ответ
                relevant_articles = []
            
            # Генерация ответа с помощью Grok с учетом контекста
            answer = await llm_service.generate_answer(
                question,
                relevant_articles,
                user_country=scope.get("country"),
                conversation_context=conversation_context_text,
            )
            
            # Сохраняем сообщения в контекст
            await conversation_context.add_message(user_id, "user", question)
            await conversation_context.add_message(user_id, "assistant", answer)
            await conversation_context.save_legal_scope(user_id, scope)
            
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
            
            # Отправка текстового ответа (fallback без Markdown)
            try:
                await message.reply_text(answer, parse_mode="Markdown")
            except Exception as send_error:
                log.warning(f"Не удалось отправить Markdown-ответ (voice), отправляем plain text: {send_error}")
                await message.reply_text(answer)
            
            # Учитываем запрос только после успешной отправки ответа
            await payment_service.increment_request(user_id)
            
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

