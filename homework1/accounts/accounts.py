import re
from abc import ABC
from collections.abc import Sequence

from homework1.core.exc import NegativeDepositError
from homework1.operations.operations import Operation, mark_operation

from .account_number_manager import AccountNumbersManager


class Account(ABC):
    def __init__(
        self,
        account_holder: str,
        *,
        account_type: str,
        account_number_manager: AccountNumbersManager,
        balance: float = 0.0,
        account_number: int | str | None = None,
        allowed_operations: set[str] | None = None,
    ):
        """Базовый класс для всех аккаунтов.

        :param account_holder: Имя Фамилия владельца аккаунта
        :param account_type: Тип аккаунта. Указывается в наследниках класса
        :param account_number_manager: Менеджер номеров аккаунтов
        :param balance: Изначальный баланс аккаунта
        :param account_number: Номер аккаунта
        :param allowed_operations: Список доступных операций аккаунта. Указывается в наследниках класса
        """
        # Дополнительная проверка на всякий случай, чтобы о ней не забыли при наследовании
        assert account_type, "Тип аккаунта обязательно должен быть указан"
        self.__account_type = account_type

        # Список доступных операций над данным аккаунтом
        self.__allowed_operations = {"deposit", "withdraw"} | (
            allowed_operations or set()
        )

        self.__holder = self.__validate_holder(account_holder)

        self._balance = balance

        self.__account_number: str = account_number_manager.addgen(account_number)
        self._operations_history: Sequence[Operation] = []

    @property
    def allowed_operations(self) -> set[str]:
        """Список доступных операций над аккаунтом"""
        return self.__allowed_operations

    @property
    def account_number(self) -> str:
        """Номер аккаунта"""
        return self.__account_number

    @property
    def account_type(self) -> str:
        """Тип аккаунта"""
        return self.__account_type

    @property
    def holder(self) -> str:
        """Имя Фамилия владельца аккаунта"""
        return self.__holder

    def get_balance(self) -> float:
        """Метод получения текущего баланса.
        Выполнен таким образом в соответствие с заданием
        """
        return self._balance

    def get_history(self) -> list[Operation]:
        """Метод получения истории операций.
        Выполнен таким образом в соответствие с заданием
        """
        return self._operations_history

    def search_history(self, limit: int = 5) -> list[Operation]:
        """Поиск последних операций с сильнее всего повлиявших на баланс аккаунта.

        Под "влиянием" подразумевается наибольшая абсолютная разница
        между состояниями баланса перед применением операции и после неё.
        Учитываются только успешные операции

        :param limit: Лимит возвращаемых операций
        :return: Список из проделанных операций
        """
        sorted_by_date_and_balance = sorted(
            [op for op in self._operations_history if op.status == "success"],
            key=lambda _op: (
                abs(_op.balance_after - _op.balance_before),
                _op.created_at,
            ),
            reverse=True,
        )

        return sorted_by_date_and_balance[:limit]

    @mark_operation("deposit")
    def deposit(self, amount: float) -> None:
        """Операция внесения суммы на счёт

        :param amount: Сумма внесения

        :raise NegativeDepositError: Критическая ошибка, возникшая при попытке внесения негативной суммы
        """
        if amount <= 0:
            err = "Сумма депозита должна быть больше 0"
            raise NegativeDepositError(err)

        self._balance += amount

    @mark_operation("withdraw")
    def withdraw(self, amount: float) -> None:
        """Операция снятия суммы со счёта

        :param amount: Сумма снятия

        :raise ValueError: Возникает при ошибках валидации суммы или итогового баланса
        """
        if amount < 0:
            err = "Сумма снятия должна быть больше 0"
            raise ValueError(err)

        if self._balance - amount < 0:
            err = "Остаток на балансе после снятия должен быть больше или равен 0"
            raise ValueError(err)

        self._balance -= amount

    @staticmethod
    def __validate_holder(value: str) -> str:
        """Валидатор Имени Фамилии владельца аккаунта

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raise ValueError: В случае провальной валидации
        """
        _title_word_patter = "[А-ЯA-Z][а-яa-z]+"
        _pattern = f"^{_title_word_patter}\\s{_title_word_patter}$"
        _pattern = re.compile(_pattern)

        if not isinstance(value, str) or not str:
            err = "Значение должно быть строкой"
            raise ValueError(err)

        if not re.fullmatch(_pattern, value):
            err = "Имя владельца счёта должно быть в формате «Имя Фамилия» с заглавных букв, кириллицей или латиницей"
            raise ValueError(err)

        return value


class CheckingAccount(Account):
    def __init__(self, *args, **kwargs) -> None:
        """Аккаунт - Расчётный счёт"""
        kwargs |= {"account_type": "checking"}

        # Не даём расширить список доступных операций
        kwargs.pop("allowed_operations", None)

        super().__init__(*args, **kwargs)


class SavingsAccount(Account):
    def __init__(self, max_allowed_rate: float = 7.0, *args, **kwargs) -> None:
        """Аккаунт - Сберегательный счёт

        :param max_allowed_rate: Максимальная процентная ставка по счёту
        """
        self._max_allowed_rate = max_allowed_rate

        kwargs |= {"account_type": "savings"}

        # Не даём расширить список доступных операций
        kwargs.pop("allowed_operations", None)

        super().__init__(*args, **kwargs, allowed_operations={"interest"})

    @mark_operation("interest")
    def apply_interest(self, rate: float) -> None:
        """Операция применения процентной ставки на сумму счёта

        :param rate: Размер процентной ставки

        :raise ValueError: Возникает при ошибках валидации ставки
        """
        if rate <= 0 or rate > self._max_allowed_rate:
            err = f"Размер процентной ставки не должен быть меньше 0 или больше максимальной процентной ставки max={self._max_allowed_rate}"
            raise ValueError(err)

        self._balance *= 1.0 + rate / 100.0

    @mark_operation("withdraw")
    def withdraw(self, amount: float) -> None:
        if amount > self._balance * 0.5:
            err = "Нельзя снять больше 50% от текущего баланса"
            raise ValueError(err)

        # Глушим родительский mark_operation,
        # чтобы не записывать в историю дважды
        super().withdraw(amount, __propagate_exc=True)
