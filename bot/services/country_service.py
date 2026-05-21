"""Сервис для работы с выбором страны пользователя."""
from typing import Optional
from bot.services.cache_service import cache_service
from bot.utils.logger import log


# Поддерживаемые страны
SUPPORTED_COUNTRIES = {
    "ru": "🇷🇺 Россия",
    "kz": "🇰🇿 Казахстан",
    "am": "🇦🇲 Армения",
    "by": "🇧🇾 Беларусь",
    "tj": "🇹🇯 Таджикистан",
    "uz": "🇺🇿 Узбекистан",
    "az": "🇦🇿 Азербайджан",
    "thai": "🇹🇭 Таиланд",
    "vn": "🇻🇳 Вьетнам"
}


class CountryService:
    """Сервис для управления выбором страны пользователя."""
    
    @staticmethod
    async def get_user_country(user_id: int) -> str:
        """Получить выбранную страну пользователя."""
        country_key = f"user_country:{user_id}"
        country = await cache_service.get(country_key)
        return country if country else "ru"  # По умолчанию Россия
    
    @staticmethod
    async def set_user_country(user_id: int, country_code: str) -> bool:
        """Установить страну для пользователя."""
        if country_code not in SUPPORTED_COUNTRIES:
            log.warning(f"Попытка установить неподдерживаемую страну: {country_code}")
            return False
        
        country_key = f"user_country:{user_id}"
        await cache_service.set(country_key, country_code, ttl=86400 * 365)  # Храним год
        log.info(f"Установлена страна {country_code} для пользователя {user_id}")
        return True
    
    @staticmethod
    def get_country_name(country_code: str) -> str:
        """Получить название страны по коду."""
        return SUPPORTED_COUNTRIES.get(country_code, country_code.upper())
    
    @staticmethod
    def get_all_countries() -> dict:
        """Получить все поддерживаемые страны."""
        return SUPPORTED_COUNTRIES


country_service = CountryService()

