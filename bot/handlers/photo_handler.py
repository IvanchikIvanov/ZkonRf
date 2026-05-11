"""Обработчик фотографий."""
import os
import tempfile
import base64
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.logger import log, log_user_action
from bot.services.payment_service import payment_service
from bot.services.language_service import language_service
from bot.services.llm_service import llm_service


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографии."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "без username"
        message = update.message
        
        if not message or not message.photo:
            return
        
        log.info(f"Фото от @{username} (ID: {user_id})")
        
        # Получаем подпись к фото, если есть
        caption = message.caption or ""
        
        # Логируем действие пользователя
        caption_info = f"Подпись: {caption}" if caption else "Без подписи"
        log_user_action(user_id, username, "photo_query", f"Отправлено фото. {caption_info}")
        
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
            subscribe_text = language_service.get_text('subscribe_button', user_language)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(subscribe_text, callback_data="subscribe_menu")
            ]])
            await message.reply_text(text, reply_markup=keyboard)
            return
        
        # Получаем самое большое фото (последний элемент в списке - самое высокое качество)
        photo = message.photo[-1]
        
        # Скачиваем фото
        photo_file = await context.bot.get_file(photo.file_id)
        
        analyzing_text = language_service.get_text('analyzing_image', user_language)
        await message.reply_text(analyzing_text)
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            await photo_file.download_to_drive(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            # Анализируем изображение
            analysis = await llm_service.analyze_image(tmp_path, caption, user_language)
            
            # Отправляем результат (fallback без Markdown)
            try:
                await message.reply_text(analysis, parse_mode="Markdown")
            except Exception as send_error:
                log.warning(f"Не удалось отправить Markdown-анализ фото, отправляем plain text: {send_error}")
                await message.reply_text(analysis)
            
            # Учитываем запрос только после успешной отправки ответа
            await payment_service.increment_request(user_id)
            
            log.info(f"Анализ фото завершен для @{username} (ID: {user_id})")
            
            # Логируем ответ
            analysis_preview = analysis[:200] + "..." if len(analysis) > 200 else analysis
            log_user_action(user_id, username, "photo_query", f"Анализ: {analysis_preview}")
        finally:
            # Удаляем временный файл
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
    except Exception as e:
        log.error(f"Ошибка обработки фото: {e}")
        import traceback
        log.error(traceback.format_exc())
        
        user_language = await language_service.get_user_language(user_id)
        error_text = language_service.get_text('error', user_language)
        await message.reply_text(error_text)

