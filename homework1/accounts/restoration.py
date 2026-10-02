"""Мне этот модуль очень не нравится, но в целом свою работу он выполняет"""

from homework1.accounts.account_number_manager import AccountNumbersManager
from homework1.accounts.accounts import Account, CheckingAccount, SavingsAccount
from homework1.operations.operations import Operation


class AccountRestoreError(Exception):
    """Произошла ошибка при восстановлении аккаунта"""


class AccountRestoreManager:
    """Класс, содержащий методы для восстановления аккаунтов из истории"""

    # Список поддерживающих восстановление типов аккаунтов
    _RESTORABLE_ACCOUNTS: tuple[type[Account], ...] = (CheckingAccount, SavingsAccount)

    @classmethod
    def restore(
        cls,
        account_type: str,
        account_number_manager: AccountNumbersManager,
        operations: list[Operation],
        account_number: int | str | None = None,
        strict: bool = True,
    ) -> CheckingAccount | SavingsAccount:
        """Метод восстановления аккаунта из истории

        :param account_type: Тип аккаунта
        :param account_number_manager: Менеджер номеров аккаунтов
        :param operations: История операций
        :param account_number: Номер аккаунта
        :param strict: Установка режима валидации.
        При установке в True - любая фатальная ошибка валидации будет приводить к невозможности создания аккаунта
        :return: Восстановленный аккаунт

        :raise AccountRestoreError: Если установлен параметр strict и произошла ошибка на уровне операций
        или если произошла ошибка на этапе создания аккаунта (strict=False не поможет в этом случае)
        """
        account_cls: type[Account] | None = None
        for acc_cls in cls._RESTORABLE_ACCOUNTS:
            if acc_cls.account_type == account_type:
                account_cls = acc_cls
                break

        if account_cls is None:
            err = "Аккаунт этого типа невозможно восстановить"
            raise ValueError(err)

        try:
            account = account_cls(
                account_holder="Unknown Account",
                account_number=account_number,
                account_number_manager=account_number_manager,
                enable_balance_override=True,
            )
            operations = cls.clean_history(account, operations)

            # Переопределяем стартовый баланс на основе самой первой операции из истории,
            # чтобы валидация шла на уровне согласованности данных
            account.add_operation_to_history(operations[0])
            account.override_balance(operations[0].balance_after)
            account.disable_balance_override()
        except Exception as e:
            err = f"Произошла ошибка при восстановлении аккаунта: {e}"
            raise AccountRestoreError(err) from e

        for op in operations[1:]:
            fn = getattr(account, op.name, None)

            # Очень костыльный метод, тк я бы завёл список вида <операция:метод> в каждом классе,
            # но это нужно много переписать, тк тогда я бы хотел сделать и автоматическое применение
            # декоратора для установки истории операции, а тогда почему бы и не переписать саму историю
            # на внешний класс-хранилище, но это долго...
            # В общем да, мне самому не нравится
            if not fn and account_cls == SavingsAccount and op.name == "interest":
                fn = account.apply_interest

            try:
                fn(op.value)

                balance = account.get_balance()

                if op.balance_after != balance:
                    err = f"Итоговый баланс после применения операции не соответствует балансу, указанному в истории ({balance} != {op.balance_after})"
                    raise ValueError(err)
            except ValueError as e:
                print(str(e))
            except Exception as e:
                if strict:
                    err = f"Произошла ошибка при восстановлении аккаунта: {e}"
                    raise AccountRestoreError(err) from e

                err = f"Произошла фатальная ошибка, из-за которой аккаунт не должен быть создан, но параметр {strict=}: {e}"
                print(err)

        return account

    @classmethod
    def clean_history(
        cls, account: Account, history: list[Operation]
    ) -> list[Operation]:
        """Крайне топорный метод очистки истории от априори невозможных типов операции над аккаунтом"""
        result = []

        for operation in history:
            if operation.name not in account.allowed_operations:
                continue

            result.append(operation)

        return result
