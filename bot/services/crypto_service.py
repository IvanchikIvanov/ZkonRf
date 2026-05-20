"""Сервис для работы с EVM кошельками и криптоплатежами."""
import asyncio
from typing import Optional, Dict, Any, List
from eth_account import Account
from bot.utils.config import settings
from bot.utils.logger import log
from bot.services.user_service import user_service
from bot.services.crypto_networks import (
    get_all_networks,
    get_network_config,
    NetworkConfig
)
from bot.services.token_checker import TokenChecker


class CryptoService:
    """Сервис для работы с криптовалютой."""
    
    def __init__(self):
        """Инициализация сервиса."""
        # Получаем список активных сетей из настроек
        enabled_networks = getattr(settings, 'crypto_enabled_networks', 'ethereum,bsc')
        self.enabled_network_ids = [n.strip() for n in enabled_networks.split(',')]
        
        # Инициализируем проверщики токенов для каждой сети
        self.token_checkers: Dict[str, TokenChecker] = {}
        
        for network_id in self.enabled_network_ids:
            try:
                checker = TokenChecker(network_id)
                self.token_checkers[network_id] = checker
                log.info(f"Инициализирован проверщик токенов для сети: {checker.network_config.name}")
            except Exception as e:
                log.error(f"Ошибка инициализации проверщика для сети {network_id}: {e}")
        
        if not self.token_checkers:
            log.warning("Не инициализировано ни одной сети для криптоплатежей!")
        
        # Адрес кошелька для приема платежей (master wallet)
        self.master_wallet = getattr(settings, 'crypto_master_wallet', '')
    
    def create_wallet(self) -> Dict[str, str]:
        """
        Создать новый EVM кошелек для пользователя.
        
        Returns:
            dict: {
                'address': str,  # Адрес кошелька
                'private_key': str  # Приватный ключ (НЕ передавать пользователю!)
            }
        """
        account = Account.create()
        return {
            'address': account.address,
            'private_key': account.key.hex()
        }
    
    async def create_user_wallet(self, user_id: int) -> Optional[str]:
        """
        Создать и сохранить EVM кошелек для пользователя.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Адрес кошелька или None при ошибке
        """
        if not self.master_wallet:
            log.warning(
                "Crypto payments disabled: CRYPTO_MASTER_WALLET is not configured. "
                "Refusing to create an unrecoverable per-user wallet."
            )
            return None
        
        try:
            address = self.master_wallet
            
            # Store only the configured receiving address; generated private wallets are not used.
            success = await user_service.set_evm_wallet(user_id, address)
            
            if success:
                log.info(f"EVM кошелек создан для пользователя {user_id}: {address}")
                return address
            else:
                log.error(f"Не удалось сохранить кошелек для пользователя {user_id}")
                return None
        except Exception as e:
            log.error(f"Ошибка создания кошелька для пользователя {user_id}: {e}")
            return None
    
    async def check_payment_received(self, user_id: int, network_id: Optional[str] = None) -> bool:
        """
        Проверить, получен ли платеж на кошелек пользователя.
        
        Args:
            user_id: Telegram user ID
            network_id: ID сети для проверки (если None, проверяет все сети)
        
        Returns:
            True если платеж получен и подписка активирована
        """
        user = await user_service.get_user(user_id)
        
        if not user or not user['evm_wallet']:
            return False
        
        wallet_address = user['evm_wallet']
        if self.master_wallet and wallet_address.lower() == self.master_wallet.lower():
            log.warning(
                "Crypto auto-activation skipped: shared CRYPTO_MASTER_WALLET balance "
                "cannot be attributed to a specific Telegram user."
            )
            return False
        
        # Определяем сети для проверки
        networks_to_check = [network_id] if network_id else list(self.token_checkers.keys())
        
        try:
            # Проверяем баланс в каждой сети
            for net_id in networks_to_check:
                if net_id not in self.token_checkers:
                    continue
                
                checker = self.token_checkers[net_id]
                
                # Проверяем, есть ли достаточный баланс
                if checker.check_payment_received(wallet_address):
                    # Если подписка еще не активирована, активируем
                    if not user['subscription_active']:
                        success = await user_service.activate_subscription(
                            user_id,
                            requests_limit=500,
                            days=30
                        )
                        
                        if success:
                            log.info(
                                f"Подписка активирована для пользователя {user_id} "
                                f"после пополнения кошелька {wallet_address} в сети {checker.network_config.name}. "
                                f"Баланс: {checker.format_balance(checker.check_usdt_balance(wallet_address)):.2f} USDT"
                            )
                            return True
            
            return False
        except Exception as e:
            log.error(f"Ошибка проверки платежа для пользователя {user_id}: {e}")
            return False
    
    async def get_wallet_info(self, address: str, network_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Получить информацию о кошельке во всех сетях или в конкретной сети.
        
        Args:
            address: Адрес кошелька
            network_id: ID сети (если None, возвращает информацию по всем сетям)
        
        Returns:
            dict с информацией о балансе в каждой сети
        """
        networks_to_check = [network_id] if network_id else list(self.token_checkers.keys())
        
        networks_info = {}
        total_balance_usdt = 0.0
        has_sufficient_balance = False
        
        for net_id in networks_to_check:
            if net_id not in self.token_checkers:
                continue
            
            checker = self.token_checkers[net_id]
            info = checker.get_wallet_info(address)
            networks_info[net_id] = info
            total_balance_usdt += info['balance_usdt']
            
            if info['has_sufficient_balance']:
                has_sufficient_balance = True
        
        return {
            'address': address,
            'networks': networks_info,
            'total_balance_usdt': total_balance_usdt,
            'has_sufficient_balance': has_sufficient_balance,
            'enabled_networks': list(self.token_checkers.keys())
        }
    
    def get_enabled_networks(self) -> List[Dict[str, Any]]:
        """
        Получить список доступных сетей.
        
        Returns:
            Список словарей с информацией о сетях
        """
        networks = []
        for network_id, checker in self.token_checkers.items():
            networks.append({
                'id': network_id,
                'name': checker.network_config.name,
                'symbol': checker.token_config.symbol,
                'min_payment_usdt': checker.format_min_payment(),
                'explorer_url': checker.network_config.explorer_url
            })
        return networks


crypto_service = CryptoService()
