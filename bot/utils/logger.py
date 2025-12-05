"""Настройка логирования."""
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger
from bot.utils.config import settings


def setup_logger():
    """Настройка логгера."""
    logger.remove()
    
    # Консольный вывод
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # Файловый вывод
    log_file = settings.log_path_resolved / "bot.log"
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger


def log_user_action(user_id: int, username: str, action_type: str, details: str = ""):
    """
    Логирование действий пользователей в отдельный файл.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя (может быть None)
        action_type: Тип действия (text_query, voice_query, photo_query, subscription, payment, language_change)
        details: Дополнительные детали действия
    """
    try:
        log_file = settings.log_path_resolved / "users_actions.txt"
        username_display = f"@{username}" if username else "без username"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] User ID: {user_id} | Username: {username_display} | Action: {action_type}\n")
            if details:
                # Форматируем детали с отступом
                details_lines = details.split('\n')
                for line in details_lines:
                    f.write(f"  {line}\n")
            f.write("-" * 80 + "\n")
    except Exception as e:
        logger.error(f"Ошибка записи лога действий пользователя: {e}")


def log_missing_topic(user_id: int, username: str, question: str, reason: str = ""):
    """
    Логирование отсутствующих тем в отдельный файл.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя (может быть None)
        question: Вопрос пользователя
        reason: Причина отсутствия информации (например, "не найдено релевантных статей" или "LLM указал на отсутствие информации")
    """
    try:
        log_file = settings.log_path_resolved / "missing_topics.txt"
        username_display = f"@{username}" if username else "без username"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] User ID: {user_id} | Username: {username_display}\n")
            f.write(f"Вопрос: {question}\n")
            if reason:
                f.write(f"Причина: {reason}\n")
            f.write("-" * 80 + "\n")
    except Exception as e:
        logger.error(f"Ошибка записи лога отсутствующих тем: {e}")


def log_suspicious_request(user_id: int, username: str, question: str, reason: str):
    """
    Логирование подозрительных запросов в отдельный файл.
    
    Args:
        user_id: ID пользователя
        username: Имя пользователя (может быть None)
        question: Вопрос пользователя
        reason: Причина блокировки запроса
    """
    try:
        log_file = settings.log_path_resolved / "suspicious_requests.txt"
        username_display = f"@{username}" if username else "без username"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] User ID: {user_id} | Username: {username_display}\n")
            f.write(f"Вопрос: {question}\n")
            f.write(f"Причина блокировки: {reason}\n")
            f.write("-" * 80 + "\n")
    except Exception as e:
        logger.error(f"Ошибка записи лога подозрительных запросов: {e}")


log = setup_logger()

