"""Модуль с примерами создания и отображения операций"""

from homework1.accounts.account_number_manager import AccountNumbersManager
from homework1.accounts.accounts import Account, CheckingAccount, SavingsAccount
from homework1.accounts.formatters import UniversalAccountFormatter
from homework1.operations.formatters import OperationsTableFormatter


def _perform_default_ops(account: Account) -> None:
    account.deposit(100.0)
    try:
        account.deposit(-100.0)
    except Exception as e:
        err = f"Операция завершилась с ошибкой: {e}"
        print(err)

    account.deposit(20.0)
    account.withdraw(15.0)

    try:
        account.withdraw(1000.0)
    except Exception as e:
        err = f"Операция завершилась с ошибкой: {e}"
        print(err)


def _make_checking_account(anm: AccountNumbersManager) -> CheckingAccount:
    account = CheckingAccount("Barbara Hoppkins", account_number_manager=anm)

    _perform_default_ops(account)

    return account


def _make_savings_account(anm: AccountNumbersManager) -> SavingsAccount:
    account = SavingsAccount("Алина Бережливая", account_number_manager=anm)

    _perform_default_ops(account)

    try:
        account.apply_interest(10.0)
    except Exception as e:
        err = f"Операция завершилась с ошибкой: {e}"
        print(err)

    account.apply_interest(5.0)

    return account


if __name__ == "__main__":
    ANM = AccountNumbersManager()
    operations_formatter = OperationsTableFormatter()

    for make_account_fn in (_make_checking_account, _make_savings_account):
        account = make_account_fn(ANM)

        print(UniversalAccountFormatter.format(account))
        print(operations_formatter.format(account.get_history()))
