"""Модуль с примерами восстановления аккаунтов из истории"""

from pathlib import Path

from homework1.accounts.account_number_manager import AccountNumbersManager
from homework1.accounts.formatters import UniversalAccountFormatter
from homework1.accounts.restoration import AccountRestoreManager
from homework1.operations.formatters import OperationsTableFormatter
from homework1.operations.serialization import (
    AccountOperations,
    OperationsHistoryCSVFSStorageHandler,
)

SRC_DIRPATH = Path(__file__).parent.parent
DATA_DIRPATH = SRC_DIRPATH / "data"
TRANSACTIONS_FILEPATH = DATA_DIRPATH / "transactions_dirty.csv"


def _restore_accounts(history: list[AccountOperations], strict: bool = True) -> None:
    anm = AccountNumbersManager()

    accounts = []
    for account_number, account_type, operations in history:
        try:
            account = AccountRestoreManager.restore(
                account_type=account_type,
                account_number=account_number,
                operations=operations,
                account_number_manager=anm,
                strict=strict,
            )

            accounts.append(account)
        except Exception as e:
            err = f"Невозможно восстановить аккаунт {account_number=} из-за фатальной ошибки {e.__class__.__name__}: {e}"
            print(err)

    print("Восстановленные аккаунты:")
    for account in accounts:
        print(UniversalAccountFormatter.format(account))
        print(operations_formatter.format(account.get_history()))


if __name__ == "__main__":
    operations_formatter = OperationsTableFormatter()

    csv_history_handler = OperationsHistoryCSVFSStorageHandler()
    history = csv_history_handler.load(TRANSACTIONS_FILEPATH)

    print(
        "Восстановление аккаунтов в строгом режиме. Любая фатальная ошибка приведёт к невозможности восстановления аккаунта"
    )
    _restore_accounts(history, strict=True)

    print(
        "Восстановление аккаунтов в упрощённом режиме. Любые фатальные ошибки пропускаются"
    )
    _restore_accounts(history, strict=False)
