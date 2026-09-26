from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial, wraps
from typing import Any, Literal

utcnowfn = partial(datetime.now, UTC)

OperationStatus = Literal["success", "fail"]


@dataclass
class Operation:
    name: str
    status: OperationStatus
    balance_before: Decimal

    details: Any

    # Поскольку операция может завершиться с ошибкой
    balance_after: Decimal | None = None

    # Я намерено опускаю существование modified_at,
    # поскольку здесь время выполнение операций минимально
    # и в рамках задачи им можно принебречь
    created_at: datetime = field(default_factory=utcnowfn)


def mark_operation(op_name: str):
    def decorator(fn):
        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            # Управленческая конструкция,
            # чтобы вернуть ошибку, а не замьютить её
            propagate_exc = kwargs.pop("__propagate_exc", False)

            op = Operation(
                name=op_name,
                status="fail",
                balance_before=self.get_balance(),
                details={"args": args, "kwargs": kwargs},
            )

            try:
                result = fn(self, *args, **kwargs)

                op.status = "success"

                return result
            except NegativeDepositError:
                # Тк нам тут ошибка на логическом уровне;
                # мы просто хотим прокинуть её наверх
                raise
            except Exception:
                op.status = "fail"

                if propagate_exc:
                    raise
            finally:
                op.balance_after = self.get_balance()

                if not propagate_exc:
                    self._operations_history.append(op)

        return wrapped

    return decorator


class NegativeDepositError(ValueError):
    pass


class Account:
    # ClassVar - глобальный подсчёт инициализированных классов,
    # здесь я его сделал через __, но обычно я бы делал через мета-класс,
    # если нам нужно такое поведение
    __account_counter: int = 0

    def __init__(self, account_holder: str, balance: Decimal = 0.0):
        assert account_holder, "Аккаунт не может быть без владельца"

        self._account_number: str = self.__gen_account_number()
        self._operations_history: list[Operation] = []

        self._balance: Decimal = balance

        self._holder = account_holder

    def __gen_account_number(self) -> str:
        value = f"ACC-{self.__account_counter:04}"

        Account.__account_counter += 1

        return value

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def holder(self) -> str:
        return self._holder

    def get_balance(self) -> Decimal:
        return self._balance

    def get_history(self) -> list[Operation]:
        return self._operations_history

    def search_history(self, limit: int = 5) -> list[Operation]:
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
    def deposit(self, amount: Decimal) -> None:
        if amount <= 0:
            err = "Сумма депозита должна быть больше 0"
            raise NegativeDepositError(err)

        self._balance += amount

    @mark_operation("withdraw")
    def withdraw(self, amount: Decimal) -> None:
        if amount < 0:
            err = "Сумма снятия должны быть больше 0"
            raise ValueError(err)

        if self._balance - amount < 0:
            err = "Остаток на балансе после снятия должен быть больше 0"
            raise ValueError(err)

        self._balance -= amount
