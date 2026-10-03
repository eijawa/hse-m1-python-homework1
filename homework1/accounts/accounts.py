import re
from abc import ABC

from homework1.core.exc import NegativeDepositError
from homework1.operations.operations import Operation, mark_operation

from homework1.accounts.account_number_manager import AccountNumbersManager


class Account(ABC):
    account_type: str

    def __init__(
        self,
        account_holder: str,
        *,
        account_number_manager: AccountNumbersManager,
        balance: float = 0.0,
        account_number: int | str | None = None,
        allowed_operations: set[str] | None = None,
        enable_balance_override: bool = False,
    ):
        """Базовый класс для всех аккаунтов.

        :param account_holder: Имя Фамилия владельца аккаунта
        :param account_type: Тип аккаунта. Указывается в наследниках класса
        :param account_number_manager: Менеджер номеров аккаунтов
        :param balance: Изначальный баланс аккаунта
        :param account_number: Номер аккаунта
        :param allowed_operations: Список доступных операций аккаунта. Указывается в наследниках класса
        """
        # Список доступных операций над данным аккаунтом
        self.__allowed_operations = {"deposit", "withdraw"} | (
            allowed_operations or set()
        )

        self.__holder = self.__validate_holder(account_holder)

        self.__is_balance_override_enabled = enable_balance_override
        self._balance = balance

        self.__account_number: str = account_number_manager.addgen(account_number)
        self._operations_history: list[Operation] = []

    def __validate_holder(self, value: str) -> str:
        """Валидатор Имени Фамилии владельца аккаунта

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raise ValueError: В случае провальной валидации
        """
        _title_word_patter = "[А-ЯA-Z][а-яa-z]+"
        _pattern = f"^{_title_word_patter}\\s{_title_word_patter}$"
        _pattern = re.compile(_pattern)

        if not isinstance(value, str) or not value:
            err = "Значение должно быть строкой"
            raise ValueError(err)

        if not re.fullmatch(_pattern, value):
            err = "Имя владельца счёта должно быть в формате «Имя Фамилия» с заглавных букв, кириллицей или латиницей"
            raise ValueError(err)

        return value

    def _validate_float(self, value: float) -> float:
        """Валидатор значения типа float

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raises ValueError: В случае провально валидации
        """
        if value is None or not isinstance(value, float):
            err = "Переданное значение должно быть валидным числом"
            raise ValueError(err)

        return value

    def _validate_deposit(self, value: float) -> float:
        """Валидатор значения для использовании в функции депозита

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raises ValueError: В случае провально валидации
        """
        value = self._validate_float(value)

        if value <= 0:
            err = "Сумма депозита должна быть больше 0"
            raise NegativeDepositError(err)

        return value

    def _validate_withdraw(self, value: float) -> float:
        """Валидатор значения для использования в функции снятия

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raises ValueError: В случае провально валидации
        """
        value = self._validate_float(value)

        if value < 0:
            err = "Сумма снятия должна быть больше 0"
            raise ValueError(err)

        if self._balance - value < 0:
            err = "Остаток на балансе после снятия должен быть больше или равен 0"
            raise ValueError(err)

        return value

    @property
    def allowed_operations(self) -> set[str]:
        """Список доступных операций над аккаунтом"""
        return self.__allowed_operations

    @property
    def account_number(self) -> str:
        """Номер аккаунта"""
        return self.__account_number

    @property
    def holder(self) -> str:
        """Имя Фамилия владельца аккаунта"""
        return self.__holder

    def get_balance(self) -> float:
        """Метод получения текущего баланса.
        Выполнен таким образом в соответствие с заданием
        """
        return self._balance

    def override_balance(self, balance: float) -> None:
        """Спец. метод для перезаписи баланса аккаунта без операции.
        Срабатывает только если установлен специальный флаг при создании аккаунта
        """
        if self.__is_balance_override_enabled:
            self._balance = self._validate_float(balance)

    def disable_balance_override(self) -> None:
        """Спец. метод для отключения возможности перезаписи баланса аккаунта без операции"""
        self.__is_balance_override_enabled = False

    def get_history(self) -> list[Operation]:
        """Метод получения истории операций.
        Выполнен таким образом в соответствие с заданием
        """
        return self._operations_history

    def add_operation_to_history(self, op: Operation) -> None:
        """Метод для добавления операции в историю из вне"""
        self._operations_history.append(op)

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
        self._balance += self._validate_deposit(amount)

    @mark_operation("withdraw")
    def withdraw(self, amount: float) -> None:
        """Операция снятия суммы со счёта

        :param amount: Сумма снятия

        :raise ValueError: Возникает при ошибках валидации суммы или итогового баланса
        """
        self._balance -= self._validate_withdraw(amount)


class CheckingAccount(Account):
    account_type: str = "checking"

    def __init__(self, *args, **kwargs) -> None:
        """Аккаунт - Расчётный счёт"""
        # Не даём расширить список доступных операций
        kwargs.pop("allowed_operations", None)

        super().__init__(*args, **kwargs)


class SavingsAccount(Account):
    account_type: str = "savings"

    def __init__(self, *args, max_allowed_rate: float = 7.0, **kwargs) -> None:
        """Аккаунт - Сберегательный счёт

        :param max_allowed_rate: Максимальная процентная ставка по счёту
        """
        self._max_allowed_rate = max_allowed_rate

        # Не даём расширить список доступных операций
        kwargs.pop("allowed_operations", None)

        super().__init__(*args, **kwargs, allowed_operations={"interest"})

    def _validate_withdraw(self, value: float) -> float:
        """Валидатор значения для использования в функции снятия

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raises ValueError: В случае провально валидации
        """
        value = super()._validate_withdraw(value)

        if value > self._balance * 0.5:
            err = "Нельзя снять больше 50% от текущего баланса"
            raise ValueError(err)

        return value

    def _validate_interest(self, value: float) -> float:
        """Валидатор значения для использования в функции применения процентной ставки

        :param value: Кандидат на значение
        :return: Отвалидированное значение в случае успешной валидации

        :raises ValueError: В случае провально валидации
        """
        value = self._validate_float(value)

        if value <= 0 or value > self.max_allowed_rate:
            err = f"Размер процентной ставки не должен быть меньше 0 или больше максимальной процентной ставки max={self._max_allowed_rate}"
            raise ValueError(err)

        return value

    @property
    def max_allowed_rate(self) -> float:
        """Максимальная процентная ставка"""
        return self._max_allowed_rate

    @mark_operation("interest")
    def apply_interest(self, rate: float) -> None:
        """Операция применения процентной ставки на сумму счёта

        :param rate: Размер процентной ставки

        :raise ValueError: Возникает при ошибках валидации ставки
        """
        rate = self._validate_interest(rate)
        self._balance *= 1.0 + rate / 100.0
