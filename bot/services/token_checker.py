"""Сервис для проверки баланса токенов."""
from typing import Optional, Dict, Any
from web3 import Web3
from bot.services.crypto_networks import (
    get_network_config,
    get_token_config,
    get_min_payment_amount,
    NetworkConfig,
    TokenConfig
)
from bot.utils.logger import log


class TokenChecker:
    """Сервис для проверки баланса токенов."""
    
    # ABI для ERC20 токена (только функция balanceOf)
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        }
    ]
    
    def __init__(self, network_id: str):
        """
        Инициализация проверщика токенов.
        
        Args:
            network_id: ID сети (ethereum, bsc)
        """
        self.network_id = network_id
        self.network_config = get_network_config(network_id)
        self.token_config = get_token_config(network_id)
        
        if not self.network_config:
            raise ValueError(f"Неизвестная сеть: {network_id}")
        
        if not self.token_config:
            raise ValueError(f"Токен USDT не настроен для сети: {network_id}")
        
        self.w3 = self.network_config.get_web3()
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.token_config.address),
            abi=self.ERC20_ABI
        )
        self.min_payment = get_min_payment_amount(network_id)
    
    def check_usdt_balance(self, address: str) -> int:
        """
        Проверить баланс USDT токена.
        
        Args:
            address: Адрес кошелька
        
        Returns:
            Баланс в наименьших единицах токена (wei для USDT)
        """
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance = self.contract.functions.balanceOf(checksum_address).call()
            return balance
        except Exception as e:
            log.error(f"Ошибка проверки баланса USDT для {address} в сети {self.network_id}: {e}")
            return 0
    
    def check_payment_received(self, address: str) -> bool:
        """
        Проверить, получен ли платеж (баланс >= минимальной суммы).
        
        Args:
            address: Адрес кошелька
        
        Returns:
            True если баланс >= минимальной суммы
        """
        balance = self.check_usdt_balance(address)
        return balance >= self.min_payment
    
    def format_balance(self, balance: int) -> float:
        """
        Форматировать баланс в читаемый вид.
        
        Args:
            balance: Баланс в наименьших единицах
        
        Returns:
            Баланс в USDT
        """
        return balance / (10 ** self.token_config.decimals)
    
    def format_min_payment(self) -> float:
        """Получить минимальную сумму платежа в USDT."""
        return self.min_payment / (10 ** self.token_config.decimals)
    
    def get_wallet_info(self, address: str) -> Dict[str, Any]:
        """
        Получить информацию о кошельке.
        
        Args:
            address: Адрес кошелька
        
        Returns:
            dict с информацией о балансе и сети
        """
        balance_raw = self.check_usdt_balance(address)
        balance_usdt = self.format_balance(balance_raw)
        
        return {
            'address': address,
            'balance_raw': balance_raw,
            'balance_usdt': balance_usdt,
            'network': self.network_config.name,
            'network_id': self.network_id,
            'token_symbol': self.token_config.symbol,
            'min_payment_usdt': self.format_min_payment(),
            'explorer_url': self.network_config.explorer_url,
            'has_sufficient_balance': balance_raw >= self.min_payment
        }

