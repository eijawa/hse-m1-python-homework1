from datetime import UTC, datetime

import pytest

from homework1.accounts.accounts import Account, CheckingAccount, SavingsAccount
from homework1.core.exc import NegativeDepositError

HISTORY_ATTR = "_operations_history"


class DummyAccount(Account):
    pass


# --- Создание и свойства ---


def test_checking_properties(checking):
    assert checking.holder == "Ivan Petrov"
    assert checking.account_type == "checking"
    assert checking.account_number == "ACC-0000"
    assert checking.allowed_operations == {"deposit", "withdraw"}
    assert checking.get_balance() == 100.0
    assert checking.get_history() == []


def test_savings_properties(savings):
    assert savings.holder == "Иван Петров"
    assert savings.account_type == "savings"
    assert savings.allowed_operations == {"deposit", "withdraw", "interest"}
    assert savings._max_allowed_rate == 7.0


def test_savings_custom_max_rate(manager):
    account = SavingsAccount(
        10.0, account_holder="Ivan Petrov", account_number_manager=manager
    )

    assert account._max_allowed_rate == 10.0


def test_default_balance_is_float_zero(manager):
    account = CheckingAccount("Ivan Petrov", account_number_manager=manager)

    assert account.get_balance() == 0.0
    assert isinstance(account.get_balance(), float)


def test_manual_account_number(manager):
    account = CheckingAccount(
        "Ivan Petrov", account_number_manager=manager, account_number="ACC-0123"
    )

    assert account.account_number == "ACC-0123"


def test_duplicate_account_number_raises(manager):
    CheckingAccount("Ivan Petrov", account_number_manager=manager, account_number=1)

    with pytest.raises(ValueError, match="недоступен"):
        CheckingAccount(
            "Ivan Petrov", account_number_manager=manager, account_number=1
        )


def test_accounts_get_unique_numbers(manager):
    first = CheckingAccount("Ivan Petrov", account_number_manager=manager)
    second = SavingsAccount(account_holder="Ivan Petrov", account_number_manager=manager)

    assert first.account_number != second.account_number


@pytest.mark.parametrize("cls", [CheckingAccount, SavingsAccount])
def test_allowed_operations_cannot_be_extended(manager, cls):
    account = cls(
        account_holder="Ivan Petrov",
        account_number_manager=manager,
        allowed_operations={"hack"},
    )

    assert "hack" not in account.allowed_operations


@pytest.mark.parametrize("cls", [CheckingAccount, SavingsAccount])
def test_account_type_cannot_be_overridden(manager, cls):
    account = cls(
        account_holder="Ivan Petrov",
        account_number_manager=manager,
        account_type="other",
    )

    assert account.account_type != "other"


def test_base_account_with_extra_operations(manager):
    account = DummyAccount(
        "Ivan Petrov",
        account_type="dummy",
        account_number_manager=manager,
        allowed_operations={"transfer"},
    )

    assert account.allowed_operations == {"deposit", "withdraw", "transfer"}


def test_base_account_requires_account_type(manager):
    with pytest.raises(AssertionError, match="Тип аккаунта"):
        DummyAccount("Ivan Petrov", account_type="", account_number_manager=manager)


# --- Валидация владельца ---


@pytest.mark.parametrize("holder", ["Ivan Petrov", "Иван Петров", "Ab Cd"])
def test_valid_holder(manager, holder):
    account = CheckingAccount(holder, account_number_manager=manager)

    assert account.holder == holder


@pytest.mark.parametrize(
    "holder",
    [
        "ivan petrov",
        "Ivan petrov",
        "Ivan",
        "Ivan Petrov Sidorov",
        "Ivan  Petrov",
        "I Petrov",
        "IVAN PETROV",
        "Ivan-Petrov",
        "Ёжик Петров",
        "",
    ],
)
def test_invalid_holder_format(manager, holder):
    with pytest.raises(ValueError, match="Имя Фамилия"):
        CheckingAccount(holder, account_number_manager=manager)


