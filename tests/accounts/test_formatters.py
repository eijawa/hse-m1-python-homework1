import pytest

from homework1.accounts.accounts import Account
from homework1.accounts.formatters import (
    CheckingAccountFormatter,
    SavingsAccountFormatter,
    UniversalAccountFormatter,
)


class DummyAccount(Account):
    account_type = "dummy"


CHECKING_TEXT = """Номер аккаунта: ACC-0000
Тип аккаунта: checking
Владелец(ица) аккаунта: Ivan Petrov
Баланс аккаунта: 100.0
"""

SAVINGS_TEXT = """Номер аккаунта: ACC-0000
Тип аккаунта: savings
Владелец(ица) аккаунта: Иван Петров
Баланс аккаунта: 100.0
Максимальная ставка - 7.0%"""


def test_checking_formatter(checking):
    assert CheckingAccountFormatter.format(checking) == CHECKING_TEXT


def test_savings_formatter(savings):
    assert SavingsAccountFormatter.format(savings) == SAVINGS_TEXT


def test_formatter_shows_current_balance(checking):
    checking.deposit(5.5)

    assert "Баланс аккаунта: 105.5\n" in CheckingAccountFormatter.format(checking)


def test_universal_formatter_checking(checking):
    assert UniversalAccountFormatter.format(checking) == CHECKING_TEXT


def test_universal_formatter_savings(savings):
    assert UniversalAccountFormatter.format(savings) == SAVINGS_TEXT


def test_universal_formatter_falls_back_to_base(manager):
    account = DummyAccount("Ivan Petrov", account_number_manager=manager)

    assert UniversalAccountFormatter.format(account) == (
        "Номер аккаунта: ACC-0000\n"
        "Тип аккаунта: dummy\n"
        "Владелец(ица) аккаунта: Ivan Petrov\n"
        "Баланс аккаунта: 0.0\n"
    )


@pytest.mark.parametrize("value", [None, "ACC-0000", object()])
def test_universal_formatter_rejects_non_account(value):
    with pytest.raises(NotImplementedError):
        UniversalAccountFormatter.format(value)
