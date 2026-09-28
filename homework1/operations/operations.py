from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial, wraps
from typing import Literal

from homework1.core.exc import NegativeDepositError

# Всё по PEP
utcnowfn = partial(datetime.now, UTC)

# Доступные типы операций на уровне аннотаций
OperationStatus = Literal["success", "fail"]


@dataclass
class Operation:
    """Класс для сохраняемых в истории операций"""

    # Название операции
    name: str = field(metadata={"serialization_alias": "operation"})

    # Статус операции
    status: OperationStatus = field()

    # Значение, передаваемое в операции
    value: float = field(metadata={"serialization_alias": "amount"})

    # Баланс аккаунта до выполнения операции
    balance_before: float = field(default=0.0, metadata={"serialize_field": False})

    # Баланс аккаунта после выполнения операции.
    # None - поскольку операция может завершиться с ошибкой
    balance_after: float | None = None

    # Дата создания операции
    created_at: datetime = field(
        default_factory=utcnowfn, metadata={"serialization_alias": "date"}
    )


def mark_operation(op_name: str, *, key: str = "_operations_history"):
    """Декоратор с параметрами для записи операции в историю

    * "Глушить" в контексте этой функции - означает не передавать ошибку наверх, а решать её в рамках текущей функции

    :param op_name: Название операции
    :param key: Ключ, в котором хранится история в рамках текущего объекта
    """

    def decorator(fn):
        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            # Управленческая конструкция,
            # чтобы вернуть ошибку, а не зашлушить её
            propagate_exc = kwargs.pop("__propagate_exc", False)

            value = None
            if args:
                value = args[0]
            elif kwargs:
                value = next(iter(kwargs.values()))

            op = Operation(
                name=op_name,
                status="fail",
                balance_before=self.get_balance(),
                value=value,  # Условно считаем, что значение будет всегда передано
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

                # Если мы не должны глушить ошибку, то возвращаем её
                if propagate_exc:
                    raise
            finally:
                op.balance_after = self.get_balance()

                # Поскольку это блок finally,
                # то нам необходимо дополнительно проверить, что мы не хотим глушить ошибку.
                # Если мы её всё же глушим, то добавляем запись об ошибке в историю
                if not propagate_exc:
                    getattr(self, key).append(op)

        return wrapped

    return decorator
