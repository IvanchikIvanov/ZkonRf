#!/usr/bin/env python3
"""Проверка готовности контейнера бота (Redis + при pgvector — PostgreSQL)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


async def _main() -> int:
    from bot.utils.config import settings

    token = (settings.telegram_bot_token or "").strip()
    if ":" not in token:
        print("TELEGRAM_BOT_TOKEN некорректен", file=sys.stderr)
        return 1

    from bot.services.cache_service import cache_service

    await cache_service.connect()
    if not cache_service.is_available:
        print("Redis недоступен", file=sys.stderr)
        return 1
    await cache_service.disconnect()

    if (settings.vector_backend or "").lower() == "pgvector":
        dsn = (settings.postgres_database_url or "").strip()
        if dsn:
            try:
                import psycopg

                with psycopg.connect(dsn, connect_timeout=5) as conn:
                    conn.execute("SELECT 1")
            except Exception as e:
                print(f"PostgreSQL: {e}", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