@pytest.mark.parametrize("holder", [None, 123, ["Ivan Petrov"]])
def test_holder_must_be_string(manager, holder):
    with pytest.raises(ValueError, match="строкой"):
        CheckingAccount(holder, account_number_manager=manager)


# --- Операции через декоратор ---


def _single_operation(account):
    [op] = account.get_history()
    return op


def test_deposit_recorded(checking):
    assert checking.deposit(10.0) is None

    op = _single_operation(checking)
    assert (op.name, op.status, op.value) == ("deposit", "success", 10.0)
    assert (op.balance_before, op.balance_after) == (100.0, 110.0)
    assert checking.get_balance() == 110.0


def test_withdraw_recorded(checking):
    checking.withdraw(30.0)

    op = _single_operation(checking)
    assert (op.name, op.status, op.value) == ("withdraw", "success", 30.0)
    assert (op.balance_before, op.balance_after) == (100.0, 70.0)


@pytest.mark.parametrize("amount", [-1.0, 100.01])
def test_failed_withdraw_swallowed_and_recorded(checking, amount):
    assert checking.withdraw(amount) is None

    op = _single_operation(checking)
    assert (op.name, op.status, op.value) == ("withdraw", "fail", amount)
    assert op.balance_before == op.balance_after == 100.0


@pytest.mark.parametrize("amount", [0.0, -5.0])
def test_negative_deposit_raises_and_recorded(checking, amount):
    with pytest.raises(NegativeDepositError):
        checking.deposit(amount)

    op = _single_operation(checking)
    assert (op.name, op.status) == ("deposit", "fail")
    assert checking.get_balance() == 100.0


def test_operations_accumulate_in_order(checking):
    checking.deposit(50.0)
    checking.withdraw(500.0)
    checking.withdraw(20.0)

    assert [(op.name, op.status) for op in checking.get_history()] == [
        ("deposit", "success"),
        ("withdraw", "fail"),
        ("withdraw", "success"),
    ]
    assert checking.get_balance() == 130.0


def test_histories_are_independent(checking, savings):
    checking.deposit(10.0)

    assert savings.get_history() == []


def test_savings_withdraw_recorded_once(savings):
    savings.withdraw(10.0)

    op = _single_operation(savings)
    assert (op.name, op.status, op.value) == ("withdraw", "success", 10.0)
    assert (op.balance_before, op.balance_after) == (100.0, 90.0)


@pytest.mark.parametrize("amount", [50.01, -1.0])
def test_savings_failed_withdraw_recorded_once(savings, amount):
    assert savings.withdraw(amount) is None

    op = _single_operation(savings)
    assert (op.name, op.status) == ("withdraw", "fail")
    assert savings.get_balance() == 100.0


def test_apply_interest_recorded(savings):
    savings.apply_interest(5.0)

    op = _single_operation(savings)
    assert (op.name, op.status, op.value) == ("interest", "success", 5.0)
    assert op.balance_after == pytest.approx(105.0)


def test_failed_apply_interest_recorded(savings):
    assert savings.apply_interest(10.0) is None

    op = _single_operation(savings)
    assert (op.name, op.status) == ("interest", "fail")
    assert savings.get_balance() == 100.0


def test_deposit_with_kwarg_amount(checking):
    checking.deposit(amount=10.0)

    op = _single_operation(checking)
    assert (op.name, op.status, op.value) == ("deposit", "success", 10.0)
    assert checking.get_balance() == 110.0


def test_search_history_on_real_operations(checking):
    checking.deposit(5.0)
    checking.withdraw(1000.0)
    checking.withdraw(50.0)
    checking.deposit(20.0)

    assert [(op.name, op.value) for op in checking.search_history(limit=2)] == [
        ("withdraw", 50.0),
        ("deposit", 20.0),
    ]


# --- Тела операций без декоратора ---


def test_deposit_body(checking):
    Account.deposit.__wrapped__(checking, 50.0)

    assert checking.get_balance() == 150.0


@pytest.mark.parametrize("amount", [0.0, -5.0])
def test_deposit_body_non_positive(checking, amount):
    with pytest.raises(NegativeDepositError, match="больше 0"):
        Account.deposit.__wrapped__(checking, amount)

    assert checking.get_balance() == 100.0


