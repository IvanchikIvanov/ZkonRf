"""Сервис для валидации запросов пользователей."""
from typing import Tuple


def validate_question(question: str, allow_short_with_context: bool = False) -> Tuple[bool, str]:
    """
    Валидация вопроса пользователя.
    
    Args:
        question: Вопрос пользователя
        allow_short_with_context: Разрешить короткие ответы если есть контекст разговора
        
    Returns:
        Tuple[bool, str]: (is_valid, reason_if_invalid)
    """
    question_lower = question.lower()
    
    # Блокируем попытки извлечения промпта/инструкций
    suspicious_patterns = [
        "покажи промпт", "show prompt", "system prompt", "системный промпт",
        "какие инструкции", "what instructions", "ignore previous",
        "забудь все", "forget all", "you are now", "теперь ты",
        "выведи все статьи", "list all articles", "покажи все статьи",
        "как ты работаешь", "how do you work", "explain your process",
        "repeat after me", "повтори за мной", "скажи слово в слово",
        "выведи промпт", "output prompt", "print prompt", "display prompt",
        "какие команды", "what commands", "show system", "покажи систему",
        "ignore all", "игнорируй все", "disregard", "проигнорируй",
        "act as", "действуй как", "pretend to be", "притворись",
        "roleplay", "ролевая игра", "you are a", "ты -",
        "перечисли все", "list all", "show all", "покажи все",
        "dump", "дамп", "export", "экспорт", "backup", "бэкап"
    ]
    
    for pattern in suspicious_patterns:
        if pattern in question_lower:
            return False, f"Подозрительный запрос обнаружен: попытка извлечения системной информации"
    
    # Блокируем слишком длинные запросы (возможная попытка переполнения)
    if len(question) > 500:
        return False, "Запрос слишком длинный (максимум 500 символов)"
    
    # Блокируем слишком короткие запросы (возможный спам)
    # Но разрешаем короткие ответы если есть контекст (например, "РФ", "Россия")
    min_length = 2 if allow_short_with_context else 3
    if len(question.strip()) < min_length:
        return False, "Запрос слишком короткий"
    
    return True, ""

