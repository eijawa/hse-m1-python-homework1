from datetime import UTC, datetime, timedelta

import pytest

from homework1.core.exc import NegativeDepositError
from homework1.operations.operations import Operation, mark_operation, utcnowfn


class FakeAccount:
    """Минимальный объект для проверки декоратора со своим ключом истории"""

    def __init__(self, balance=100.0) -> None:
        self.balance = balance
        self.history = []

    def get_balance(self):
        return self.balance

    @mark_operation("add", key="history")
    def add(self, amount=None):
        self.balance += amount
        return "ok"

    @mark_operation("boom", key="history")
    def boom(self, amount):
        self.balance -= amount
        raise ValueError("boom")

    @mark_operation("negative", key="history")
    def negative(self, amount):
        raise NegativeDepositError("negative")

    @mark_operation("noop", key="history")
    def noop(self):
        return "noop"


# --- Operation ---


def test_utcnowfn_returns_aware_utc():
    now = utcnowfn()

    assert now.tzinfo is UTC
    assert abs(datetime.now(UTC) - now) < timedelta(seconds=5)


def test_operation_defaults():
    op = Operation(name="deposit", status="success", value=10.0)

    assert op.balance_before is None
    assert op.balance_after is None
    assert op.created_at.tzinfo is UTC


def test_operation_created_at_is_unique_per_instance():
    first = Operation(name="a", status="success", value=1)
    second = Operation(name="a", status="success", value=1)

    assert first.created_at <= second.created_at


def test_negative_deposit_error_is_runtime_error():
    assert issubclass(NegativeDepositError, RuntimeError)


# --- mark_operation ---


def test_wraps_preserves_metadata():
    assert FakeAccount.add.__name__ == "add"
    assert FakeAccount.add.__wrapped__ is not None


def test_success_recorded():
    account = FakeAccount()

    assert account.add(5.0) == "ok"

    [op] = account.history
    assert op.name == "add"
    assert op.status == "success"
    assert op.value == 5.0
    assert op.balance_before == 100.0
    assert op.balance_after == 105.0


def test_failure_swallowed_and_recorded():
    account = FakeAccount()

    assert account.boom(5.0) is None

    [op] = account.history
    assert op.status == "fail"
    assert op.balance_before == 100.0
    assert op.balance_after == 95.0


def test_failure_propagated_and_not_recorded():
    account = FakeAccount()

    with pytest.raises(ValueError, match="boom"):
        account.boom(5.0, __propagate_exc=True)

    assert account.history == []


def test_success_with_propagate_not_recorded():
    account = FakeAccount()

    assert account.add(5.0, __propagate_exc=True) == "ok"
    assert account.history == []
    assert account.balance == 105.0


def test_negative_deposit_error_reraised_and_recorded_as_fail():
    account = FakeAccount()

    with pytest.raises(NegativeDepositError):
        account.negative(-1.0)

    [op] = account.history
    assert op.status == "fail"


def test_no_args_value_is_none():
    account = FakeAccount()

    assert account.noop() == "noop"

    [op] = account.history
    assert op.value is None
    assert op.status == "success"


def test_value_as_kwarg():
    account = FakeAccount()

    assert account.add(amount=5.0) == "ok"

    [op] = account.history
    assert (op.value, op.status, op.balance_after) == (5.0, "success", 105.0)


def test_value_as_kwarg_with_propagate():
    account = FakeAccount()

    account.add(amount=5.0, __propagate_exc=True)

    assert account.history == []
    assert account.balance == 105.0


def test_default_key():
    class Plain(FakeAccount):
        def __init__(self) -> None:
            super().__init__()
            self._operations_history = []

        @mark_operation("op")
        def op(self, amount):
            return amount

    account = Plain()

    assert account.op(7) == 7
    assert account._operations_history[0].value == 7
    assert account.history == []


def test_missing_history_attribute():
    class NoHistory(FakeAccount):
        @mark_operation("op")
        def op(self, amount):
            return amount

    with pytest.raises(AttributeError, match="_operations_history"):
        NoHistory().op(1)
