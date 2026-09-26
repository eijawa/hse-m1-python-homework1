import re
from icecream import ic
from decimal import Decimal
import random

from .p1 import Account, mark_operation


class HolderValidationMixin:
    def __init__(self, *args, **kwargs) -> None:
        _key_arg = "account_holder"
        _key_pos = 0

        _holder: str = kwargs.get(_key_arg, "")
        if not _holder and args:
            _holder = args[_key_pos]

        assert _holder, "Параметр владельца аккаунта не передан"
        HolderValidationMixin.__validate_holder(_holder)

        super().__init__(*args, **kwargs)

    @staticmethod
    def __validate_holder(value: str) -> str:
        _title_word_patter = "[А-ЯA-Z][а-яa-z]+"
        _pattern = f"^{_title_word_patter}\\s{_title_word_patter}$"
        _pattern = re.compile(_pattern)

        if not isinstance(value, str):
            err = "Значение должно быть строкой"
            raise ValueError(err)

        if not re.fullmatch(_pattern, value):
            err = "Имя владельца счёта должно быть в формате «Имя Фамилия» с заглавных букв, кириллицей или латиницей"
            raise ValueError(err)

        return value


class CheckingAccount(HolderValidationMixin, Account):
    def __init__(self, *args, **kwargs) -> None:
        self.__account_type = "checking"

        super().__init__(*args, **kwargs)


class SavingsAccount(HolderValidationMixin, Account):
    def __init__(self, max_allowed_rate: float = 7.0, *args, **kwargs) -> None:
        self.__account_type = "savings"
        self._max_allowed_rate = max_allowed_rate

        super().__init__(*args, **kwargs)

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


if __name__ == "__main__":
    acc1 = CheckingAccount("Евгений Увеонович")
    print(acc1.holder)

    acc2 = SavingsAccount(8.0, "Холдер Аликович", balance=100)
    print(acc2.holder)
    acc2.apply_interest(5)
    print(acc2.get_balance())
    acc2.withdraw(53)
    ic(acc2.get_history())

    acc3 = CheckingAccount("Barbara Ari")
    print(acc3.holder)

    for i in range(50):
        amount = random.randint(1, 100)

        if i % 2 == 0:
            acc3.deposit(amount)
        else:
            acc3.withdraw(amount)

    # print(acc3.get_history())
    h = acc3.search_history()
    for _ in range(100002):
        acc = Account("a")

    print(acc.account_number)

    acc4 = CheckingAccount("холдер")
