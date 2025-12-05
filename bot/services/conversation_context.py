"""Сервис для хранения контекста разговора пользователей."""
import time
from typing import List, Dict, Optional
from bot.services.cache_service import cache_service
from bot.utils.logger import log


class ConversationContextService:
    """Сервис для управления контекстом разговора."""
    
    MAX_CONTEXT_MESSAGES = 5  # Максимум сообщений в контексте
    CONTEXT_TTL = 1800  # 30 минут
    MAX_CONTENT_LENGTH = 2000  # Максимальная длина контента
    
    def _get_context_key(self, user_id: int) -> str:
        """Получить ключ для хранения контекста пользователя."""
        return f"conversation_context:{user_id}"
    
    async def add_message(self, user_id: int, role: str, content: str) -> bool:
        """
        Добавить сообщение в контекст пользователя.
        
        Args:
            user_id: ID пользователя
            role: Роль ('user', 'assistant' или 'system')
            content: Содержимое сообщения
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Валидация роли
            if role not in ("user", "assistant", "system"):
                log.warning(f"Невалидная роль: {role} для user {user_id}")
                return False
            
            # Валидация и ограничение контента
            if not isinstance(content, str):
                content = str(content)
            
            original_length = len(content)
            if len(content) > self.MAX_CONTENT_LENGTH:
                content = content[:self.MAX_CONTENT_LENGTH] + "…"
                log.debug(f"Контент обрезан для user {user_id} (было {original_length} символов, стало {len(content)})")
            
            # Получаем текущий контекст
            context = await self.get_context(user_id)
            
            # Добавляем новое сообщение с метаданными
            new_msg = {
                "role": role,
                "content": content,
                "ts": int(time.time())
            }
            context.append(new_msg)
            
            # Ограничиваем количество сообщений
            if len(context) > self.MAX_CONTEXT_MESSAGES:
                removed_count = len(context) - self.MAX_CONTEXT_MESSAGES
                context = context[-self.MAX_CONTEXT_MESSAGES:]
                log.debug(f"Контекст обрезан для user {user_id}: удалено {removed_count} старых сообщений")
            
            # Сохраняем в кэш (cache_service уже делает json.dumps)
            context_key = self._get_context_key(user_id)
            success = await cache_service.set(context_key, context, ttl=self.CONTEXT_TTL)
            
            if success:
                log.debug(f"Сообщение добавлено в контекст для user {user_id} (role: {role}, длина: {len(content)})")
            
            return success
            
        except Exception as e:
            log.error(f"Ошибка добавления сообщения в контекст для user {user_id}: {e}", exc_info=True)
            return False
    
    async def get_context(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получить контекст разговора пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список сообщений в формате [{"role": "user/assistant", "content": "...", "ts": ...}]
        """
        try:
            context_key = self._get_context_key(user_id)
            context = await cache_service.get(context_key)
            
            if context is None:
                return []
            
            # Проверяем что это список словарей
            if not isinstance(context, list):
                log.warning(f"Неожиданный формат контекста для user {user_id}: {type(context)}")
                return []
            
            # Продлеваем TTL при чтении (если контекст существует)
            if context:
                await cache_service.extend_ttl(context_key, self.CONTEXT_TTL)
            
            return context
            
        except Exception as e:
            log.error(f"Ошибка получения контекста для user {user_id}: {e}", exc_info=True)
            return []
    
    async def clear_context(self, user_id: int) -> bool:
        """
        Очистить контекст разговора пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        try:
            context_key = self._get_context_key(user_id)
            success = await cache_service.delete(context_key)
            
            if success:
                log.info(f"Контекст очищен для пользователя {user_id}")
            
            return success
            
        except Exception as e:
            log.error(f"Ошибка очистки контекста для user {user_id}: {e}", exc_info=True)
            return False
    
    async def extract_context_info(self, user_id: int) -> Dict[str, Optional[str]]:
        """
        Извлечь информацию о стране и кодексе из контекста разговора.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с ключами: 'country', 'codex', 'enhanced_question'
        """
        context = await self.get_context(user_id)
        
        if not context:
            return {"country": None, "codex": None, "enhanced_question": None}
        
        # Маппинг названий стран на коды
        country_mapping = {
            "таиланд": "thai", "тайланд": "thai", "thailand": "thai",
            "россия": "ru", "рф": "ru", "russia": "ru", "российск": "ru",
            "казахстан": "kz", "kazakhstan": "kz", "казахск": "kz",
            "армения": "am", "armenia": "am", "армянск": "am",
            "беларусь": "by", "belarus": "by", "белорусск": "by",
            "таджикистан": "tj", "tajikistan": "tj", "таджикск": "tj",
            "узбекистан": "uz", "uzbekistan": "uz", "узбекск": "uz",
            "азербайджан": "az", "azerbaijan": "az", "азербайджанск": "az"
        }
        
        # Ключевые слова для кодексов
        codex_keywords = {
            "гражданский": "гражданский",
            "трудовой": "трудовой",
            "уголовный": "уголовный",
            "налоговый": "налоговый",
            "коап": "коап", "административный": "коап",
            "семейный": "семейный"
        }
        
        found_country = None
        found_codex = None
        
        # Анализируем последние сообщения (более приоритетны)
        for msg in reversed(context):
            content_lower = msg.get("content", "").lower()
            
            # Ищем страну
            if not found_country:
                for country_name, country_code in country_mapping.items():
                    if country_name in content_lower:
                        found_country = country_code
                        log.debug(f"Найдена страна в контексте для user {user_id}: {country_code}")
                        break
            
            # Ищем кодекс
            if not found_codex:
                for keyword, codex_name in codex_keywords.items():
                    if keyword in content_lower:
                        found_codex = codex_name
                        log.debug(f"Найден кодекс в контексте для user {user_id}: {codex_name}")
                        break
            
            # Если нашли оба, можно прервать поиск
            if found_country and found_codex:
                break
        
        # Формируем расширенный вопрос
        enhanced_question = None
        if found_country:
            country_names = {
                "thai": "Thailand Таиланд",  # Добавляем английское название для поиска
                "ru": "Россия", "kz": "Казахстан",
                "am": "Армения", "by": "Беларусь", "tj": "Таджикистан",
                "uz": "Узбекистан", "az": "Азербайджан"
            }
            country_name = country_names.get(found_country, found_country)
            enhanced_question = country_name
        
        return {
            "country": found_country,
            "codex": found_codex,
            "enhanced_question": enhanced_question
        }
    
    async def format_context_for_prompt(self, user_id: int) -> str:
        """
        Форматировать контекст для передачи в промпт.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Отформатированная строка с контекстом
        """
        context = await self.get_context(user_id)
        
        if not context:
            return ""
        
        formatted = []
        system_messages = []
        
        for msg in context:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_messages.append(f"Система: {content}")
            elif role == "user":
                formatted.append(f"Пользователь: {content}")
            else:
                formatted.append(f"Ассистент: {content}")
        
        # System сообщения всегда первыми
        return "\n".join(system_messages + formatted)


# Глобальный экземпляр
conversation_context = ConversationContextService()

