import re
from abc import ABC
from collections.abc import Sequence
from decimal import Decimal

from homework1.operations.operations import Operation, mark_operation


class AccountNumbersManager:
    def __init__(self, *, limit: int = 1_000_000) -> None:
        self.__occupied_ids = set()
        self.__counter = 0

        self.__limit = limit

        self.__pattern = "ACC-{:04}"

    def __extract_number(self, value: str) -> int:
        return int(value.split("-", maxsplit=1)[1])

    def _inc(self) -> int:
        """Метод является недетерминированным,
        т.е. его повторный вызов даст другое значение
        и будет иметь дальнейшие эффекты на работу всей системы

        :return:
        """
        while self.__counter < self.__limit and self.__counter in self.__occupied_ids:
            self.__counter += 1

        if self.__counter >= self.__limit:
            err = "Превышен лимит доступных аккаунтов"
            raise ValueError(err)

        return self.__counter

    @property
    def pattern(self) -> str:
        return self.__pattern

    def addgen(self, number: int | str | None = None) -> str:
        if number is None:
            number = self._inc()

        if isinstance(number, str):
            number = self.__extract_number(number)

        if number in self.__occupied_ids or number >= self.__limit:
            err = "Введённый вручную номер аккаунта недоступен"
            raise ValueError(err)

        self.__occupied_ids.add(number)

        return self.pattern.format(number)


class Account(ABC):
    def __init__(
        self,
        account_holder: str,
        account_number_manager: AccountNumbersManager,
        *,
        account_type: str,
        balance: Decimal = 0.0,
        account_number: int | str | None = None,
        allowed_operations: set[str] | None = None,
    ):
        assert account_type, "Тип аккаунта обязательно должен быть указан"
        self.__account_type = account_type

        self.__allowed_operations = {"deposit", "withdraw"} | (
            allowed_operations or set()
        )

        self.__holder = self.__validate_holder(account_holder)

        self._balance: Decimal = balance

        self.__account_number: str = account_number_manager.addgen(account_number)
        self.__operations_history: Sequence[Operation] = []

    @property
    def allowed_operations(self) -> set[str]:
        return self.__allowed_operations

    @property
    def account_number(self) -> str:
        return self.__account_number

    @property
    def account_type(self) -> str:
        return self.__account_type

    @property
    def holder(self) -> str:
        return self.__holder

    def get_balance(self) -> Decimal:
        return self._balance

    def get_history(self) -> list[Operation]:
        return self.__operations_history

    def search_history(self, limit: int = 5) -> list[Operation]:
        sorted_by_date_and_balance = sorted(
            [op for op in self.__operations_history if op.status == "success"],
            key=lambda _op: (
                abs(_op.balance_after - _op.balance_before),
                _op.created_at,
            ),
            reverse=True,
        )

        return sorted_by_date_and_balance[:limit]

    @mark_operation("deposit")
    def deposit(self, amount: Decimal) -> None:
        if amount <= 0:
            err = "Сумма депозита должна быть больше 0"
            raise NegativeDepositError(err)

        self._balance += amount

    @mark_operation("withdraw")
    def withdraw(self, amount: Decimal) -> None:
        if amount < 0:
            err = "Сумма снятия должна быть больше 0"
            raise ValueError(err)

        if self._balance - amount < 0:
            err = "Остаток на балансе после снятия должен быть больше или равен 0"
            raise ValueError(err)

        self._balance -= amount

    @staticmethod
    def __validate_holder(value: str) -> str:
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
        kwargs |= {"account_type": "checking"}
        super().__init__(*args, **kwargs)


class SavingsAccount(Account):
    def __init__(self, max_allowed_rate: float = 7.0, *args, **kwargs) -> None:
        self._max_allowed_rate = max_allowed_rate

        kwargs |= {"account_type": "savings"}
        super().__init__(*args, **kwargs, allowed_operations={"interest"})

    @mark_operation("interest")
    def apply_interest(self, rate: float) -> None:
        assert 0 < rate <= self._max_allowed_rate, (
            f"Размер процентной ставки не должен быть меньше 0 или больше максимальной процентной ставки max={self._max_allowed_rate}"
        )

        self._balance *= 1.0 + rate / 100.0

    @mark_operation("withdraw")
    def withdraw(self, amount: Decimal) -> None:
        if amount > self._balance * 0.5:
            err = "Нельзя снять больше 50% от текущего баланса"
            raise ValueError(err)

        super().withdraw(amount, __propagate_exc=True)
