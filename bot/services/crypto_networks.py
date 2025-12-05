"""Конфигурация криптосетей и токенов."""
from dataclasses import dataclass
from typing import Dict, Optional
from web3 import Web3
from web3.middleware import geth_poa_middleware


@dataclass
class NetworkConfig:
    """Конфигурация сети."""
    name: str
    rpc_url: str
    chain_id: int
    explorer_url: str
    requires_poa: bool = False
    native_symbol: str = "ETH"
    
    def get_web3(self) -> Web3:
        """Получить экземпляр Web3 для сети."""
        w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if self.requires_poa:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return w3


@dataclass
class TokenConfig:
    """Конфигурация токена."""
    address: str
    symbol: str
    decimals: int
    name: str


# Конфигурация сетей
NETWORKS: Dict[str, NetworkConfig] = {
    "ethereum": NetworkConfig(
        name="Ethereum",
        rpc_url="https://eth.drpc.org",
        chain_id=1,
        explorer_url="https://etherscan.io",
        requires_poa=False,
        native_symbol="ETH"
    ),
    "bsc": NetworkConfig(
        name="Binance Smart Chain",
        rpc_url="https://bsc-dataseed.binance.org",
        chain_id=56,
        explorer_url="https://bscscan.com",
        requires_poa=True,
        native_symbol="BNB"
    ),
}

# Конфигурация токенов USDT для каждой сети
USDT_TOKENS: Dict[str, TokenConfig] = {
    "ethereum": TokenConfig(
        address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        symbol="USDT",
        decimals=6,
        name="Tether USD (Ethereum)"
    ),
    "bsc": TokenConfig(
        address="0x55d398326f99059fF775485246999027B3197955",
        symbol="USDT",
        decimals=18,
        name="Tether USD (BSC)"
    ),
}

# Минимальная сумма платежа: $1 USDT
# USDT имеет 6 decimals на Ethereum и 18 decimals на BSC
MIN_PAYMENT_USD = 1.0
MIN_PAYMENT_USDT_ETHEREUM = int(1.0 * 10**6)  # 1 USDT с 6 decimals
MIN_PAYMENT_USDT_BSC = int(1.0 * 10**18)  # 1 USDT с 18 decimals

MIN_PAYMENT_AMOUNTS: Dict[str, int] = {
    "ethereum": MIN_PAYMENT_USDT_ETHEREUM,
    "bsc": MIN_PAYMENT_USDT_BSC,
}


def get_network_config(network_id: str) -> Optional[NetworkConfig]:
    """Получить конфигурацию сети."""
    return NETWORKS.get(network_id)


def get_token_config(network_id: str) -> Optional[TokenConfig]:
    """Получить конфигурацию токена USDT для сети."""
    return USDT_TOKENS.get(network_id)


def get_min_payment_amount(network_id: str) -> int:
    """Получить минимальную сумму платежа для сети."""
    return MIN_PAYMENT_AMOUNTS.get(network_id, MIN_PAYMENT_USDT_ETHEREUM)


def get_all_networks() -> Dict[str, NetworkConfig]:
    """Получить все доступные сети."""
    return NETWORKS.copy()

