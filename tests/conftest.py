from datetime import UTC, datetime

import pytest

from homework1.accounts.account_number_manager import AccountNumbersManager
from homework1.accounts.accounts import CheckingAccount, SavingsAccount
from homework1.operations.operations import Operation


@pytest.fixture
def manager() -> AccountNumbersManager:
    """Свежий менеджер номеров, чтобы тесты не делили общее состояние"""
    return AccountNumbersManager()


@pytest.fixture
def small_manager() -> AccountNumbersManager:
    return AccountNumbersManager(limit=3)


@pytest.fixture
def checking(manager: AccountNumbersManager) -> CheckingAccount:
    return CheckingAccount(
        "Ivan Petrov", account_number_manager=manager, balance=100.0
    )


@pytest.fixture
def savings(manager: AccountNumbersManager) -> SavingsAccount:
    return SavingsAccount(
        account_holder="Иван Петров",
        account_number_manager=manager,
        balance=100.0,
    )


@pytest.fixture
def make_operation():
    def factory(
        *,
        name: str = "deposit",
        status: str = "success",
        value=10.0,
        balance_before=0.0,
        balance_after=10.0,
        created_at: datetime = datetime(2025, 1, 1, tzinfo=UTC),
    ) -> Operation:
        return Operation(
            name=name,
            status=status,
            value=value,
            balance_before=balance_before,
            balance_after=balance_after,
            created_at=created_at,
        )

    return factory
