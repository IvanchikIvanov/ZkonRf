"""Сервис для работы с пользователями в БД."""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from bot.utils.config import settings
from bot.utils.logger import log


class UserService:
    """Сервис для работы с пользователями."""
    
    def __init__(self):
        """Инициализация сервиса."""
        db_dir = Path(settings.database_path_resolved).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "users.db"
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
    
    async def _init_db(self):
        """Инициализация базы данных."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    evm_wallet TEXT UNIQUE,
                    language TEXT DEFAULT 'ru',
                    free_requests_used INTEGER DEFAULT 0,
                    subscription_active BOOLEAN DEFAULT 0,
                    subscription_expires_at TEXT,
                    requests_limit INTEGER DEFAULT 0,
                    requests_used INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            
            # Миграция: добавляем поле language если его нет
            try:
                cursor = await db.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in await cursor.fetchall()]
                if 'language' not in columns:
                    await db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
                    await db.commit()
                    log.info("Поле language добавлено в таблицу users")
            except Exception as e:
                log.warning(f"Ошибка при миграции поля language: {e}")
            
            # Миграция: обновляем пустые строки в evm_wallet на NULL
            # Это нужно для избежания нарушения UNIQUE constraint
            try:
                await db.execute("UPDATE users SET evm_wallet = NULL WHERE evm_wallet = ''")
                updated_count = db.total_changes
                if updated_count > 0:
                    await db.commit()
                    log.info(f"Миграция: обновлено {updated_count} пользователей (пустые строки evm_wallet -> NULL)")
            except Exception as e:
                log.warning(f"Ошибка при миграции evm_wallet: {e}")
            
            log.info(f"База данных пользователей инициализирована: {self.db_path}")
    
    async def ensure_db_initialized(self):
        """Убедиться, что БД инициализирована."""
        if self._db_initialized:
            return
        
        async with self._init_lock:
            # Проверяем еще раз после получения блокировки
            if self._db_initialized:
                return
            
            await self._init_db()
            self._db_initialized = True
    
    async def register_user(self, user_id: int, username: Optional[str] = None, evm_wallet: Optional[str] = None) -> bool:
        """
        Регистрация нового пользователя.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            evm_wallet: EVM адрес кошелька (если уже создан)
        
        Returns:
            True если пользователь зарегистрирован, False если уже существует
        """
        await self.ensure_db_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем, существует ли пользователь
                cursor = await db.execute(
                    "SELECT user_id FROM users WHERE user_id = ?",
                    (user_id,)
                )
                existing = await cursor.fetchone()
                
                if existing:
                    # Обновляем username если изменился
                    if username:
                        await db.execute(
                            "UPDATE users SET username = ?, updated_at = ? WHERE user_id = ?",
                            (username, datetime.now().isoformat(), user_id)
                        )
                        await db.commit()
                    return False
                
                # Создаем нового пользователя
                # Используем NULL вместо пустой строки для evm_wallet, чтобы избежать нарушения UNIQUE constraint
                await db.execute("""
                    INSERT INTO users (
                        user_id, username, evm_wallet, language, free_requests_used,
                        subscription_active, requests_limit, requests_used, created_at, updated_at
                    ) VALUES (?, ?, ?, 'ru', 0, 0, 0, 0, ?, ?)
                """, (
                    user_id,
                    username or "",
                    evm_wallet if evm_wallet else None,  # NULL вместо пустой строки
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                await db.commit()
                log.info(f"Пользователь {user_id} (@{username}) зарегистрирован")
                return True
        except Exception as e:
            log.error(f"Ошибка регистрации пользователя {user_id}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о пользователе."""
        await self.ensure_db_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # Получаем язык, если поле существует (для обратной совместимости)
                row_keys = row.keys()
                language = row["language"] if "language" in row_keys else "ru"
                
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "evm_wallet": row["evm_wallet"] if row["evm_wallet"] else None,  # NULL -> None
                    "language": language,
                    "free_requests_used": row["free_requests_used"],
                    "subscription_active": bool(row["subscription_active"]),
                    "subscription_expires_at": row["subscription_expires_at"],
                    "requests_limit": row["requests_limit"],
                    "requests_used": row["requests_used"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        except Exception as e:
            log.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None
    
    async def set_evm_wallet(self, user_id: int, evm_wallet: str) -> bool:
        """Установить EVM кошелек для пользователя."""
        await self.ensure_db_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET evm_wallet = ?, updated_at = ? WHERE user_id = ?",
                    (evm_wallet, datetime.now().isoformat(), user_id)
                )
                await db.commit()
                log.info(f"EVM кошелек установлен для пользователя {user_id}: {evm_wallet}")
                return True
        except Exception as e:
            log.error(f"Ошибка установки EVM кошелька для {user_id}: {e}")
            return False
    
    async def increment_free_request(self, user_id: int) -> bool:
        """Увеличить счетчик бесплатных запросов."""
        await self.ensure_db_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET free_requests_used = free_requests_used + 1, updated_at = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                await db.commit()
                return True
        except Exception as e:
            log.error(f"Ошибка увеличения счетчика бесплатных запросов для {user_id}: {e}")
            return False
    
    async def increment_subscription_request(self, user_id: int) -> bool:
        """Увеличить счетчик запросов по подписке."""
        await self.ensure_db_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET requests_used = requests_used + 1, updated_at = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                await db.commit()
                return True
        except Exception as e:
            log.error(f"Ошибка увеличения счетчика запросов подписки для {user_id}: {e}")
            return False
    
    async def activate_subscription(self, user_id: int, requests_limit: int = 500, days: int = 30) -> bool:
        """
        Активировать подписку пользователя.
        
        Args:
            user_id: Telegram user ID
            requests_limit: Лимит запросов (500 для месячной подписки)
            days: Количество дней подписки (30 для месячной)
        """
        await self.ensure_db_initialized()
        
        try:
            expires_at = datetime.now() + timedelta(days=days)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users 
                    SET subscription_active = 1,
                        subscription_expires_at = ?,
                        requests_limit = ?,
                        requests_used = 0,
                        updated_at = ?
                    WHERE user_id = ?
                """, (
                    expires_at.isoformat(),
                    requests_limit,
                    datetime.now().isoformat(),
                    user_id
                ))
                await db.commit()
                log.info(f"Подписка активирована для пользователя {user_id} до {expires_at}")
                return True
        except Exception as e:
            log.error(f"Ошибка активации подписки для {user_id}: {e}")
            return False
    
    async def check_user_limits(self, user_id: int) -> Dict[str, Any]:
        """
        Проверить лимиты пользователя.
        
        Returns:
            dict: {
                'registered': bool,
                'can_make_request': bool,
                'free_requests_used': int,
                'free_requests_limit': int,
                'subscription_active': bool,
                'subscription_expires_at': Optional[datetime],
                'requests_used': int,
                'requests_limit': int,
                'evm_wallet': Optional[str]
            }
        """
        await self.ensure_db_initialized()
        
        user = await self.get_user(user_id)
        
        if not user:
            return {
                'registered': False,
                'can_make_request': False,
                'free_requests_used': 0,
                'free_requests_limit': settings.free_requests_per_day,
                'subscription_active': False,
                'subscription_expires_at': None,
                'requests_used': 0,
                'requests_limit': 0,
                'evm_wallet': None
            }
        
        # Проверяем, не истекла ли подписка
        subscription_active = user['subscription_active']
        subscription_expires_at = None
        
        if user['subscription_expires_at']:
            subscription_expires_at = datetime.fromisoformat(user['subscription_expires_at'])
            if subscription_expires_at < datetime.now():
                subscription_active = False
                # Обновляем статус в БД
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "UPDATE users SET subscription_active = 0, updated_at = ? WHERE user_id = ?",
                        (datetime.now().isoformat(), user_id)
                    )
                    await db.commit()
        
        # Определяем, может ли пользователь делать запрос
        can_make_request = False
        
        if subscription_active:
            # Проверяем лимит подписки
            can_make_request = user['requests_limit'] <= 0 or user['requests_used'] < user['requests_limit']
        else:
            # Проверяем бесплатный лимит
            can_make_request = user['free_requests_used'] < settings.free_requests_per_day
        
        return {
            'registered': True,
            'can_make_request': can_make_request,
            'free_requests_used': user['free_requests_used'],
            'free_requests_limit': settings.free_requests_per_day,
            'subscription_active': subscription_active,
            'subscription_expires_at': subscription_expires_at,
            'requests_used': user['requests_used'],
            'requests_limit': user['requests_limit'],
            'evm_wallet': user['evm_wallet']
        }


user_service = UserService()

