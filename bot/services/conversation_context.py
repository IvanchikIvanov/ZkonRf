"""Сервис для хранения контекста разговора пользователей."""
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
import aiosqlite
from bot.utils.config import settings
from bot.utils.logger import log


class ConversationContextService:
    """Сервис для управления контекстом разговора."""
    
    def __init__(self):
        db_dir = Path(settings.database_path_resolved).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "users.db"
        self.max_content_length = settings.context_max_content_length
        self.prompt_messages = settings.context_prompt_messages
        self.scan_messages = settings.context_scan_messages
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
    
    async def _init_db(self):
        """Инициализация таблицы истории диалогов."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ts INTEGER NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON conversation_messages(user_id, id)"
            )
            await db.commit()
        log.info(f"История диалогов инициализирована: {self.db_path}")
    
    async def ensure_db_initialized(self):
        """Убедиться, что таблица истории готова к использованию."""
        if self._db_initialized:
            return
        
        async with self._init_lock:
            if self._db_initialized:
                return
            await self._init_db()
            self._db_initialized = True
    
    async def add_message(self, user_id: int, role: str, content: str) -> bool:
        """
        Добавить сообщение в историю пользователя.
        
        Args:
            user_id: ID пользователя
            role: Роль ('user', 'assistant' или 'system')
            content: Содержимое сообщения
        """
        await self.ensure_db_initialized()
        
        try:
            if role not in ("user", "assistant", "system"):
                log.warning(f"Невалидная роль: {role} для user {user_id}")
                return False
            
            if not isinstance(content, str):
                content = str(content)
            
            original_length = len(content)
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "…"
                log.debug(
                    f"Контент обрезан для user {user_id} "
                    f"(было {original_length}, стало {len(content)})"
                )
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO conversation_messages (user_id, role, content, ts)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, role, content, int(time.time()))
                )
                await db.commit()
            
            return True
        except Exception as e:
            log.error(f"Ошибка добавления сообщения в контекст для user {user_id}: {e}", exc_info=True)
            return False
    
    async def get_context(self, user_id: int, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Получить контекст разговора пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Сколько последних сообщений вернуть. Если None - берется context_prompt_messages.
        """
        await self.ensure_db_initialized()
        
        try:
            limit = self.prompt_messages if limit is None else limit
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                if limit and limit > 0:
                    cursor = await db.execute(
                        """
                        SELECT role, content, ts
                        FROM conversation_messages
                        WHERE user_id = ?
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                        (user_id, limit)
                    )
                else:
                    cursor = await db.execute(
                        """
                        SELECT role, content, ts
                        FROM conversation_messages
                        WHERE user_id = ?
                        ORDER BY id DESC
                        """,
                        (user_id,)
                    )
                rows = await cursor.fetchall()
            
            if not rows:
                return []
            
            # Возвращаем в хронологическом порядке
            context = [
                {"role": row["role"], "content": row["content"], "ts": row["ts"]}
                for row in reversed(rows)
            ]
            return context
        except Exception as e:
            log.error(f"Ошибка получения контекста для user {user_id}: {e}", exc_info=True)
            return []
    
    async def clear_context(self, user_id: int) -> bool:
        """Очистить историю контекста пользователя."""
        await self.ensure_db_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM conversation_messages WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
            log.info(f"Контекст очищен для пользователя {user_id}")
            return True
        except Exception as e:
            log.error(f"Ошибка очистки контекста для user {user_id}: {e}", exc_info=True)
            return False
    
    async def save_legal_scope(self, user_id: int, scope: Dict[str, Any]) -> bool:
        """Сохранить последний юридический scope как system-сообщение."""
        payload = {
            "country": scope.get("country"),
            "codex": scope.get("codex"),
            "topic": scope.get("topic"),
            "intent": scope.get("intent"),
            "country_confidence": scope.get("country_confidence"),
            "codex_confidence": scope.get("codex_confidence"),
        }
        return await self.add_message(
            user_id,
            "system",
            "LEGAL_SCOPE_JSON:" + json.dumps(payload, ensure_ascii=False)
        )
    
    async def get_last_legal_scope(self, user_id: int) -> Dict[str, Any]:
        """Получить последний сохраненный юридический scope."""
        context = await self.get_context(user_id, limit=self.scan_messages)
        for msg in reversed(context):
            content = msg.get("content", "")
            if msg.get("role") == "system" and content.startswith("LEGAL_SCOPE_JSON:"):
                try:
                    return json.loads(content.split("LEGAL_SCOPE_JSON:", 1)[1])
                except Exception as e:
                    log.warning(f"Не удалось прочитать LEGAL_SCOPE для user {user_id}: {e}")
                    return {}
        return {}
    
    async def extract_context_info(self, user_id: int) -> Dict[str, Optional[str]]:
        """Извлечь информацию о стране и кодексе из истории диалога."""
        context = await self.get_context(user_id, limit=self.scan_messages)
        
        if not context:
            return {"country": None, "codex": None, "enhanced_question": None}
        
        country_mapping = {
            "таиланд": "thai", "тайланд": "thai", "thailand": "thai",
            "вьетнам": "vn", "вьетнамск": "vn", "vietnam": "vn", "viet nam": "vn",
            "россия": "ru", "рф": "ru", "russia": "ru", "российск": "ru",
            "казахстан": "kz", "kazakhstan": "kz", "казахск": "kz",
            "армения": "am", "armenia": "am", "армянск": "am",
            "беларусь": "by", "belarus": "by", "белорусск": "by",
            "таджикистан": "tj", "tajikistan": "tj", "таджикск": "tj",
            "узбекистан": "uz", "uzbekistan": "uz", "узбекск": "uz",
            "азербайджан": "az", "azerbaijan": "az", "азербайджанск": "az"
        }
        
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
        
        # Приоритет - сообщения пользователя, чтобы не подтягивать шум из ответов ассистента.
        user_messages = [msg for msg in context if msg.get("role") == "user"]
        messages_to_scan = user_messages if user_messages else context
        
        for msg in reversed(messages_to_scan):
            content_lower = msg.get("content", "").lower()
            
            if not found_country:
                for country_name, country_code in country_mapping.items():
                    if country_name in content_lower:
                        found_country = country_code
                        break
            
            if not found_codex:
                for keyword, codex_name in codex_keywords.items():
                    if keyword in content_lower:
                        found_codex = codex_name
                        break
            
            if found_country and found_codex:
                break
        
        enhanced_parts = []
        if found_country:
            country_names = {
                "thai": "Thailand Таиланд",
                "vn": "Vietnam Вьетнам",
                "ru": "Россия", "kz": "Казахстан",
                "am": "Армения", "by": "Беларусь", "tj": "Таджикистан",
                "uz": "Узбекистан", "az": "Азербайджан"
            }
            enhanced_parts.append(country_names.get(found_country, found_country))
        if found_codex:
            enhanced_parts.append(f"{found_codex} кодекс")
        
        return {
            "country": found_country,
            "codex": found_codex,
            "enhanced_question": " ".join(enhanced_parts) if enhanced_parts else None
        }
    
    async def format_context_for_prompt(self, user_id: int) -> str:
        """Форматировать последние сообщения для передачи в промпт."""
        context = await self.get_context(user_id, limit=self.prompt_messages)
        
        if not context:
            return ""
        
        formatted = []
        system_messages = []
        
        for msg in context:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                if content.startswith("LEGAL_SCOPE_JSON:"):
                    continue
                system_messages.append(f"Система: {content}")
            elif role == "user":
                formatted.append(f"Пользователь: {content}")
            else:
                formatted.append(f"Ассистент: {content}")
        
        return "\n".join(system_messages + formatted)


# Глобальный экземпляр
conversation_context = ConversationContextService()
