from typing import Generic, TypeVar

from homework1.accounts.accounts import Account, CheckingAccount, SavingsAccount

T = TypeVar("T", bound=Account)


class _AccountFormatter(Generic[T]):
    """Базовый форматтер для аккаунтов"""

    @classmethod
    def format(cls, account: T) -> str:
        """Метод форматирования аккаунта"""

        return f"""Номер аккаунта: {account.account_number}
Тип аккаунта: {account.account_type}
Владелец(ица) аккаунта: {account.holder}
Баланс аккаунта: {account.get_balance():03}
"""


class CheckingAccountFormatter(_AccountFormatter[CheckingAccount]):
    """Форматтер для аккаунтов типа - checking"""


class SavingsAccountFormatter(_AccountFormatter[SavingsAccount]):
    """Форматтер для аккаунтов типа - savings"""

    @classmethod
    def format(cls, account: SavingsAccount) -> str:
        return (
            super().format(account=account)
            + f"Максимальная ставка - {account.max_allowed_rate}%"
        )


class UniversalAccountFormatter:
    """Универсальный форматтер,
    который сам определяет тип аккаунта и применяет необходимый форматтер
    """

    # Таблица поддерживаемых типов аккаунтов
    _MAP = {
        CheckingAccount: CheckingAccountFormatter,
        SavingsAccount: SavingsAccountFormatter,
    }

    @classmethod
    def format(cls, account: Account) -> str:
        """Метод форматирования аккаунта"""

        for type_, formatter in cls._MAP.items():
            if isinstance(account, type_):
                return formatter.format(account=account)

        if isinstance(account, Account):
            return _AccountFormatter.format(account=account)

        raise NotImplementedError