@pytest.mark.parametrize(
    ("amount", "expected"),
    [(30.0, 70.0), (100.0, 0.0), (0.0, 100.0)],
)
def test_withdraw_body(checking, amount, expected):
    Account.withdraw.__wrapped__(checking, amount)

    assert checking.get_balance() == expected


def test_withdraw_body_negative_amount(checking):
    with pytest.raises(ValueError, match="Сумма снятия"):
        Account.withdraw.__wrapped__(checking, -1.0)


def test_withdraw_body_overdraft(checking):
    with pytest.raises(ValueError, match="Остаток"):
        Account.withdraw.__wrapped__(checking, 100.01)

    assert checking.get_balance() == 100.0


def test_savings_withdraw_body(savings):
    SavingsAccount.withdraw.__wrapped__(savings, 50.0)

    assert savings.get_balance() == 50.0
    # Родительский mark_operation заглушён, история не пишется
    assert savings.get_history() == []


def test_savings_withdraw_body_more_than_half(savings):
    with pytest.raises(ValueError, match="50%"):
        SavingsAccount.withdraw.__wrapped__(savings, 50.01)

    assert savings.get_balance() == 100.0


def test_savings_withdraw_body_parent_error_propagates(savings):
    with pytest.raises(ValueError, match="Сумма снятия"):
        SavingsAccount.withdraw.__wrapped__(savings, -1.0)


@pytest.mark.parametrize("rate", [0.0, -10.0, 7.01])
def test_apply_interest_body_rejects_invalid_rate(savings, rate):
    with pytest.raises(ValueError, match="процентной ставки"):
        SavingsAccount.apply_interest.__wrapped__(savings, rate)

    assert savings.get_balance() == 100.0


@pytest.mark.parametrize(("rate", "expected"), [(0.1, 100.1), (5.0, 105.0), (7.0, 107.0)])
def test_apply_interest_body(savings, rate, expected):
    SavingsAccount.apply_interest.__wrapped__(savings, rate)

    assert savings.get_balance() == pytest.approx(expected)


def test_apply_interest_body_custom_max_rate(manager):
    account = SavingsAccount(
        10.0, account_holder="Ivan Petrov", account_number_manager=manager, balance=100.0
    )

    SavingsAccount.apply_interest.__wrapped__(account, 10.0)

    assert account.get_balance() == pytest.approx(110.0)


# --- Поиск по истории ---


def _set_history(account, operations):
    setattr(account, HISTORY_ATTR, operations)


def test_search_history_empty(checking):
    assert checking.search_history() == []


def test_search_history_sorts_by_impact(checking, make_operation):
    small = make_operation(balance_before=0.0, balance_after=5.0)
    big = make_operation(balance_before=100.0, balance_after=0.0)
    mid = make_operation(balance_before=0.0, balance_after=50.0)
    _set_history(checking, [small, big, mid])

    assert checking.search_history() == [big, mid, small]


def test_search_history_ties_prefer_newest(checking, make_operation):
    older = make_operation(created_at=datetime(2025, 1, 1, tzinfo=UTC))
    newer = make_operation(created_at=datetime(2025, 1, 2, tzinfo=UTC))
    _set_history(checking, [older, newer])

    assert checking.search_history() == [newer, older]


def test_search_history_skips_failed(checking, make_operation):
    ok = make_operation()
    failed = make_operation(status="fail", balance_after=1000.0)
    _set_history(checking, [ok, failed])

    assert checking.search_history() == [ok]


def test_search_history_limit(checking, make_operation):
    ops = [make_operation(balance_after=float(i)) for i in range(10)]
    _set_history(checking, ops)

    result = checking.search_history(limit=3)

    assert result == [ops[9], ops[8], ops[7]]


def test_search_history_default_limit(checking, make_operation):
    _set_history(checking, [make_operation(balance_after=float(i)) for i in range(10)])

    assert len(checking.search_history()) == 5


def test_get_history_returns_same_list(checking, make_operation):
    op = make_operation()
    _set_history(checking, [op])

    assert checking.get_history() == [op]
